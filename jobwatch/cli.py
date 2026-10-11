from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from .config import load_config
from .filters import EvergreenFilter, FilterConfig
from .notify import build_notifier
from .runner import run_once
from .sources import build_source
from .store import Store


def _setup(cfg: dict):
    store = Store(cfg.get("db", "jobwatch.db"))
    sources = [build_source(s) for s in cfg.get("sources", [])]
    if not sources:
        sys.exit("설정에 sources가 하나도 없습니다")
    notifiers = [build_notifier(n) for n in cfg.get("notifiers", [{"type": "console"}])]
    flt = EvergreenFilter(FilterConfig.from_dict(cfg.get("filter")), store)
    return store, sources, notifiers, flt


def _run(store, sources, notifiers, flt, baseline: bool, verbose: bool) -> None:
    first = store.stats()["total"] == 0
    if first and not baseline:
        logging.info("DB가 비어 있어서 이번 회차는 기록만 합니다 (기존 공고 폭탄 알림 방지)")
    res = run_once(sources, store, flt, notifiers, baseline=baseline or first)
    logging.info("가져옴 %d · 이미 본 것 %d · 새 공고 %d · 걸러냄 %d · 오류 %d",
                 res.fetched, res.already_seen, len(res.new), len(res.skipped), len(res.errors))
    if verbose:
        for job, reasons in res.skipped:
            logging.info("  ✗ %s / %s — %s", job.company, job.title, "; ".join(reasons))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="jobwatch", description="상주 공고는 거르고 새 공고만 알림")
    p.add_argument("-c", "--config", default="config.yaml")
    p.add_argument("-v", "--verbose", action="store_true", help="걸러진 공고와 이유도 출력")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="한 번 확인")
    r.add_argument("--baseline", action="store_true", help="알림 없이 현재 공고만 기록")

    w = sub.add_parser("watch", help="주기적으로 계속 확인")
    w.add_argument("-i", "--interval", type=int, default=None, help="초 단위 (기본: 설정의 interval_seconds 또는 600)")

    s = sub.add_parser("stats", help="DB 통계 (어느 회사가 공고를 쏟아내는지)")
    s.add_argument("--days", type=int, default=30)

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    if not Path(args.config).exists():
        sys.exit(f"설정 파일 {args.config} 이 없습니다. config.example.yaml을 복사해서 만드세요.")
    cfg = load_config(args.config)

    if args.cmd == "stats":
        st = Store(cfg.get("db", "jobwatch.db")).stats(days=args.days)
        print(f"전체 {st['total']}건 · 알림 보낸 것 {st['notified']}건")
        print(f"최근 {args.days}일 공고 많은 회사:")
        for company, n in st["top_companies"]:
            print(f"  {n:4d}  {company}")
        return

    store, sources, notifiers, flt = _setup(cfg)
    try:
        if args.cmd == "run":
            _run(store, sources, notifiers, flt, args.baseline, args.verbose)
        else:
            interval = args.interval or int(cfg.get("interval_seconds", 600))
            while True:
                _run(store, sources, notifiers, flt, False, args.verbose)
                time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        store.close()


if __name__ == "__main__":
    main()
