from datetime import datetime, timedelta

import pytest

from jobwatch.filters import EvergreenFilter, FilterConfig
from jobwatch.models import Job, normalize_company, normalize_title
from jobwatch.runner import run_once
from jobwatch.sources.base import Source
from jobwatch.sources.rss import RssSource
from jobwatch.sources.saramin import SaraminSource
from jobwatch.store import Store

NOW = datetime(2026, 10, 11, 12, 0)


class ListSource(Source):
    def __init__(self, jobs):
        super().__init__("test")
        self.jobs = jobs

    def fetch(self):
        return list(self.jobs)


class Collector:
    def __init__(self):
        self.sent = []

    def send(self, job):
        self.sent.append(job)


def job(i, title="웹 개발자 채용", company="작은회사", **kw):
    return Job(source="test", job_id=str(i), title=title, company=company, **kw)


@pytest.fixture
def store():
    s = Store(":memory:")
    yield s
    s.close()


def make(store, **cfg):
    return EvergreenFilter(FilterConfig(**{"company_max_posts": 0, "max_age_days": 0, **cfg}), store)


def test_normalize():
    assert normalize_title("[급구] 물류센터 상하차 (주간/야간)") == "물류센터상하차"
    assert normalize_company("(주)작은회사") == normalize_company("작은회사 주식회사") == "작은회사"


def test_new_job_is_notified_once(store):
    c = Collector()
    src = ListSource([job(1)])
    r1 = run_once([src], store, make(store), [c], now=NOW)
    r2 = run_once([src], store, make(store), [c], now=NOW)
    assert len(r1.new) == 1 and len(r2.new) == 0 and r2.already_seen == 1
    assert len(c.sent) == 1


def test_keyword_filter(store):
    c = Collector()
    run_once([ListSource([job(1, title="쿠팡 물류센터 상하차 당일지급")])], store, make(store), [c], now=NOW)
    assert c.sent == []


def test_include_keywords(store):
    flt = make(store, include_keywords=["개발"])
    assert flt.reasons(job(1), NOW) == []
    assert "관심 키워드 없음" in flt.reasons(job(2, title="매장 판매직"), NOW)


def test_repost_is_filtered(store):
    c = Collector()
    run_once([ListSource([job(1, title="[급구] 홀서빙")])], store, make(store), [c], now=NOW)
    # 같은 공고를 id만 바꿔 다시 올림
    run_once([ListSource([job(2, title="홀서빙 (급구)")])], store, make(store), [c],
             now=NOW + timedelta(days=3))
    assert [j.job_id for j in c.sent] == ["1"]


def test_mass_hiring_company(store):
    c = Collector()
    flt = make(store, company_max_posts=3, company_window_days=14)
    jobs = [job(i, title=f"포지션 {chr(65 + i)}", company="대량회사") for i in range(5)]
    run_once([ListSource(jobs)], store, flt, [c], now=NOW)
    assert len(c.sent) == 2  # 3번째부터 대량채용으로 걸러짐


def test_mass_hiring_window_expires(store):
    flt = make(store, company_max_posts=2, company_window_days=7)
    store.insert(job(1, title="A"), NOW - timedelta(days=30), [], True)
    assert flt.reasons(job(2, title="B"), NOW) == []


def test_always_open_and_blocked_and_old(store):
    flt = make(store, blocked_companies=["(주)나쁜회사"], max_age_days=30)
    assert "상시/수시 채용" in flt.reasons(job(1, always_open=True), NOW)
    assert any("차단 회사" in r for r in flt.reasons(job(2, company="나쁜회사"), NOW))
    assert any("오래된" in r for r in flt.reasons(job(3, posted_at=NOW - timedelta(days=90)), NOW))


def test_baseline_does_not_notify(store):
    c = Collector()
    run_once([ListSource([job(1)])], store, make(store), [c], baseline=True, now=NOW)
    run_once([ListSource([job(1), job(2, title="새 포지션")])], store, make(store), [c], now=NOW)
    assert [j.job_id for j in c.sent] == ["2"]


def test_broken_source_does_not_stop_others(store):
    class Broken(Source):
        def fetch(self):
            raise RuntimeError("boom")

    c = Collector()
    r = run_once([Broken("x"), ListSource([job(1)])], store, make(store), [c], now=NOW)
    assert len(c.sent) == 1 and r.errors


def test_saramin_parse():
    src = SaraminSource(access_key="k")
    data = {"jobs": {"job": [
        {"id": "123", "url": "https://saramin/123", "posting-timestamp": "1760000000",
         "close-type": {"code": "3", "name": "상시"},
         "company": {"detail": {"name": "(주)회사"}},
         "position": {"title": "백엔드", "location": {"name": "서울 &gt; 강남구"},
                      "job-type": {"name": "정규직"}}, "keyword": "Python"},
    ]}}
    (j,) = src.parse(data)
    assert j.job_id == "123" and j.company == "(주)회사" and j.always_open
    assert j.location == "서울 > 강남구" and "Python" in j.tags


def test_rss_parse():
    xml = b"""<rss><channel>
      <item><title>Acme - Data Engineer</title><link>https://x/1</link>
            <guid>g1</guid><pubDate>Sat, 10 Oct 2026 09:00:00 +0900</pubDate>
            <category>remote</category></item>
    </channel></rss>"""
    (j,) = RssSource("u", company_separator=" - ").parse(xml)
    assert (j.job_id, j.company, j.title, j.tags) == ("g1", "Acme", "Data Engineer", ["remote"])
    assert j.posted_at.day == 10
