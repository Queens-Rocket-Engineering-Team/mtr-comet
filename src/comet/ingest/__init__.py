from pathlib import Path

from comet.core.types import Run
from comet.ingest import checks, descriptor
from comet.ingest.adapter import QRETCsvAdapter

ADAPTERS = {"qret_csv": QRETCsvAdapter}


def ingest(path: Path) -> Run:
    """Load the test described by `path`: parse the data, then check it."""
    d = descriptor.load(path)
    tags = {name: spec.tags for name, spec in d.channels.items()}
    run = ADAPTERS[d.format]().ingest(str(d.data), tags)
    faults = [
        f
        for name, spec in d.channels.items()
        if spec.range and name in run.channels
        for f in checks.railed(run.channels[name], *spec.range)
    ]
    motor = descriptor.load_motor(d.motor) if d.motor else None
    return Run(run.channels, tuple(faults), motor)
