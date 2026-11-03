from pathlib import Path
from typing import Annotated

import typer

import comet.analysis.detectors  # noqa: F401  registers the detectors
import comet.analysis.metrics  # noqa: F401 registers the metrics
from comet import api
from comet.core.plugins import REGISTRY
from comet.core.regions import mean
from comet.core.types import Channel, Run
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
def detect(csv: Path, detector: str, tag: TagOption):
    """Find a region in a Launch Control CSV."""
    run = _load(csv, tag)
    typer.echo(api.detect(run, detector))


@app.command()
def report(csv: Path, detector: str, tag: TagOption):
    """Every metric over the region found by `detector`."""
    run = _load(csv, tag)
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
