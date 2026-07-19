#!/usr/bin/env python3
"""Generate a soft-pink WakaTime stats SVG for the profile README."""

from __future__ import annotations

import base64
import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

API_URL = "https://wakatime.com/api/v1/users/current/stats/last_7_days"
OUT_PATH = Path("profile/github-wakatime.svg")

BG = "#FFF8FB"
TITLE = "#C45C8A"
TEXT = "#333333"
MUTED = "#666666"
BAR_TRACK = "#F3D6E4"
BAR_FILL = "#D489B0"
ACCENT = "#E8A0BF"


def fetch_stats(api_key: str) -> dict:
    token = base64.b64encode(f"{api_key}:".encode()).decode()
    req = urllib.request.Request(
        API_URL,
        headers={
            "Authorization": f"Basic {token}",
            "User-Agent": "kiki3231-profile-wakatime",
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        payload = json.load(resp)
    return payload["data"]


def bar_width(percent: float, max_width: int = 220) -> float:
    return max(4.0, round(max_width * min(percent, 100.0) / 100.0, 1))


def render_svg(data: dict) -> str:
    total = escape(data.get("human_readable_total") or "0 mins")
    daily = escape(data.get("human_readable_daily_average") or "0 mins")
    languages = (data.get("languages") or [])[:5]

    rows = []
    y = 92
    for lang in languages:
        name = escape(str(lang.get("name") or "Other"))
        text = escape(str(lang.get("text") or "0 mins"))
        percent = float(lang.get("percent") or 0)
        width = bar_width(percent)
        rows.append(
            f"""
  <text x="28" y="{y}" fill="{TEXT}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13" font-weight="600">{name}</text>
  <text x="438" y="{y}" text-anchor="end" fill="{MUTED}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="12">{text}</text>
  <rect x="28" y="{y + 8}" width="410" height="8" rx="4" fill="{BAR_TRACK}"/>
  <rect x="28" y="{y + 8}" width="{width}" height="8" rx="4" fill="{BAR_FILL}"/>"""
        )
        y += 36

    height = max(195, y + 24)
    langs_block = "\n".join(rows) if rows else f"""
  <text x="28" y="110" fill="{MUTED}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">No coding activity in the last 7 days</text>"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="466" height="{height}" viewBox="0 0 466 {height}" role="img" aria-label="WakaTime stats">
  <title>WakaTime Stats (Last 7 Days)</title>
  <rect width="466" height="{height}" rx="8" fill="{BG}"/>
  <text x="28" y="36" fill="{TITLE}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="18" font-weight="700">WakaTime · Last 7 Days</text>
  <circle cx="420" cy="30" r="6" fill="{ACCENT}"/>
  <text x="28" y="64" fill="{TEXT}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">Total Coding: <tspan font-weight="700">{total}</tspan></text>
  <text x="250" y="64" fill="{TEXT}" font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">Daily Avg: <tspan font-weight="700">{daily}</tspan></text>
{langs_block}
</svg>
"""


def main() -> int:
    api_key = os.environ.get("WAKATIME_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("WAKATIME_API_KEY is missing")

    try:
        data = fetch_stats(api_key)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"WakaTime API error {exc.code}: {body}") from exc

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render_svg(data), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
