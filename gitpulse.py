#!/usr/bin/env python3
"""gitpulse - GitHub contribution analyzer with terminal heatmap."""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

CACHE_DIR = os.path.expanduser("~/.cache/gitpulse")
CACHE_TTL_HOURS = 2

# ── GitHub GraphQL ──────────────────────────────────────────────

GQL_ENDPOINT = "https://api.github.com/graphql"

CONTRIB_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes {
        name
        stargazerCount
        forkCount
        primaryLanguage { name color }
        description
        url
      }
    }
    pullRequests(first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
      totalCount
      nodes {
        title
        state
        mergedAt
        createdAt
        repository { name }
        url
      }
    }
    issues(first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
      totalCount
      nodes {
        title
        state
        createdAt
        repository { name }
        url
      }
    }
  }
}
"""

# ── ANSI Helpers ────────────────────────────────────────────────

GREEN_SCALE = [232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85]

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def green_bg(level: int) -> str:
    """Return ANSI escape for green background at intensity 0..63."""
    idx = min(level, 63)
    return f"\033[48;5;{GREEN_SCALE[idx]}m"


def gray_bg() -> str:
    return "\033[48;5;235m"


def empty_cell() -> str:
    return f"{gray_bg()}  {RESET}"


# ── Cache ───────────────────────────────────────────────────────

def cache_path(username: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{username}.json")


def load_cache(username: str) -> dict | None:
    path = cache_path(username)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    age = datetime.now().timestamp() - os.path.getmtime(path)
    if age > CACHE_TTL_HOURS * 3600:
        return None
    return data


def save_cache(username: str, data: dict) -> None:
    with open(cache_path(username), "w") as f:
        json.dump(data, f)


# ── Fetch ───────────────────────────────────────────────────────

def fetch_github(username: str, token: str | None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    now = datetime.now(timezone.utc)
    one_year_ago = now - timedelta(days=365)

    payload = {
        "query": CONTRIB_QUERY,
        "variables": {
            "login": username,
            "from": one_year_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }
    resp = requests.post(GQL_ENDPOINT, json=payload, headers=headers, timeout=30)
    if resp.status_code == 401:
        print("Error: Bad credentials. Set GITHUB_TOKEN or use --token.", file=sys.stderr)
        sys.exit(1)
    if resp.status_code != 200:
        print(f"Error: GitHub API returned {resp.status_code}", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        sys.exit(1)
    result = resp.json()
    if "errors" in result:
        for err in result["errors"]:
            print(f"  {err['message']}", file=sys.stderr)
        sys.exit(1)
    return result["data"]


# ── Heatmap Render ──────────────────────────────────────────────

def render_heatmap(data: dict) -> str:
    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    total = cal["totalContributions"]

    # Build date -> count map
    day_map: dict[str, int] = {}
    max_count = 0
    for week in weeks:
        for day in week["contributionDays"]:
            day_map[day["date"]] = day["contributionCount"]
            if day["contributionCount"] > max_count:
                max_count = day["contributionCount"]

    # Determine date range
    all_dates = sorted(day_map.keys())
    if not all_dates:
        return "No contribution data found."

    start = datetime.fromisoformat(all_dates[0])
    end = datetime.fromisoformat(all_dates[-1])

    # Build grid: rows = days of week (Sun=0..Sat=6), cols = weeks
    num_weeks = (end - start).days // 7 + 2
    grid: list[list[str | None]] = [[None] * num_weeks for _ in range(7)]

    current = start
    # Align to Sunday
    while current.weekday() != 6:
        current -= timedelta(days=1)

    col = 0
    for _ in range(num_weeks):
        for row in range(7):
            date_str = current.strftime("%Y-%m-%d")
            if date_str in day_map:
                cnt = day_map[date_str]
                if max_count > 0:
                    level = int(cnt / max_count * 63)
                else:
                    level = 0
                grid[row][col] = green_bg(level) + "  " + RESET
            else:
                grid[row][col] = empty_cell()
            current += timedelta(days=1)
        col += 1

    # Month labels
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    lines = []
    lines.append(f"\n{BOLD}  {username}'s Contribution Heatmap{RESET}")
    lines.append(f"  {total} contributions in the last year\n")

    # Render with day labels on left
    day_labels = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
    for row in range(7):
        line = f"  {DIM}{day_labels[row]}{RESET} "
        for col in range(num_weeks):
            cell = grid[row][col]
            line += (cell if cell else empty_cell())
        lines.append(line)

    # Legend
    lines.append(f"\n  {DIM}Less{empty_cell()}{green_bg(20)}  {RESET}{green_bg(40)}  {RESET}{green_bg(60)}  {RESET}{DIM}More{RESET}")

    return "\n".join(lines)


# ── Stats Render ────────────────────────────────────────────────

def render_stats(data: dict) -> str:
    user_data = data["user"]
    repos = user_data["repositories"]["nodes"]
    prs = user_data["pullRequests"]["nodes"]
    issues = user_data["issues"]["nodes"]

    total_stars = sum(r["stargazerCount"] for r in repos)
    total_forks = sum(r["forkCount"] for r in repos)

    # Language breakdown
    lang_count: dict[str, int] = defaultdict(int)
    for r in repos:
        lang = r["primaryLanguage"]["name"] if r["primaryLanguage"] else "Unknown"
        lang_count[lang] += 1
    top_langs = sorted(lang_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # PR stats
    merged = sum(1 for p in prs if p["mergedAt"])
    open_prs = sum(1 for p in prs if p["state"] == "OPEN")

    lines = []
    lines.append(f"\n{BOLD}  Repository Stats{RESET}")
    lines.append(f"  ├─ Public repos : {user_data['repositories']['totalCount']}")
    lines.append(f"  ├─ Total stars  : {total_stars}")
    lines.append(f"  ├─ Total forks  : {total_forks}")
    lines.append(f"  ├─ PRs merged   : {merged}")
    lines.append(f"  ├─ PRs open     : {open_prs}")
    lines.append(f"  ├─ Issues filed : {user_data['issues']['totalCount']}")
    lines.append(f"  └─ Top languages: {', '.join(f'{l}({c})' for l, c in top_langs)}")

    # Top repos
    lines.append(f"\n{BOLD}  Top Repositories{RESET}")
    for i, r in enumerate(repos[:5], 1):
        stars = f"{r['stargazerCount']}★"
        lang = r["primaryLanguage"]["name"] if r["primaryLanguage"] else "—"
        desc = (r["description"] or "")[:60]
        lines.append(f"  {i}. {BOLD}{r['name']}{RESET}  {stars}  {lang}  {desc}")

    # Recent PRs
    lines.append(f"\n{BOLD}  Recent Pull Requests{RESET}")
    for p in prs[:5]:
        status = "✓ merged" if p["mergedAt"] else "○ open" if p["state"] == "OPEN" else "✗ closed"
        lines.append(f"  {status}  {p['title'][:60]}  ({p['repository']['name']})")

    return "\n".join(lines)


# ── HTML Export ─────────────────────────────────────────────────

def export_html(data: dict, output_path: str, username: str) -> None:
    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]

    cells_html = ""
    for week in weeks:
        for day in week["contributionDays"]:
            cnt = day["contributionCount"]
            color = day["color"]
            date = day["date"]
            title = f"{cnt} contributions on {date}"
            cells_html += f'<td data-date="{date}" title="{title}" style="background-color:{color};width:12px;height:12px;border-radius:2px"></td>'
        cells_html += "\n"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>gitpulse — {username}</title>
<style>
  body {{ background:#0d1117; color:#c9d1d9; font-family:-apple-system,BlinkMacSystemFont,sans-serif; padding:40px; max-width:900px; margin:auto; }}
  h1 {{ color:#58a6ff; }}
  table {{ border-spacing:3px; }}
  td {{ width:12px; height:12px; border-radius:2px; }}
  .stat {{ color:#8b949e; }}
  .value {{ color:#c9d1d9; font-weight:bold; }}
</style>
</head>
<body>
<h1>gitpulse report for @{username}</h1>
<p>{cal['totalContributions']} contributions in the last year</p>
<table>{cells_html}</table>
<p style="margin-top:24px;color:#8b949e;font-size:12px">Generated by <a href="https://github.com/gitpulse" style="color:#58a6ff">gitpulse</a></p>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"  HTML report saved to {output_path}")


# ── CLI ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="gitpulse — GitHub contribution analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("username", nargs="?", help="GitHub username (default: from GITHUB_USER env)")
    parser.add_argument("--token", help="GitHub personal access token (or set GITHUB_TOKEN env)")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache, force fresh fetch")
    parser.add_argument("--html", metavar="PATH", help="Export heatmap as standalone HTML file")
    parser.add_argument("--json", metavar="PATH", help="Export raw data as JSON")
    args = parser.parse_args()

    username = args.username or os.environ.get("GITHUB_USER")
    if not username:
        print("Error: provide a username or set GITHUB_USER env var.", file=sys.stderr)
        sys.exit(1)

    token = args.token or os.environ.get("GITHUB_TOKEN")

    # Try cache
    data = None
    if not args.no_cache:
        data = load_cache(username)
        if data:
            print(f"  (using cached data, {CACHE_TTL_HOURS}h TTL)")

    if data is None:
        print(f"  Fetching data for @{username} ...")
        data = fetch_github(username, token)
        save_cache(username, data)

    # Render
    print(render_heatmap(data))
    print(render_stats(data))

    # Export
    if args.json:
        with open(args.json, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n  JSON exported to {args.json}")

    if args.html:
        export_html(data, args.html, username)


if __name__ == "__main__":
    main()
