"""Make one minimal request to the Claude API and dump every anthropic-* response
header. Use to discover the Claude Design / Sonnet-only / All-models / Opus
weekly-limit header names that Anthropic doesn't formally document."""

from __future__ import annotations

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))

import httpx
from poller import API_URL, API_HEADERS_TEMPLATE, API_BODY, read_token


def main() -> None:
    token = read_token()
    if not token:
        raise SystemExit("No token available")
    headers = dict(API_HEADERS_TEMPLATE)
    headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=20.0) as c:
        r = c.post(API_URL, headers=headers, json=API_BODY)
    print(f"status: {r.status_code}")
    for k, v in sorted(r.headers.items()):
        if "anthropic" in k.lower() or "ratelimit" in k.lower():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
