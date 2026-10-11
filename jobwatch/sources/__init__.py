from __future__ import annotations

from .base import Source
from .json_file import JsonFileSource
from .rss import RssSource
from .saramin import SaraminSource

SOURCE_TYPES: dict[str, type[Source]] = {
    "saramin": SaraminSource,
    "rss": RssSource,
    "json": JsonFileSource,
}


def build_source(spec: dict) -> Source:
    spec = dict(spec)
    kind = spec.pop("type")
    try:
        cls = SOURCE_TYPES[kind]
    except KeyError:
        raise ValueError(f"알 수 없는 소스 type: {kind!r} (가능: {', '.join(SOURCE_TYPES)})")
    return cls(**spec)
