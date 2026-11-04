from collections.abc import Callable
from dataclasses import dataclass
from types import FunctionType
from typing import Literal, Protocol, get_type_hints

from pydantic.alias_generators import to_snake

from comet.core.types import Channel, Region


@dataclass(frozen=True)
class Plugin:
    kind: Literal["filter", "detector", "metric"]
    function: Callable
    unit: str | None = None  # metrics: from @metric(unit=...)
    region_kind: str | None = None  # detectors: from @detector(region="burn")

    @property
    def name(self) -> str:
        if isinstance(self.function, FunctionType):
            return f"{self.kind}/{to_snake(self.function.__name__)}"
        else:
            # Not all `Callable`s have __name__
            return f"{self.kind}/unknown_{id(self.function)}"


REGISTRY: dict[str, Plugin] = {}


def _add(p: Plugin):
    REGISTRY[p.name] = p


# A metric must output a number or a channel
class MetricDecorator(Protocol):
    def __call__[F: Callable[..., float | Channel]](self, fn: F, /) -> F: ...


# A detector must output a region or list of regions
class DetectorDecorator(Protocol):
    def __call__[F: Callable[..., Region | list[Region]]](self, fn: F, /) -> F: ...


def metric(*, unit: str) -> MetricDecorator:
    def register(fn):
        # A bare Region would never be selected by a report; the author says which kind.
        for param, hint in get_type_hints(fn, include_extras=True).items():
            if hint is Region and param != "return":
                raise TypeError(
                    f"{fn.__name__}: {param!r} needs a typed region, e.g. Burn"
                )
        p = Plugin("metric", fn, unit=unit)
        fn.__comet_plugin__ = p
        _add(p)

        return fn

    return register


def detector(*, kind: str) -> DetectorDecorator:
    def register(fn):
        p = Plugin("detector", fn, region_kind=kind)
        fn.__comet_plugin__ = p
        _add(p)

        return fn

    return register
