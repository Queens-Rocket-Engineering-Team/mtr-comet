from typer.testing import CliRunner

from comet.cli import app


def test_cli_detect_cold_flow():
    result = CliRunner().invoke(
        app,
        [
            "detect",
            "tests/data/cold-flow-2026-03-06.yaml",
            "tank_pressure_drop",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "cold_flow" in result.output


def test_cli_report_cold_flow():
    result = CliRunner().invoke(
        app,
        [
            "report",
            "tests/data/cold-flow-2026-03-06.yaml",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "oxidizer_mass_flow: 1.61 kg/s" in result.output


def test_cli_report_hotfire():
    result = CliRunner().invoke(app, ["report", "tests/data/hot-fire-2026-07-11.yaml"])
    assert result.exit_code == 0, result.output
    assert "burn: 10015.15-10022.32 (thrust_above)" in result.output
    assert "discharge_coefficient: 0.35" in result.output
