"""Tests for CLI commands: analyze and download-and-analyze."""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cgm_insights.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def sample_csv() -> Path:
    return Path(__file__).parent.parent.parent / "data" / "readings.csv"


class TestAnalyzeCommand:
    """Tests for the analyze subcommand."""

    def test_basic(self, runner: CliRunner, sample_csv: Path) -> None:
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        result = runner.invoke(app, ["analyze", str(sample_csv)])

        assert result.exit_code == 0
        assert "Analysis Period" in result.output
        assert "Average" in result.output

    def test_with_dates(self, runner: CliRunner, sample_csv: Path) -> None:
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        result = runner.invoke(
            app,
            ["analyze", str(sample_csv), "--start", "2026-04-20", "--end", "2026-04-22"],
        )

        assert result.exit_code == 0
        assert "Analysis Period" in result.output

    def test_missing_file(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["analyze", "/nonexistent/file.csv"])

        assert result.exit_code != 0
        assert "does not exist" in result.output.lower() or "invalid" in result.output.lower()

    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["analyze", "--help"])

        assert result.exit_code == 0
        assert "--start" in result.output
        assert "--end" in result.output
        assert "--exclude-warmup" in result.output or "--include-warmup" in result.output

    def test_shows_metrics(self, runner: CliRunner, sample_csv: Path) -> None:
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        result = runner.invoke(app, ["analyze", str(sample_csv)])

        assert result.exit_code == 0
        assert "Average" in result.output
        assert "GMI" in result.output
        assert "Target" in result.output or "70-180" in result.output

    def test_shows_gmi_caveat(self, runner: CliRunner, sample_csv: Path) -> None:
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        result = runner.invoke(app, ["analyze", str(sample_csv)])

        assert result.exit_code == 0
        assert "GMI" in result.output or "glucose management" in result.output.lower()

    def test_include_warmup(self, runner: CliRunner, sample_csv: Path) -> None:
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        result = runner.invoke(app, ["analyze", str(sample_csv), "--include-warmup"])

        assert result.exit_code == 0
        assert "Analysis Period" in result.output


class TestDownloadAndAnalyzeCommand:
    """Tests for the download-and-analyze subcommand."""

    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["download-and-analyze", "--help"])

        assert result.exit_code == 0
        assert "URL" in result.output or "url" in result.output
        assert "--start" in result.output
        assert "--end" in result.output

    def test_rejects_non_http_scheme(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["download-and-analyze", "ftp://example.com/data.csv"])

        assert result.exit_code != 0
        assert "http" in result.output.lower()

    def test_rejects_file_scheme(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["download-and-analyze", "file:///etc/passwd"])

        assert result.exit_code != 0
        assert "http" in result.output.lower()

    def test_download_failure_reported(self, runner: CliRunner) -> None:
        import urllib.error

        with patch(
            "urllib.request.urlretrieve",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = runner.invoke(
                app, ["download-and-analyze", "https://example.com/readings.csv"]
            )

        assert result.exit_code != 0
        assert "Download failed" in result.output or "connection refused" in result.output

    def test_downloads_and_analyzes(self, runner: CliRunner, sample_csv: Path) -> None:
        """Successful download: urlretrieve copies the sample CSV into the temp file."""
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        def fake_urlretrieve(url: str, dest: Path) -> None:
            shutil.copy(sample_csv, dest)

        with patch("urllib.request.urlretrieve", side_effect=fake_urlretrieve):
            result = runner.invoke(
                app, ["download-and-analyze", "https://example.com/readings.csv"]
            )

        assert result.exit_code == 0
        assert "Download complete" in result.output
        assert "Analysis Period" in result.output
        assert "Average" in result.output

    def test_temp_file_cleaned_up_on_success(self, runner: CliRunner, sample_csv: Path) -> None:
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        captured_tmp: list[Path] = []

        def fake_urlretrieve(url: str, dest: Path) -> None:
            captured_tmp.append(Path(dest))
            shutil.copy(sample_csv, dest)

        with patch("urllib.request.urlretrieve", side_effect=fake_urlretrieve):
            runner.invoke(app, ["download-and-analyze", "https://example.com/readings.csv"])

        assert captured_tmp, "urlretrieve was not called"
        assert not captured_tmp[0].exists(), "Temp file was not cleaned up"

    def test_temp_file_cleaned_up_on_error(self, runner: CliRunner, sample_csv: Path) -> None:
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        captured_tmp: list[Path] = []

        def fake_urlretrieve(url: str, dest: Path) -> None:
            captured_tmp.append(Path(dest))
            shutil.copy(sample_csv, dest)

        with patch("urllib.request.urlretrieve", side_effect=fake_urlretrieve), patch(
            "cgm_insights.cli._run_analysis", side_effect=RuntimeError("boom")
        ):
            runner.invoke(app, ["download-and-analyze", "https://example.com/readings.csv"])

        assert captured_tmp, "urlretrieve was not called"
        assert not captured_tmp[0].exists(), "Temp file was not cleaned up after error"

    def test_with_date_options(self, runner: CliRunner, sample_csv: Path) -> None:
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        def fake_urlretrieve(url: str, dest: Path) -> None:
            shutil.copy(sample_csv, dest)

        with patch("urllib.request.urlretrieve", side_effect=fake_urlretrieve):
            result = runner.invoke(
                app,
                [
                    "download-and-analyze",
                    "https://example.com/readings.csv",
                    "--start", "2026-04-20",
                    "--end", "2026-04-22",
                ],
            )

        assert result.exit_code == 0
        assert "Analysis Period" in result.output
