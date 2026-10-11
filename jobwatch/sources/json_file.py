from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..models import Job
from .base import Source


class JsonFileSource(Source):
    """로컬 JSON 파일에서 공고를 읽는다. 직접 만든 크롤러 출력이나 테스트용.

    형식: [{"id": "...", "title": "...", "company": "...", "url": "...",
            "location": "...", "tags": [...], "posted_at": "2026-10-01T09:00:00",
            "always_open": false}, ...]
    """

    def __init__(self, path: str, name: str = "json"):
        super().__init__(name)
        self.path = Path(path)

    def fetch(self) -> list[Job]:
        items = json.loads(self.path.read_text(encoding="utf-8"))
        return [
            Job(
                source=self.name,
                job_id=str(it["id"]),
                title=it["title"],
                company=it.get("company", ""),
                url=it.get("url", ""),
                location=it.get("location", ""),
                tags=list(it.get("tags", [])),
                posted_at=datetime.fromisoformat(it["posted_at"]) if it.get("posted_at") else None,
                always_open=bool(it.get("always_open", False)),
            )
            for it in items
        ]
