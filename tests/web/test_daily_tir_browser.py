"""Playwright regression tests for Daily TIR chart JavaScript behavior.

These tests run a real browser to catch regressions in chart-rendering logic
that cannot be tested at the Python/HTML level:

  - computeDailyTIR fills mid-period gaps with grey 0% bars
  - A 90-day dataset expands the container past the viewport and shows a scroll hint
  - All N bars are rendered (no bars are silently dropped)

The test server runs uvicorn in a background thread on port 18766 and shares
the same process-level session_store, so sessions created by test helpers are
immediately visible to the server.
"""

import math
import threading
import time
from datetime import datetime, timedelta

import httpx
import pytest

from cgm_insights.models import CGMReading
from src.web.app import app
from src.web.services.session import session_store, create_session
from tests.fixtures.sample_data import generate_sample_readings, generate_sample_results

_SERVER_PORT = 18766
_BASE_URL = f"http://127.0.0.1:{_SERVER_PORT}"


# ── Server fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def live_server():
    """Start a real uvicorn server so Playwright can load the app with full JS.

    Scoped to the module so the server starts once and is reused across all
    browser tests, keeping the suite fast.
    """
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=_SERVER_PORT, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            httpx.get(f"{_BASE_URL}/", timeout=1, follow_redirects=True)
            break
        except Exception:
            time.sleep(0.2)

    yield _BASE_URL

    server.should_exit = True
    thread.join(timeout=5)


# ── Session helpers ────────────────────────────────────────────────────────────

def _make_session(raw_readings: list[dict]) -> str:
    """Insert a session directly into the shared store and return its ID.

    The date_range on the AnalysisResults is derived from the first and last
    reading timestamps so glucoseDateRange in JS covers the full reading period.
    """
    from datetime import datetime as _dt

    sid = create_session()
    base = generate_sample_results()
    if raw_readings:
        ts_sorted = sorted(r["timestamp"] for r in raw_readings)
        results = base.model_copy(update={
            "date_range_start": _dt.fromisoformat(ts_sorted[0]),
            "date_range_end": _dt.fromisoformat(ts_sorted[-1]),
        })
    else:
        results = base
    session_store.store(sid, results, patterns=[], raw_readings=raw_readings)
    return sid


def _readings_30_days_full() -> list[dict]:
    """30 days, every 2 hours — 360 readings total, all days present."""
    start = datetime(2026, 3, 1, 0, 0)
    return [
        {
            "timestamp": (start + timedelta(days=d, hours=h)).isoformat(),
            "glucose": round(max(70.0, min(200.0, 140.0 + 20.0 * math.sin(h / 6.0))), 1),
        }
        for d in range(30)
        for h in range(0, 24, 2)
    ]


def _readings_30_days_with_gap(skip_days: set) -> list[dict]:
    """30-day range but skip_days have no readings (to test gap-filling)."""
    start = datetime(2026, 3, 1, 0, 0)
    return [
        {
            "timestamp": (start + timedelta(days=d, hours=h)).isoformat(),
            "glucose": round(max(70.0, min(200.0, 140.0 + 20.0 * math.sin(h / 6.0))), 1),
        }
        for d in range(30) if d not in skip_days
        for h in range(0, 24, 2)
    ]


def _readings_90_days_full() -> list[dict]:
    """90 days at 4-hour intervals — 540 readings, all 90 days covered."""
    start = datetime(2026, 1, 1, 0, 0)
    return [
        {
            "timestamp": (start + timedelta(days=d, hours=h)).isoformat(),
            "glucose": round(max(70.0, min(200.0, 140.0 + 20.0 * math.sin(h / 6.0))), 1),
        }
        for d in range(90)
        for h in range(0, 24, 4)
    ]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_chart_page(page, base_url: str, session_id: str, timeout_ms: int = 15000):
    """Navigate to results page and wait until the glucoseTrendChart canvas appears."""
    page.goto(f"{base_url}/results/{session_id}")
    page.wait_for_selector("#glucoseTrendChart", timeout=timeout_ms)
    page.wait_for_timeout(2000)  # Allow Chart.js initialisation to complete


def _chart_info(page) -> dict:
    """Return bar count and grey-bar count from the rendered chart."""
    return page.evaluate("""() => {
        const chart = Chart.getChart('glucoseTrendChart');
        if (!chart) return { found: false };
        const colors = chart.data.datasets[0].backgroundColor;
        return {
            found: true,
            barCount: chart.data.labels.length,
            greyBars: Array.isArray(colors)
                ? colors.filter(c => typeof c === 'string' && c.includes('156,163,175')).length
                : 0,
        };
    }""")


def _scroll_info(page) -> dict:
    """Return layout metrics for the scroll container and hint visibility."""
    return page.evaluate("""() => {
        const outer  = document.getElementById('glucoseTrendOuter');
        const scroll = document.getElementById('glucoseTrendScroll');
        const hint   = document.getElementById('glucoseTrendScrollHint');
        return {
            outerWidth:    outer  ? outer.offsetWidth  : 0,
            scrollVisible: scroll ? scroll.offsetWidth  : 0,
            scrollContent: scroll ? scroll.scrollWidth  : 0,
            hintVisible:   hint   ? !hint.classList.contains('hidden') : false,
        };
    }""")


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestDailyTIRBrowserBehavior:
    """Browser-level regression suite for the Daily TIR chart."""

    def test_30_day_full_dataset_renders_all_bars(self, live_server):
        """A 30-day dataset with no gaps must render exactly 30 bars.

        Regression guard: if computeDailyTIR slices or truncates the data,
        bar count drops below 30 and this test fails.
        """
        from playwright.sync_api import sync_playwright

        sid = _make_session(_readings_30_days_full())

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            _load_chart_page(page, live_server, sid)
            info = _chart_info(page)
            browser.close()

        assert info["found"], "glucoseTrendChart not initialised"
        assert info["barCount"] == 30, (
            f"Expected 30 bars for 30-day dataset, got {info['barCount']}"
        )
        assert info["greyBars"] == 0, (
            f"Expected 0 grey bars (no gaps), got {info['greyBars']}"
        )

    def test_mid_period_gap_filled_with_grey_bars(self, live_server):
        """Days 10–14 (5 days) have no readings; chart must show 30 bars with 5 grey.

        Regression guard: if computeDailyTIR reverts to skipping missing days,
        barCount drops to 25 and the visual gap-indicator disappears.
        """
        from playwright.sync_api import sync_playwright

        SKIP = {10, 11, 12, 13, 14}
        sid = _make_session(_readings_30_days_with_gap(SKIP))

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            _load_chart_page(page, live_server, sid)
            info = _chart_info(page)
            browser.close()

        assert info["found"], "glucoseTrendChart not initialised"
        assert info["barCount"] == 30, (
            f"Expected 30 bars (gap-filled), got {info['barCount']}. "
            "computeDailyTIR may have stopped filling missing days."
        )
        assert info["greyBars"] == len(SKIP), (
            f"Expected {len(SKIP)} grey no-data bars, got {info['greyBars']}"
        )

    def test_90_day_dataset_triggers_scroll_and_hint(self, live_server):
        """A 90-day dataset must expand the chart past the viewport and show the scroll hint.

        Regression guard: if per-bar width changes or width expansion is removed,
        long datasets silently squish all bars into the visible area.
        90 days × 32 px = 2 880 px, which exceeds any typical viewport width.
        """
        from playwright.sync_api import sync_playwright

        sid = _make_session(_readings_90_days_full())

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            _load_chart_page(page, live_server, sid)
            chart = _chart_info(page)
            scroll = _scroll_info(page)
            browser.close()

        assert chart["found"], "glucoseTrendChart not initialised"
        assert chart["barCount"] == 90, (
            f"Expected 90 bars for 90-day dataset, got {chart['barCount']}"
        )
        assert scroll["outerWidth"] > scroll["scrollVisible"], (
            f"Chart ({scroll['outerWidth']}px) should be wider than "
            f"visible area ({scroll['scrollVisible']}px) for a 90-day period."
        )
        assert scroll["hintVisible"], (
            "Scroll hint must be visible when chart overflows the container."
        )
