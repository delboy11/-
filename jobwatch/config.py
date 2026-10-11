from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

_ENV = re.compile(r"\$\{(\w+)\}")


def _expand(value):
    if isinstance(value, str):
        return _ENV.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, list):
        return [_expand(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    return value


def load_config(path: str | Path) -> dict:
    """YAML 설정을 읽고 ${ENV_VAR} 를 환경변수 값으로 바꾼다."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return _expand(data)
