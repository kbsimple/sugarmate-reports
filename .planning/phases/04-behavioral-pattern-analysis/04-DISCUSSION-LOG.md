# Phase 4: Behavioral Pattern Analysis - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 04-behavioral-pattern-analysis
**Areas discussed:** Window size UX, Existing patterns fate, Consistency score display, Consistency threshold

---

## Window size UX

| Option | Description | Selected |
|--------|-------------|----------|
| 60-min only | Single default window size — simplest UX | |
| All three (30/60/120) | Show all window sizes simultaneously | ✓ |
| User-selectable toggle | Default 60-min with toggle to switch | |

**User's choice:** All three (30/60/120)

**Follow-up — Layout:**

| Option | Description | Selected |
|--------|-------------|----------|
| Tabs (30 / 60 / 120) | One at a time, user switches | |
| Stacked sections | All visible, scrollable | |
| You decide | Claude picks based on existing dashboard layout | ✓ |

**User's choice:** Claude's discretion

**Notes:** User wants full visibility across all three window sizes. Layout deferred to implementation.

---

## Existing patterns fate

| Option | Description | Selected |
|--------|-------------|----------|
| Upgrade in place | Phase 4 replaces fixed 2-hour detection | |
| Keep both | Old patterns remain, new section added alongside | |
| Archive old, new is primary | Keep old code but don't surface in UI | |
| You decide | Claude decides based on codebase | ✓ (via "No constraint" answer) |

**User's choice:** No backward-compatibility constraint on CLI or web output — Claude decides

**Notes:** User confirmed no constraints on existing output. Upgrade-in-place is the natural implementation choice.

---

## Consistency score display

| Option | Description | Selected |
|--------|-------------|----------|
| Label only | Consistent/Moderate/Variable, no raw number | |
| Number + label | Show both r=0.72 and Consistent | |
| Top/bottom highlight | Rank top 3 most/least consistent, no individual scores | |
| Label default + optional number | User's own framing | ✓ |

**User's choice:** "Show at least the label but make it optional to see the number if I want to"

**Follow-up — How to reveal the raw number:**

| Option | Description | Selected |
|--------|-------------|----------|
| Tooltip on hover | Desktop-only disclosure | |
| Expandable detail | `<details>` section, works on mobile | ✓ |
| You decide | Claude picks the pattern | |

**User's choice:** Expandable detail section

**Notes:** Label is default, raw correlation coefficient revealed via `<details>` expand. Works on mobile, fits HTMX/Jinja2 pattern.

---

## Consistency threshold

| Option | Description | Selected |
|--------|-------------|----------|
| Relative to user's own data | Top/bottom quartile of user's periods | ✓ |
| Fixed absolute thresholds | e.g. r≥0.7 = consistent, r<0.4 = variable | |
| Both | Absolute first, fall back to relative | |

**User's choice:** Relative to the user's own data (top/bottom quartile)

**Notes:** This ensures every user sees meaningful output regardless of overall glucose control. Middle 50% = "Moderate".

---

## Claude's Discretion

- Layout for all-three window size display (tabs vs stacked sections)
- Fate of existing `detect_time_of_day_patterns()` / `detect_day_of_week_patterns()` code
- Exact correlation metric (Pearson r standard; Spearman acceptable)
- Minimum days threshold for a valid consistency score
- Whether `PatternResult` is extended or a new model created

## Deferred Ideas

- ENHC-01, ENHC-02, ENHC-03, ENHC-04 from REQUIREMENTS.md — all deferred to v2.1+
