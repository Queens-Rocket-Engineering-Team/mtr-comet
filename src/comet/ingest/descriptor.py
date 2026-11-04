from pathlib import Path

import yaml
from pydantic import BaseModel

from comet.core.types import MotorConfig


class ChannelSpec(BaseModel):
    tags: list[str] = []
    range: tuple[float, float] | None = None


class Descriptor(BaseModel):
    data: Path
    format: str = "qret_csv"
    motor: Path | None = None
    channels: dict[str, ChannelSpec] = {}


def load(path: Path) -> Descriptor:
    """Read a test descriptor, resolving file paths relative to the descriptor."""
    d = Descriptor.model_validate(yaml.safe_load(path.read_text()))
    return d.model_copy(
        update={
            "data": path.parent / d.data,
            "motor": path.parent / d.motor if d.motor else None,
        }
    )


def load_motor(path: Path) -> MotorConfig:
    """Read a motor config file."""
    return MotorConfig.model_validate(yaml.safe_load(path.read_text()))
