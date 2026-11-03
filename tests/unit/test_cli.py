from typer.testing import CliRunner

from comet.cli import app


def test_cli_detect_cold_flow():
    result = CliRunner().invoke(
        app,
        [
            "detect",
            "tests/data/cold-flow-2026-03-06-slice.csv",
            "tank_pressure_drop",
            "--tag",
            "PTRun=tank_pressure",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "cold_flow" in result.output


def test_cli_report_cold_flow():
    result = CliRunner().invoke(
        app,
        [
            "report",
            "tests/data/cold-flow-2026-03-06-slice.csv",
            "tank_pressure_drop",
            "--tag",
            "PTRun=tank_pressure",
            "--tag",
            "LCFill=tank_mass",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "oxidizer_mass_flow: 1.61 kg/s" in result.output
