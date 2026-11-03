from pathlib import Path

import yaml
from pydantic import BaseModel


class ChannelSpec(BaseModel):
    tags: list[str] = []
    range: tuple[float, float] | None = None


class Descriptor(BaseModel):
    data: Path
    format: str = "qret_csv"
    channels: dict[str, ChannelSpec] = {}


def load(path: Path) -> Descriptor:
    """Read a test descriptor, resolving `data` relative to the descriptor file."""
    d = Descriptor.model_validate(yaml.safe_load(path.read_text()))
    return d.model_copy(update={"data": path.parent / d.data})
