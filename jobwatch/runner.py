from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from .filters import EvergreenFilter
from .models import Job
from .notify import Notifier
from .sources.base import Source
from .store import Store

log = logging.getLogger("jobwatch")


@dataclass
class RunResult:
    fetched: int = 0
    already_seen: int = 0
    new: list[Job] = field(default_factory=list)
    skipped: list[tuple[Job, list[str]]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run_once(sources: list[Source], store: Store, flt: EvergreenFilter,
             notifiers: list[Notifier], baseline: bool = False,
             now: datetime | None = None) -> RunResult:
    """모든 소스를 한 번 훑는다. baseline=True면 기록만 하고 알림은 보내지 않는다."""
    now = now or datetime.now()
    result = RunResult()
    for src in sources:
        try:
            jobs = src.fetch()
        except Exception as e:  # 한 소스가 죽어도 나머지는 돈다
            log.warning("소스 %s 실패: %s", src.name, e)
            result.errors.append(f"{src.name}: {e}")
            continue
        result.fetched += len(jobs)
        seen_this_run: set[tuple[str, str]] = set()
        for job in jobs:
            key = (job.source, job.job_id)
            if key in seen_this_run:
                continue
            seen_this_run.add(key)
            if store.exists(job):
                store.touch(job, now)
                result.already_seen += 1
                continue
            reasons = flt.reasons(job, now)
            notify = not reasons and not baseline
            if notify:
                for n in notifiers:
                    try:
                        n.send(job)
                    except Exception as e:
                        log.warning("알림 %s 실패: %s", type(n).__name__, e)
                        result.errors.append(f"{type(n).__name__}: {e}")
                result.new.append(job)
            elif reasons:
                result.skipped.append((job, reasons))
            store.insert(job, now, reasons, notified=notify)
        store.commit()
    return result
