from __future__ import annotations

import os
from datetime import datetime

import requests

from ..models import Job
from .base import Source

API_URL = "https://oapi.saramin.co.kr/job-search"
# close-type 코드: 1 접수마감일, 2 채용시, 3 상시, 4 수시
ALWAYS_OPEN_CLOSE_TYPES = {"3", "4"}


class SaraminSource(Source):
    """사람인 공식 채용공고 API (https://oapi.saramin.co.kr). access-key 발급 필요.

    params에는 API 검색 파라미터를 그대로 넣는다. 예: {"keywords": "백엔드", "loc_cd": "101000"}
    """

    def __init__(self, access_key: str | None = None, params: dict | None = None,
                 name: str = "saramin", pages: int = 1, count: int = 110, timeout: float = 15):
        super().__init__(name)
        self.access_key = access_key or os.environ.get("SARAMIN_ACCESS_KEY", "")
        if not self.access_key:
            raise ValueError("사람인 access_key가 없습니다 (설정 또는 SARAMIN_ACCESS_KEY 환경변수)")
        self.params = params or {}
        self.pages = pages
        self.count = count
        self.timeout = timeout

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        for page in range(self.pages):
            params = {"sort": "pd", **self.params, "access-key": self.access_key,
                      "start": page, "count": self.count}
            resp = requests.get(API_URL, params=params, timeout=self.timeout,
                                headers={"Accept": "application/json"})
            resp.raise_for_status()
            batch = self.parse(resp.json())
            jobs.extend(batch)
            if len(batch) < self.count:
                break
        return jobs

    def parse(self, data: dict) -> list[Job]:
        items = data.get("jobs", {}).get("job", [])
        out = []
        for it in items:
            pos = it.get("position", {})
            ts = it.get("posting-timestamp")
            out.append(Job(
                source=self.name,
                job_id=str(it["id"]),
                title=pos.get("title", ""),
                company=it.get("company", {}).get("detail", {}).get("name", ""),
                url=it.get("url", ""),
                location=pos.get("location", {}).get("name", "").replace("&gt;", ">"),
                tags=[t for t in [it.get("keyword", ""), pos.get("job-type", {}).get("name", "")] if t],
                posted_at=datetime.fromtimestamp(int(ts)) if ts else None,
                always_open=str(it.get("close-type", {}).get("code", "")) in ALWAYS_OPEN_CLOSE_TYPES,
            ))
        return out
