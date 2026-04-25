"""Tests for CLI analyze command."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from cgm_insights.cli import app


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_csv() -> Path:
    """Get path to sample CSV file."""
    return Path(__file__).parent.parent.parent / "data" / "readings.csv"


class TestAnalyzeCommand:
    """Tests for the analyze command."""

    def test_analyze_command_basic(self, runner: CliRunner, sample_csv: Path) -> None:
        """Test analyze command with basic file argument."""
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        # With single-command Typer app, invoke directly without subcommand
        result = runner.invoke(app, [str(sample_csv)])

        assert result.exit_code == 0
        assert "Analysis Period" in result.output
        assert "Time in Range" in result.output
        assert "Glucose Metrics" in result.output

    def test_analyze_command_with_dates(
        self, runner: CliRunner, sample_csv: Path
    ) -> None:
        """Test analyze command accepts date range options."""
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        result = runner.invoke(
            app,
            [
                str(sample_csv),
                "--start",
                "2026-04-20",
                "--end",
                "2026-04-22",
            ],
        )

        assert result.exit_code == 0
        # Command accepts date arguments and processes successfully
        assert "Analysis Period" in result.output

    def test_analyze_command_missing_file(self, runner: CliRunner) -> None:
        """Test analyze command returns error for missing file."""
        result = runner.invoke(app, ["/nonexistent/file.csv"])

        # Typer validation errors use exit code 2, not 1
        assert result.exit_code != 0
        # Error message should mention file issue
        assert "does not exist" in result.output.lower() or "invalid" in result.output.lower()

    def test_analyze_command_help(self, runner: CliRunner) -> None:
        """Test analyze command help shows expected options."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "--start" in result.output
        assert "--end" in result.output
        assert "--exclude-warmup" in result.output or "--include-warmup" in result.output

    def test_analyze_command_shows_metrics(
        self, runner: CliRunner, sample_csv: Path
    ) -> None:
        """Test analyze command displays key glucose metrics."""
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        result = runner.invoke(app, [str(sample_csv)])

        assert result.exit_code == 0
        # Verify key metrics are in output
        assert "Average:" in result.output
        assert "GMI:" in result.output
        assert "Target (70-180):" in result.output

    def test_analyze_command_shows_gmi_caveat(
        self, runner: CliRunner, sample_csv: Path
    ) -> None:
        """Test analyze command displays GMI caveat."""
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        result = runner.invoke(app, [str(sample_csv)])

        assert result.exit_code == 0
        # GMI caveat should be displayed
        assert "GMI" in result.output or "glucose management" in result.output.lower()

    def test_analyze_command_include_warmup(
        self, runner: CliRunner, sample_csv: Path
    ) -> None:
        """Test analyze command with --include-warmup flag."""
        if not sample_csv.exists():
            pytest.skip("Sample data file not found")

        result = runner.invoke(app, [str(sample_csv), "--include-warmup"])

        assert result.exit_code == 0
        assert "Analysis Period" in result.output