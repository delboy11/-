"""'상주하는 일자리' 판별 규칙.

공고 하나에 대해 걸러야 할 이유 목록을 돌려준다. 빈 목록이면 진짜 새 공고.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import Job, normalize_company
from .store import Store

DEFAULT_KEYWORDS = [
    "상시채용", "상시모집", "상시 채용", "상시 모집", "수시채용", "수시모집",
    "물류센터", "상하차", "택배분류", "일용직", "당일지급", "단기알바",
    "쿠팡", "cfs", "풀필먼트",
]


@dataclass
class FilterConfig:
    keywords: list[str] = field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    # 반드시 포함돼야 하는 키워드(하나라도). 비우면 제한 없음.
    include_keywords: list[str] = field(default_factory=list)
    blocked_companies: list[str] = field(default_factory=list)
    # 같은 회사+제목이 이 횟수 이상 이미 올라왔으면 재게시로 본다
    repost_threshold: int = 1
    # company_window_days 동안 한 회사가 이만큼 이상 올리면 대량채용으로 본다
    company_max_posts: int = 5
    company_window_days: int = 14
    # 소스가 '상시/수시' 마감 유형이라고 알려주면 거른다
    skip_always_open: bool = True
    # 처음 본 시점에 이미 이만큼 오래된 공고면 거른다 (0이면 끔)
    max_age_days: int = 30

    @classmethod
    def from_dict(cls, d: dict | None) -> "FilterConfig":
        d = dict(d or {})
        extra = d.pop("extra_keywords", [])
        cfg = cls(**d)
        cfg.keywords = [*cfg.keywords, *extra]
        return cfg


class EvergreenFilter:
    def __init__(self, cfg: FilterConfig, store: Store):
        self.cfg = cfg
        self.store = store
        self._keywords = [k.lower() for k in cfg.keywords]
        self._include = [k.lower() for k in cfg.include_keywords]
        self._blocked = {normalize_company(c) for c in cfg.blocked_companies}

    def reasons(self, job: Job, now: datetime) -> list[str]:
        """store에 job을 넣기 *전에* 호출해야 한다."""
        cfg = self.cfg
        out: list[str] = []
        text = job.searchable_text()

        if self._include and not any(k in text for k in self._include):
            out.append("관심 키워드 없음")

        hits = [k for k in self._keywords if k in text]
        if hits:
            out.append(f"키워드: {', '.join(hits)}")

        if job.company_key in self._blocked:
            out.append(f"차단 회사: {job.company}")

        if cfg.skip_always_open and job.always_open:
            out.append("상시/수시 채용")

        prior = self.store.fingerprint_count(job.fingerprint)
        if prior >= cfg.repost_threshold > 0:
            out.append(f"재게시 {prior}회")

        if cfg.company_max_posts > 0:
            since = now - timedelta(days=cfg.company_window_days)
            # 지금 공고까지 포함한 개수
            n = self.store.company_count(job.company_key, since) + 1
            if n >= cfg.company_max_posts:
                out.append(f"대량채용: {cfg.company_window_days}일간 {n}건")

        if cfg.max_age_days > 0 and job.posted_at is not None:
            posted = job.posted_at.astimezone().replace(tzinfo=None) if job.posted_at.tzinfo else job.posted_at
            age = (now - posted).days
            if age > cfg.max_age_days:
                out.append(f"오래된 공고: {age}일 전 게시")

        return out
