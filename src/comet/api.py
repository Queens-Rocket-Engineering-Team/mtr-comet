from collections.abc import Mapping
from typing import Annotated, get_args, get_origin, get_type_hints

from comet.core.plugins import REGISTRY
from comet.core.types import Channel, MotorConfig, Region, Run, Tag


def _tagged(fn, base: type) -> dict[str, list[str]]:
    """Parameter name -> tags, for every parameter typed Annotated[base, Tag(...)]."""
    hints = get_type_hints(fn, include_extras=True)
    return {
        param: [meta.name for meta in get_args(hint)[1:] if isinstance(meta, Tag)]
        for param, hint in hints.items()
        if get_origin(hint) is Annotated and get_args(hint)[0] is base
    }


def channel_inputs(fn) -> dict[str, str]:
    """Parameter name -> channel tag, e.g. {"p": "tank_pressure"}."""
    return {param: tags[0] for param, tags in _tagged(fn, Channel).items()}


def region_inputs(fn) -> dict[str, list[str]]:
    """Parameter name -> acceptable region kinds in priority order."""
    return _tagged(fn, Region)


def _pick(regions: Mapping[str, Region], kinds: list[str]) -> Region:
    """The first region whose kind is in `kinds`, in that order."""
    for kind in kinds:
        if kind in regions:
            return regions[kind]
    raise ValueError(f"no region of kind {' or '.join(kinds)}")


def call(run: Run, name: str, regions: Mapping[str, Region] = {}, **kwargs):
    """Call plugin `name` with its tagged channels and regions resolved."""
    fn = REGISTRY[name].function
    channels = {param: run.channel(tag) for param, tag in channel_inputs(fn).items()}
    found = {param: _pick(regions, kinds) for param, kinds in region_inputs(fn).items()}

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
        and all(
            any(k in regions for k in kinds) for kinds in region_inputs(fn).values()
        )
        and (run.motor is not None or not needs_motor(fn))
    )


def detect(run: Run, name: str, **settings) -> Region | list[Region]:
    """Run the detector `name` on `run`."""
    return call(run, f"detector/{name}", **settings)


def compute(
    run: Run, name: str, regions: Mapping[str, Region] = {}, **settings
) -> float | Channel:
    """Evaluate the metric `name`, taking the regions it declares from `regions`."""
    return call(run, f"metric/{name}", regions, **settings)


def needs_motor(fn) -> bool:
    return MotorConfig in get_type_hints(fn).values()
