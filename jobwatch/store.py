from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from .models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    source      TEXT NOT NULL,
    job_id      TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    company_key TEXT NOT NULL,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL,
    url         TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    seen_count  INTEGER NOT NULL DEFAULT 1,
    reasons     TEXT NOT NULL DEFAULT '',
    notified    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (source, job_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_fp ON jobs(fingerprint);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_key, first_seen);
"""


class Store:
    def __init__(self, path: str = "jobwatch.db"):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def exists(self, job: Job) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM jobs WHERE source=? AND job_id=?", (job.source, job.job_id)
        ).fetchone()
        return row is not None

    def touch(self, job: Job, now: datetime) -> None:
        self.conn.execute(
            "UPDATE jobs SET last_seen=?, seen_count=seen_count+1 WHERE source=? AND job_id=?",
            (now.isoformat(), job.source, job.job_id),
        )

    def insert(self, job: Job, now: datetime, reasons: list[str], notified: bool) -> None:
        ts = now.isoformat()
        self.conn.execute(
            "INSERT INTO jobs (source, job_id, fingerprint, company_key, title, company, url,"
            " first_seen, last_seen, reasons, notified) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (job.source, job.job_id, job.fingerprint, job.company_key, job.title, job.company,
             job.url, ts, ts, "; ".join(reasons), int(notified)),
        )

    def fingerprint_count(self, fingerprint: str) -> int:
        """이 공고(회사+제목)가 다른 id로 이미 몇 번 올라왔었는지."""
        (n,) = self.conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE fingerprint=?", (fingerprint,)
        ).fetchone()
        return n

    def company_count(self, company_key: str, since: datetime) -> int:
        (n,) = self.conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE company_key=? AND first_seen>=?",
            (company_key, since.isoformat()),
        ).fetchone()
        return n

    def commit(self) -> None:
        self.conn.commit()

    def stats(self, days: int = 30, top: int = 15) -> dict:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        total, notified = self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(notified),0) FROM jobs"
        ).fetchone()
        top_companies = self.conn.execute(
            "SELECT company, COUNT(*) c FROM jobs WHERE first_seen>=? "
            "GROUP BY company_key ORDER BY c DESC LIMIT ?",
            (since, top),
        ).fetchall()
        return {"total": total, "notified": notified, "top_companies": top_companies}
