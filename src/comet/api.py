from collections.abc import Mapping
from typing import Annotated, get_args, get_origin, get_type_hints

from comet.core.plugins import REGISTRY
from comet.core.types import Channel, MotorConfig, Region, Run, Tag


def _tagged(fn, base: type) -> dict[str, str]:
    """Parameter name -> tag for every parameter annotated Annotated[base, Tag(...)]."""
    hints = get_type_hints(fn, include_extras=True)
    return {
        param: meta.name
        for param, hint in hints.items()
        if get_origin(hint) is Annotated and get_args(hint)[0] is base
        for meta in get_args(hint)[1:]
        if isinstance(meta, Tag)
    }


def channel_inputs(fn) -> dict[str, str]:
    """Parameter name -> channel tag, e.g. {"p": "tank_pressure"}."""
    return _tagged(fn, Channel)


def region_inputs(fn) -> dict[str, str]:
    """Parameter name -> region tag, e.g. {"liquid": "liquid_phase"}."""
    return _tagged(fn, Region)


def call(run: Run, name: str, regions: Mapping[str, Region] = {}, **kwargs):
    """Call plugin `name` with its tagged channels and regions resolved."""
    fn = REGISTRY[name].function
    channels = {param: run.channel(tag) for param, tag in channel_inputs(fn).items()}
    found = {param: regions[tag] for param, tag in region_inputs(fn).items()}

    if needs_motor(fn):
        if run.motor is None:
            raise ValueError(f"{name} needs a motor config, descriptor has none")
        kwargs |= {
            p: run.motor for p, h in get_type_hints(fn).items() if h is MotorConfig
        }

    return fn(**channels, **found, **kwargs)


def applicable(run: Run, name: str, regions: Mapping[str, Region] = {}) -> bool:
    """Whether every tagged input of plugin `name` can be resolved."""
    fn = REGISTRY[name].function
    channel_tags = {t for c in run.channels.values() for t in c.tags}
    return (
        all(tag in channel_tags for tag in channel_inputs(fn).values())
        and all(tag in regions for tag in region_inputs(fn).values())
        and (run.motor is not None or not needs_motor(fn))
    )


def detect(run: Run, name: str, **settings) -> Region | list[Region]:
    """Run the detector `name` on `run`."""
    return call(run, f"detector/{name}", **settings)


def compute(
    run: Run, name: str, region: Region, regions: Mapping[str, Region] = {}, **settings
) -> float | Channel:
    """Evaluate the metric `name` over `region`."""
    return call(run, f"metric/{name}", regions, region=region, **settings)


def needs_motor(fn) -> bool:
    return MotorConfig in get_type_hints(fn).values()
