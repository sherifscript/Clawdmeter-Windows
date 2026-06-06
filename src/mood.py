"""Rate-of-change group selection — mirrors firmware/src/usage_rate.cpp.

The firmware computes session-percentage growth rate over a ring buffer and
maps it to 4 groups that pick the animation. This is a faithful port:

    rate < 0.10 %/min  -> 0 idle
    rate < 0.20 %/min  -> 1 normal
    rate < 0.33 %/min  -> 2 active
    rate >= 0.33       -> 3 heavy

A minimum 4-minute span is required before we trust a computed rate, so the
first few minutes after startup will sit in group 0. A session reset (pct
dropping by more than 5) clears the ring and re-arms the warmup.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

RING_SIZE = 6
MIN_WINDOW_SECONDS = 240.0
RATE_THRESH_NORMAL = 0.10
RATE_THRESH_ACTIVE = 0.20
RATE_THRESH_HEAVY = 0.33
SESSION_RESET_DROP = 5.0


@dataclass
class _Sample:
    t: float
    pct: float


GROUP_NAMES = {0: "idle", 1: "normal", 2: "active", 3: "heavy"}

# Animation roster per group — mirrors firmware/src/splash.cpp GROUP_NAMES.
GROUP_ANIMS: dict[int, list[str]] = {
    0: ["expression sleep", "idle breathe", "idle blink", "expression wink"],
    1: ["idle look around", "work think", "work coding"],
    2: ["dance sway", "expression surprise", "dance bounce"],
    3: ["dance bounce dj", "dance sway dj", "dance djmix"],
}


class RateGroupTracker:
    def __init__(self) -> None:
        self._ring: deque[_Sample] = deque(maxlen=RING_SIZE)

    def observe(self, session_pct: float) -> None:
        now = time.time()
        if self._ring and session_pct + SESSION_RESET_DROP < self._ring[-1].pct:
            self._ring.clear()
        self._ring.append(_Sample(now, float(session_pct)))

    def rate_per_minute(self) -> float | None:
        if len(self._ring) < 2:
            return None
        first, last = self._ring[0], self._ring[-1]
        dt = last.t - first.t
        if dt < MIN_WINDOW_SECONDS:
            return None
        dp = max(0.0, last.pct - first.pct)
        return dp * 60.0 / dt

    def group(self) -> int:
        r = self.rate_per_minute()
        if r is None:
            return 0
        if r < RATE_THRESH_NORMAL:
            return 0
        if r < RATE_THRESH_ACTIVE:
            return 1
        if r < RATE_THRESH_HEAVY:
            return 2
        return 3
