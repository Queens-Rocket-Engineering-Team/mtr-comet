from dataclasses import dataclass
from typing import Annotated

import numpy as np


@dataclass(frozen=True)
class Channel:
    name: str
    times: np.ndarray
    values: np.ndarray
    unit: str
    tags: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Region:
    """A closed time interval in a run. `end` is None for a region with no end."""

    kind: str
    start: float
    end: float | None


@dataclass(frozen=True)
class Run:
    channels: dict[str, Channel]

    def channel(self, tag: str) -> Channel:
        found = [c for c in self.channels.values() if tag in c.tags]
        if len(found) != 1:
            raise LookupError(f"{len(found)} channels tagged {tag!r}, need exactly one")
        return found[0]


@dataclass(frozen=True)
class Tag:
    """The standard tag an input channel is found by."""

    name: str


@dataclass(frozen=True)
class Dimension:
    name: str


# Typed Inputs
Thrust = Annotated[Channel, Tag("thrust"), Dimension("force")]
TankPressure = Annotated[Channel, Tag("tank_pressure"), Dimension("pressure")]
TankMass = Annotated[Channel, Tag("tank_mass"), Dimension("mass")]
