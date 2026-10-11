from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Job


class Source(ABC):
    """공고 목록을 가져오는 어댑터. 새 사이트는 이걸 상속해서 fetch()만 구현하면 된다."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fetch(self) -> list[Job]:
        ...
