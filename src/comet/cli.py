from pathlib import Path
from typing import Annotated

import typer

import comet.analysis.detectors  # noqa: F401  registers the detectors
import comet.analysis.metrics  # noqa: F401 registers the metrics
from comet import api
from comet.core.plugins import REGISTRY
from comet.core.regions import mean
from comet.core.types import Channel, Run
from comet.ingest import ingest
from comet.ingest.adapter import QRETCsvAdapter

app = typer.Typer()


@app.callback()
def main():
    """COMET: cold flow and hotfire analysis."""


TagOption = Annotated[
    list[str],
    typer.Option(default_factory=list, help="COLUMN=TAG, e.g. PTRun=tank_pressure"),
]


def _load(csv: Path, tag: TagOption) -> Run:
    tags: dict[str, list[str]] = {}
    for item in tag:
        column, _, name = item.partition("=")
        tags.setdefault(column, []).append(name)
    return QRETCsvAdapter().ingest(str(csv), tags)


@app.command()
def detect(descriptor: Path, detector: str):
    """Find a region in a test."""
    typer.echo(api.detect(ingest(descriptor), detector))


@app.command()
def report(descriptor: Path, detector: str):
    """Every metric over the region found by `detector`."""
    run = ingest(descriptor)
    for f in run.faults:
        typer.echo(
            f"warning: {f.channel} {f.kind} {f.region.start:.1f}-{f.region.end:.1f}",
            err=True,
        )
        if run.channels[f.channel].tags:
            raise typer.Exit(code=1)
    region = api.detect(run, detector)
    if isinstance(region, list):
        raise typer.BadParameter(
            f"{detector} found {len(region)} regions, report needs one"
        )
    for name, plugin in REGISTRY.items():
        if plugin.kind != "metric":
            continue
        value = api.compute(run, name.removeprefix("metric/"), region)
        if isinstance(value, Channel):
            value = mean(value, region)
        typer.echo(f"{name.removeprefix('metric/')}: {value:.2f} {plugin.unit}")
