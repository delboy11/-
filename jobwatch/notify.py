from __future__ import annotations

import os
from abc import ABC, abstractmethod

import requests

from .models import Job


def format_job(job: Job) -> str:
    lines = [f"🆕 {job.title}", f"🏢 {job.company or '-'}"]
    if job.location:
        lines.append(f"📍 {job.location}")
    if job.url:
        lines.append(job.url)
    return "\n".join(lines)


class Notifier(ABC):
    @abstractmethod
    def send(self, job: Job) -> None:
        ...


class ConsoleNotifier(Notifier):
    def send(self, job: Job) -> None:
        print(format_job(job), end="\n\n", flush=True)


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        if not (self.bot_token and self.chat_id):
            raise ValueError("텔레그램 bot_token / chat_id가 필요합니다")

    def send(self, job: Job) -> None:
        requests.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={"chat_id": self.chat_id, "text": format_job(job), "disable_web_page_preview": True},
            timeout=10,
        ).raise_for_status()


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")
        if not self.webhook_url:
            raise ValueError("디스코드 webhook_url이 필요합니다")

    def send(self, job: Job) -> None:
        requests.post(self.webhook_url, json={"content": format_job(job)}, timeout=10).raise_for_status()


NOTIFIER_TYPES: dict[str, type[Notifier]] = {
    "console": ConsoleNotifier,
    "telegram": TelegramNotifier,
    "discord": DiscordNotifier,
}


def build_notifier(spec: dict) -> Notifier:
    spec = dict(spec)
    kind = spec.pop("type")
    if kind not in NOTIFIER_TYPES:
        raise ValueError(f"알 수 없는 알림 type: {kind!r} (가능: {', '.join(NOTIFIER_TYPES)})")
    return NOTIFIER_TYPES[kind](**spec)
