from typing import Annotated, get_args, get_origin, get_type_hints

from comet.core.plugins import REGISTRY
from comet.core.types import Channel, Region, Run, Tag


def inputs(fn) -> dict[str, str]:
    """Parameter name -> tag, for every Annotated[Channel, Tag(...)] parameter."""
    hints = get_type_hints(fn, include_extras=True)
    return {
        param: meta.name
        for param, hint in hints.items()
        if get_origin(hint) is Annotated
        for meta in get_args(hint)[1:]
        if isinstance(meta, Tag)
    }


def call(run: Run, name: str, **kwargs):
    """Call plugin `name` with its tagged input channels resolved from `run`."""
    fn = REGISTRY[name].function
    channels = {param: run.channel(tag) for param, tag in inputs(fn).items()}
    return fn(**channels, **kwargs)


def detect(run: Run, name: str, **settings) -> Region | list[Region]:
    """Run the detector `name` on `run`."""
    return call(run, f"detector/{name}", **settings)


def compute(run: Run, name: str, region: Region, **settings) -> float | Channel:
    """Evaluate the metric `name` over `region`."""
    return call(run, f"metric/{name}", region=region, **settings)
