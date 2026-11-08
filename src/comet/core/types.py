import math
from dataclasses import dataclass
from typing import Annotated

import numpy as np
from pydantic import BaseModel


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
class Fault:
    """A data-quality problem on one channel over a region."""

    channel: str
    kind: str
    region: Region


class InjectorConfig(BaseModel):
    area: float  # m^2, total orifice area


class NozzleConfig(BaseModel):
    throat_diameter: float  # m
    exit_diameter: float  # m

    @property
    def throat_area(self) -> float:
        return math.pi * (self.throat_diameter / 2) ** 2

    @property
    def expansion_ratio(self) -> float:
        return (self.exit_diameter / self.throat_diameter) ** 2


class MotorConfig(BaseModel):
    injector: InjectorConfig
    nozzle: NozzleConfig


@dataclass(frozen=True)
class Run:
    channels: dict[str, Channel]
    faults: tuple[Fault, ...] = ()
    motor: MotorConfig | None = None

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
# Channels
Thrust = Annotated[Channel, Tag("thrust"), Dimension("force")]
TankPressure = Annotated[Channel, Tag("tank_pressure"), Dimension("pressure")]
TankMass = Annotated[Channel, Tag("tank_mass"), Dimension("mass")]
PreInjectorPressure = Annotated[
    Channel, Tag("preinjector_pressure"), Dimension("pressure")
]
ChamberPressure = Annotated[Channel, Tag("chamber_pressure"), Dimension("pressure")]
RunValve = Annotated[Channel, Tag("run_valve")]

# Regions
LiquidPhase = Annotated[Region, Tag("liquid_phase")]
Burn = Annotated[Region, Tag("burn")]
ColdFlow = Annotated[Region, Tag("cold_flow")]
Ignition = Annotated[Region, Tag("ignition")]
# Either kind of oxidizer flow. When a test has both, the burn is used.
OxidizerFlow = Annotated[Region, Tag("burn"), Tag("cold_flow")]
