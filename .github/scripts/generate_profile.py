#!/usr/bin/env python3
"""Draw the profile charts from GitHub and WakaTime.

Public contribution calendars omit commits in private repositories unless the
profile setting is on. This script counts those commits on the default branch
and adds the dates to the chart. Repository names are never written into the SVG.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = os.environ.get("PROFILE_LOGIN", "kiki3231").strip() or "kiki3231"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "profile"
MANIFEST = OUT / "manifest.json"
API = "https://api.github.com/graphql"
WAKATIME_URL = "https://wakatime.com/api/v1/users/current/stats/last_7_days"
TZ = timezone(timedelta(hours=8))
WIDTH = 720

MARKUP = {
    "HTML",
    "CSS",
    "SCSS",
    "Less",
    "Sass",
    "Shell",
    "PowerShell",
    "Batchfile",
    "Dockerfile",
    "Makefile",
    "Procfile",
    "CMake",
}


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    ink: str
    muted: str
    line: str
    empty: str
    scale: tuple[str, str, str, str]
    track: str
    fill: str


LIGHT = Theme(
    name="light",
    bg="#F7FAFB",
    ink="#172430",
    muted="#3C5364",
    line="#D3E0E8",
    empty="#E4EEF3",
    scale=("#C9DCE8", "#7EADC4", "#2C6C8F", "#14364A"),
    track="#E4EEF3",
    fill="#2C6C8F",
)
DARK = Theme(
    name="dark",
    bg="#0E141B",
    ink="#E7EEF4",
    muted="#C5D5E0",
    line="#2A3A48",
    empty="#1B242E",
    scale=("#1C3D52", "#2C6B8A", "#8EC4DC", "#E5F3FA"),
    track="#1B242E",
    fill="#8EC4DC",
)
THEMES = (LIGHT, DARK)
USE_GH = False

FONT = "'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
DISPLAY = "Georgia, 'Iowan Old Style', 'Palatino Linotype', Palatino, serif"


def graphql(query: str, token: str, variables: dict | None = None) -> dict:
    global USE_GH
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    raw = json.dumps(payload).encode()
    body = None
    if not USE_GH:
        try:
            req = urllib.request.Request(
                API,
                data=raw,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "User-Agent": "kiki3231-profile",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.load(resp)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:240]
            raise RuntimeError(f"GitHub API {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError):
            USE_GH = True
    if body is None:
        env = os.environ.copy()
        env["GH_TOKEN"] = token
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env.pop(key, None)
        completed = subprocess.run(
            ["gh", "api", "graphql", "--input", "-"],
            input=raw,
            capture_output=True,
            env=env,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", "replace")[:240]
            raise RuntimeError(f"gh api graphql failed: {detail}") from None
        body = json.loads(completed.stdout.decode("utf-8"))
    if body.get("errors"):
        message = body["errors"][0].get("message", "graphql error")
        raise RuntimeError(message)
    return body["data"]


def token_works(token: str) -> bool:
    try:
        graphql("query { viewer { login } }", token)
    except RuntimeError as exc:
        print(f"token skipped: {exc}")
        return False
    return True


def choose_token() -> str:
    seen: set[str] = set()
    for name in ("PAT_TOKEN", "GH_TOKEN", "GITHUB_TOKEN", "GH_FALLBACK_TOKEN"):
        token = os.environ.get(name, "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        if token_works(token):
            print(f"using {name}")
            return token
    raise SystemExit("no working GitHub token")


def fetch_public(token: str) -> dict:
    query = """
    query($login: String!) {
      user(login: $login) {
        id
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays { date contributionCount }
            }
          }
        }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
          nodes {
            name
            stargazerCount
            languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name color } }
            }
          }
        }
      }
    }
    """
    return graphql(query, token, {"login": LOGIN})["user"]


def fetch_private_days(token: str, author_id: str, since: str) -> tuple[Counter, int] | None:
    """Return commit counts by local date, or None when private repos are hidden.

    Repository names stay in memory for the API call and are not printed.
    Actions logs for this public repository are public.
    """
    listed = graphql(
        """
        query($login: String!) {
          user(login: $login) {
            repositories(first: 50, ownerAffiliations: OWNER, isFork: false, privacy: PRIVATE) {
              nodes { name }
            }
          }
        }
        """,
        token,
        {"login": LOGIN},
    )
    repos = [node["name"] for node in listed["user"]["repositories"]["nodes"] if node.get("name")]
    if not repos:
        print("private repositories are not visible to this token")
        return None

    counts: Counter = Counter()
    total = 0
    history = """
    query($owner: String!, $name: String!, $since: GitTimestamp!, $author: ID!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 100, after: $cursor, since: $since, author: {id: $author}) {
                pageInfo { hasNextPage endCursor }
                nodes { authoredDate }
              }
            }
          }
        }
      }
    }
    """
    for name in repos:
        cursor = None
        repo_total = 0
        for _ in range(20):
            data = graphql(
                history,
                token,
                {
                    "owner": LOGIN,
                    "name": name,
                    "since": since,
                    "author": author_id,
                    "cursor": cursor,
                },
            )
            ref = (data.get("repository") or {}).get("defaultBranchRef")
            target = (ref or {}).get("target") or {}
            page = (target.get("history") or {})
            for node in page.get("nodes") or []:
                raw = node.get("authoredDate")
                if not raw:
                    continue
                local = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(TZ).date().isoformat()
                counts[local] += 1
                repo_total += 1
            if not page.get("pageInfo", {}).get("hasNextPage"):
                break
            cursor = page["pageInfo"]["endCursor"]
        total += repo_total
    print(f"private commits {total}")
    return counts, total


def level(count: int) -> int:
    if count <= 0:
        return 0
    if count == 1:
        return 1
    if count <= 3:
        return 2
    if count <= 6:
        return 3
    return 4


def streaks(days: list[dict]) -> tuple[int, int]:
    counts = [day["contributionCount"] for day in days]
    longest = current = 0
    for count in counts:
        if count > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    active = 0
    end = len(counts) - 1
    if counts and counts[-1] == 0 and end > 0:
        end -= 1
    for count in reversed(counts[: end + 1]):
        if count <= 0:
            break
        active += 1
    if counts and counts[-1] == 0 and (end < 0 or counts[end] == 0):
        active = 0
    return active, longest


def languages(repos: list[dict]) -> list[dict]:
    sizes: dict[str, int] = {}
    colors: dict[str, str] = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + edge["size"]
            if edge["node"].get("color"):
                colors[name] = edge["node"]["color"]
    total = sum(sizes.values()) or 1
    ranked = [item for item in sorted(sizes.items(), key=lambda item: item[1], reverse=True) if item[0] not in MARKUP][:6]
    return [
        {
            "name": name,
            "percent": size / total * 100,
            "color": colors.get(name) or LIGHT.fill,
        }
        for name, size in ranked
    ]


def stamp_now() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M CST")


def svg_open(width: int, height: int, label: str, theme: Theme) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">
  <title>{escape(label)}</title>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="{theme.bg}" stroke="{theme.line}"/>"""


def svg_close() -> str:
    return "\n</svg>\n"


GREEN = {
    "light": ("#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"),
    "dark": ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"),
}


def zh_duration(text: str) -> str:
    import re

    hours = re.search(r"(\d+)\s*hrs?", text or "")
    minutes = re.search(r"(\d+)\s*mins?", text or "")
    if not hours and not minutes:
        return text
    parts = []
    if hours and int(hours.group(1)):
        parts.append(f"{int(hours.group(1))} 小时")
    if minutes and int(minutes.group(1)):
        parts.append(f"{int(minutes.group(1))} 分钟")
    return " ".join(parts) or "0 分钟"


def render_contrib(theme: Theme, weeks: list[list[dict]], summary: str, total: int, generated: str) -> str:
    cell, gap = 10, 2
    step = cell + gap
    grid_x = 40
    grid_y = 72
    height = 228
    parts = [svg_open(WIDTH, height, f"过去一年 {total} 次贡献", theme)]
    parts.append(
        f"""
  <text x="24" y="38" fill="{theme.ink}" font-family="{FONT}" font-size="18" font-weight="600">过去一年</text>
  <text x="{WIDTH - 24}" y="40" text-anchor="end" fill="{theme.ink}" font-family="{DISPLAY}" font-size="26">{total}</text>"""
    )
    weekdays = ["", "一", "", "三", "", "五", ""]
    for index, label in enumerate(weekdays):
        if not label:
            continue
        y = grid_y + index * step + 9
        parts.append(
            f"""
  <text x="22" y="{y}" text-anchor="end" fill="{theme.muted}" font-family="{FONT}" font-size="10">{label}</text>"""
        )
    for index, week in enumerate(weeks):
        if any(datetime.fromisoformat(day["date"]).day == 1 for day in week):
            month = next(
                datetime.fromisoformat(day["date"]).month
                for day in week
                if datetime.fromisoformat(day["date"]).day == 1
            )
            parts.append(
                f"""
  <text x="{grid_x + index * step}" y="60" fill="{theme.muted}" font-family="{FONT}" font-size="11">{month}月</text>"""
            )
    greens = GREEN[theme.name]
    for week_index, week in enumerate(weeks):
        for day_index, day in enumerate(week):
            count = day["contributionCount"]
            shade = greens[0] if count <= 0 else greens[level(count)]
            x = grid_x + week_index * step
            y = grid_y + day_index * step
            parts.append(
                f"""
  <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{shade}"><title>{escape(day["date"])} · {count}</title></rect>"""
            )
    legend_x = WIDTH - 24 - 5 * 14 - 28
    parts.append(
        f"""
  <text x="24" y="186" fill="{theme.ink}" font-family="{FONT}" font-size="13">{escape(summary)}</text>
  <text x="24" y="210" fill="{theme.muted}" font-family="{FONT}" font-size="12">更新于 {escape(generated)}</text>
  <text x="{legend_x - 8}" y="210" text-anchor="end" fill="{theme.muted}" font-family="{FONT}" font-size="11">少</text>"""
    )
    for index, color in enumerate(greens):
        parts.append(
            f"""
  <rect x="{legend_x + index * 14}" y="200" width="10" height="10" rx="2" fill="{color}"/>"""
        )
    parts.append(
        f"""
  <text x="{legend_x + 5 * 14 + 4}" y="210" fill="{theme.muted}" font-family="{FONT}" font-size="11">多</text>"""
    )
    parts.append(svg_close())
    return "".join(parts)


def render_bars(
    theme: Theme,
    title: str,
    label: str,
    rows: list[tuple[str, str, float, str]],
    generated: str,
    stats: list[tuple[str, str]] | None = None,
) -> str:
    row_h = 32
    stats = stats or []
    rows_top = 108 if stats else 64
    height = rows_top + max(len(rows), 1) * row_h + 28
    parts = [svg_open(WIDTH, height, label, theme)]
    parts.append(
        f"""
  <text x="24" y="36" fill="{theme.ink}" font-family="{FONT}" font-size="18" font-weight="600">{escape(title)}</text>"""
    )
    for index, (stat_label, stat_value) in enumerate(stats[:2]):
        x = 24 + index * 220
        parts.append(
            f"""
  <text x="{x}" y="64" fill="{theme.muted}" font-family="{FONT}" font-size="12">{escape(stat_label)}</text>
  <text x="{x}" y="92" fill="{theme.ink}" font-family="{FONT}" font-size="22" font-weight="600">{escape(stat_value)}</text>"""
        )
    if not rows:
        parts.append(
            f"""
  <text x="24" y="{rows_top + 8}" fill="{theme.muted}" font-family="{FONT}" font-size="14" dominant-baseline="central">这段时间没有记录</text>"""
        )
    for index, (name, value, ratio, color) in enumerate(rows):
        center = rows_top + index * row_h + 16
        width = max(4, round(360 * max(0.0, min(ratio, 1.0))))
        parts.append(
            f"""
  <text x="24" y="{center}" fill="{theme.ink}" font-family="{FONT}" font-size="13" dominant-baseline="central">{escape(name)}</text>
  <text x="{WIDTH - 24}" y="{center}" text-anchor="end" fill="{theme.muted}" font-family="{FONT}" font-size="12" dominant-baseline="central">{escape(value)}</text>
  <rect x="156" y="{center - 4}" width="360" height="8" rx="4" fill="{theme.track}"/>
  <rect x="156" y="{center - 4}" width="{width}" height="8" rx="4" fill="{color}"/>"""
        )
    parts.append(
        f"""
  <text x="24" y="{height - 16}" fill="{theme.muted}" font-family="{FONT}" font-size="12">更新于 {escape(generated)}</text>"""
    )
    parts.append(svg_close())
    return "".join(parts)


def write_pair(stem: str, render) -> None:
    for theme in THEMES:
        path = OUT / f"{stem}-{theme.name}.svg"
        path.write_text(render(theme), encoding="utf-8")
        text = path.read_text(encoding="utf-8").lower()
        if "<svg" not in text:
            raise SystemExit(f"{path.name} is empty")
        for bad in ("rate limit", "bad credentials", "something went wrong"):
            if bad in text:
                raise SystemExit(f"{path.name} contains an error message")


def load_manifest() -> dict:
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save_manifest(payload: dict) -> None:
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_github(token: str) -> None:
    user = fetch_public(token)
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = [week["contributionDays"] for week in calendar["weeks"]]
    days = [day for week in weeks for day in week]
    since_day = datetime.fromisoformat(days[0]["date"]) - timedelta(days=1)
    since = since_day.replace(tzinfo=TZ).isoformat()
    try:
        private = fetch_private_days(token, user["id"], since)
    except RuntimeError as exc:
        print(f"private contributions unavailable: {exc}")
        private = None
    previous = load_manifest()
    if private is None and previous.get("private_access") and os.environ.get("FORCE_PUBLIC") != "1":
        print("keeping the previous contribution chart; this token cannot see private repositories")
        return

    private_days: Counter = Counter()
    private_total = 0
    if private is not None:
        private_days, private_total = private
    window = {day["date"] for day in days}
    added = 0
    for day in days:
        extra = private_days.get(day["date"], 0)
        if extra:
            day["contributionCount"] += extra
            added += extra
    outside = sum(count for date, count in private_days.items() if date not in window)
    if outside:
        print(f"ignored {outside} private commits outside the chart window")
    current, longest = streaks(days)
    commits = user["contributionsCollection"]["totalCommitContributions"] + private_total
    stars = sum(repo["stargazerCount"] or 0 for repo in user["repositories"]["nodes"])
    total = sum(day["contributionCount"] for day in days)
    summary = f"当前连续 {current} 天 · 最长 {longest} 天 · 提交 {commits} · 星标 {stars}"
    if private_total:
        summary += " · 含未公开仓库"
    generated = stamp_now()
    print(
        f"contributions {total} commits {commits} private {private_total} "
        f"added-to-calendar {added} streak {current}/{longest} stars {stars}"
    )

    def draw(theme: Theme) -> str:
        return render_contrib(theme, weeks, summary, total, generated)

    write_pair("contrib", draw)
    langs = languages(user["repositories"]["nodes"])

    def draw_langs(theme: Theme) -> str:
        peak = max((item["percent"] for item in langs), default=1) or 1
        rows = [
            (item["name"], f"{item['percent']:.1f}%", item["percent"] / peak, item["color"])
            for item in langs
        ]
        return render_bars(theme, "公开仓库的语言", "公开仓库的语言占比", rows, generated)

    write_pair("languages", draw_langs)
    save_manifest(
        {
            "private_access": private is not None,
            "includes_private_commits": private_total > 0,
            "generated_at": generated,
        }
    )


def wakatime_stats(api_key: str) -> dict:
    import base64

    token = base64.b64encode(f"{api_key}:".encode()).decode()
    req = urllib.request.Request(
        WAKATIME_URL,
        headers={"Authorization": f"Basic {token}", "User-Agent": "kiki3231-profile"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["data"]


def write_wakatime(data: dict, generated: str) -> None:
    languages = (data.get("languages") or [])[:5]
    total_text = zh_duration(data.get("human_readable_total") or "0 mins")
    daily = zh_duration(data.get("human_readable_daily_average") or "0 mins")

    def draw(theme: Theme) -> str:
        rows = []
        for item in languages:
            percent = float(item.get("percent") or 0)
            rows.append(
                (
                    str(item.get("name") or "Other"),
                    zh_duration(str(item.get("text") or "")),
                    percent / 100,
                    theme.fill,
                )
            )
        return render_bars(
            theme,
            "编码时长",
            f"近 7 天编码 {total_text}",
            rows,
            generated,
            stats=[("近 7 天", total_text), ("日均", daily)],
        )

    write_pair("wakatime", draw)
    print(f"wakatime {total_text}")


def build_wakatime() -> None:
    api_key = os.environ.get("WAKATIME_API_KEY", "").strip()
    if not api_key:
        existing = OUT / "wakatime-light.svg"
        if existing.exists():
            print("WAKATIME_API_KEY missing; keeping the current coding-time chart")
            return
        write_wakatime({"human_readable_total": "等待密钥", "human_readable_daily_average": "—", "languages": []}, stamp_now())
        return
    try:
        write_wakatime(wakatime_stats(api_key), stamp_now())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:180]
        print(f"WakaTime API {exc.code}: {detail}")
        if not (OUT / "wakatime-light.svg").exists():
            raise SystemExit("WakaTime failed and no previous chart exists") from exc
        print("keeping the current coding-time chart")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    build_github(choose_token())
    build_wakatime()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
