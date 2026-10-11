from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

_BRACKETS = re.compile(r"[\[\(【<{][^\]\)】>}]*[\]\)】>}]")
_COMPANY_SUFFIX = re.compile(r"(주식회사|\(주\)|㈜|\(유\)|유한회사|co\.?,?\s*ltd\.?|inc\.?|corp\.?)", re.I)
_NON_WORD = re.compile(r"[^\w가-힣]+")


def normalize_title(title: str) -> str:
    """'[급구] 물류센터 상하차 (주간/야간)' -> '물류센터상하차'"""
    t = _BRACKETS.sub(" ", title.lower())
    return _NON_WORD.sub("", t)


def normalize_company(company: str) -> str:
    c = _COMPANY_SUFFIX.sub(" ", company.lower())
    return _NON_WORD.sub("", c)


@dataclass
class Job:
    source: str
    job_id: str
    title: str
    company: str
    url: str = ""
    location: str = ""
    tags: list[str] = field(default_factory=list)
    posted_at: datetime | None = None
    # 소스가 '상시채용/수시채용' 같은 마감 유형을 알려주면 True
    always_open: bool = False

    @property
    def company_key(self) -> str:
        return normalize_company(self.company)

    @property
    def fingerprint(self) -> str:
        """같은 회사가 같은 공고를 id만 바꿔 다시 올려도 같은 값이 나온다."""
        return f"{self.company_key}|{normalize_title(self.title)}"

    def searchable_text(self) -> str:
        return " ".join([self.title, self.company, self.location, *self.tags]).lower()
