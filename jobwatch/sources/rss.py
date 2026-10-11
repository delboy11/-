from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

from ..models import Job
from .base import Source

_ATOM = "{http://www.w3.org/2005/Atom}"


class RssSource(Source):
    """RSS 2.0 / Atom 피드. 제목이 '회사명 - 공고명' 꼴이면 company_separator로 나눈다."""

    def __init__(self, url: str, name: str = "rss", company_separator: str | None = None,
                 timeout: float = 15):
        super().__init__(name)
        self.url = url
        self.company_separator = company_separator
        self.timeout = timeout

    def fetch(self) -> list[Job]:
        resp = requests.get(self.url, timeout=self.timeout, headers={"User-Agent": "jobwatch/0.1"})
        resp.raise_for_status()
        return self.parse(resp.content)

    def parse(self, content: bytes) -> list[Job]:
        root = ET.fromstring(content)
        jobs: list[Job] = []
        for item in root.iter("item"):
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or link).strip()
            date = item.findtext("pubDate")
            jobs.append(self._make(guid, item.findtext("title") or "", link,
                                   item.findtext("author") or "",
                                   [c.text or "" for c in item.findall("category")], date, rfc822=True))
        for entry in root.iter(f"{_ATOM}entry"):
            link_el = entry.find(f"{_ATOM}link")
            link = link_el.get("href", "") if link_el is not None else ""
            guid = (entry.findtext(f"{_ATOM}id") or link).strip()
            jobs.append(self._make(guid, entry.findtext(f"{_ATOM}title") or "", link,
                                   entry.findtext(f"{_ATOM}author/{_ATOM}name") or "",
                                   [c.get("term", "") for c in entry.findall(f"{_ATOM}category")],
                                   entry.findtext(f"{_ATOM}updated"), rfc822=False))
        return jobs

    def _make(self, guid, title, link, author, tags, date, rfc822: bool) -> Job:
        title = title.strip()
        company = author.strip()
        if self.company_separator and self.company_separator in title and not company:
            company, title = (s.strip() for s in title.split(self.company_separator, 1))
        posted = None
        if date:
            try:
                if rfc822:
                    posted = parsedate_to_datetime(date)
                else:
                    posted = datetime.fromisoformat(date.strip().replace("Z", "+00:00"))
            except (TypeError, ValueError):
                posted = None
        return Job(source=self.name, job_id=guid, title=title, company=company, url=link,
                   tags=[t for t in tags if t], posted_at=posted)
