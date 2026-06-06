"""Claude usage polling for Clawdmeter-Windows.

Ported from HermannBjorgvin/Clawdmeter daemon. The BLE/asyncio plumbing is
gone; this is a QThread that posts UsageSample objects via a Qt signal.

Token resolution order on Windows:
  1. CLAUDE_CREDENTIALS_PATH env var (explicit override)
  2. ~/.claude/.credentials.json (Claude Code default)
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from PySide6.QtCore import QThread, Signal

API_URL = "https://api.anthropic.com/v1/messages"
API_HEADERS_TEMPLATE = {
    "anthropic-version": "2023-06-01",
    "anthropic-beta": "oauth-2025-04-20",
    "Content-Type": "application/json",
    "User-Agent": "claude-code/2.1.5",
}
API_BODY = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 1,
    "messages": [{"role": "user", "content": "hi"}],
}

DEFAULT_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"
POLL_INTERVAL_SECONDS = 60


@dataclass
class UsageSample:
    """One snapshot of Claude rate-limit state. Mirrors the BLE payload."""

    session_pct: int
    session_reset_minutes: int
    weekly_pct: int
    weekly_reset_minutes: int
    status: str
    ok: bool
    error: str | None = None
    timestamp: float = 0.0


def credentials_path() -> Path:
    override = os.environ.get("CLAUDE_CREDENTIALS_PATH")
    return Path(override) if override else DEFAULT_CREDENTIALS_PATH


def _extract_access_token(blob: str) -> str | None:
    """Pull accessToken from a credentials blob — JSON, nested JSON, or raw."""
    blob = blob.strip()
    if not blob:
        return None
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        if isinstance(data.get("accessToken"), str):
            return data["accessToken"]
        for v in data.values():
            if isinstance(v, dict) and isinstance(v.get("accessToken"), str):
                return v["accessToken"]
    m = re.search(r'"accessToken"\s*:\s*"([^"]+)"', blob)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_\-.~+/=]{20,}", blob):
        return blob
    return None


def read_token() -> str | None:
    path = credentials_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return _extract_access_token(raw)


def _poll_once(token: str) -> UsageSample:
    """Make one rate-limit probe. Returns a sample with ok=False on failure."""
    headers = dict(API_HEADERS_TEMPLATE)
    headers["Authorization"] = f"Bearer {token}"
    now = time.time()
    try:
        with httpx.Client(timeout=20.0) as http:
            resp = http.post(API_URL, headers=headers, json=API_BODY)
    except httpx.HTTPError as exc:
        return UsageSample(0, 0, 0, 0, "error", False, str(exc), now)

    def hdr(name: str, default: str = "0") -> str:
        return resp.headers.get(name, default)

    def reset_minutes(reset_ts: str) -> int:
        try:
            r = float(reset_ts)
        except ValueError:
            return 0
        mins = (r - now) / 60.0
        return int(round(mins)) if mins > 0 else 0

    def pct(util: str) -> int:
        try:
            return int(round(float(util) * 100))
        except ValueError:
            return 0

    return UsageSample(
        session_pct=pct(hdr("anthropic-ratelimit-unified-5h-utilization")),
        session_reset_minutes=reset_minutes(hdr("anthropic-ratelimit-unified-5h-reset")),
        weekly_pct=pct(hdr("anthropic-ratelimit-unified-7d-utilization")),
        weekly_reset_minutes=reset_minutes(hdr("anthropic-ratelimit-unified-7d-reset")),
        status=hdr("anthropic-ratelimit-unified-5h-status", "unknown"),
        ok=True,
        error=None,
        timestamp=now,
    )


class UsagePoller(QThread):
    """Background polling thread. Emits sample(UsageSample) on every poll."""

    sample = Signal(UsageSample)

    def __init__(self, interval_seconds: int = POLL_INTERVAL_SECONDS, parent=None) -> None:
        super().__init__(parent)
        self._interval = interval_seconds
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:  # QThread entry
        while not self._stop:
            token = read_token()
            if not token:
                self.sample.emit(UsageSample(
                    0, 0, 0, 0, "no-token", False,
                    f"No token at {credentials_path()}", time.time(),
                ))
            else:
                self.sample.emit(_poll_once(token))
            for _ in range(self._interval):
                if self._stop:
                    return
                self.msleep(1000)
