from pathlib import Path

import typer

import comet.analysis.detectors  # noqa: F401  registers the detectors
import comet.analysis.metrics  # noqa: F401 registers the metrics
from comet import api
from comet.core.plugins import REGISTRY
from comet.core.regions import mean, span
from comet.core.types import Channel, Region
from comet.ingest import ingest

app = typer.Typer()


@app.callback()
def main():
    """COMET: cold flow and hotfire analysis."""


@app.command()
def detect(descriptor: Path, detector: str):
    """Find a region in a test."""
    typer.echo(api.detect(ingest(descriptor), detector))


@app.command()
def report(descriptor: Path):
    """Every detector, then every metric, for one test."""
    run = ingest(descriptor)
    for f in run.faults:
        typer.echo(
            f"warning: {f.channel} {f.kind} {f.region.start:.1f}-{f.region.end:.1f}",
            err=True,
        )
        if run.channels[f.channel].tags:
            raise typer.Exit(code=1)

    # Run every detector whose inputs this test has. The first detector registered
    # for a kind supplies that region. Later ones still print, so any disagreement
    # between detectors is visible.
    regions: dict[str, Region] = {}
    for name, plugin in REGISTRY.items():
        if plugin.kind != "detector" or not api.applicable(run, name):
            continue
        short = name.removeprefix("detector/")
        try:
            found = api.detect(run, short)
        except ValueError as e:
            typer.echo(f"warning: {short}: {e}", err=True)
            continue
        for r in found if isinstance(found, list) else [found]:
            end = f"{r.end:.2f}" if r.end is not None else "open"
            typer.echo(f"{r.kind}: {r.start:.2f}-{end} ({short})")
            regions.setdefault(r.kind, r)

    for name, plugin in REGISTRY.items():
        if plugin.kind != "metric" or not api.applicable(run, name, regions):
            continue
        short = name.removeprefix("metric/")
        value = api.compute(run, short, regions)
        if isinstance(value, Channel):
            value = mean(value, span(value))
        typer.echo(f"{short}: {value:.2f} {plugin.unit}")
