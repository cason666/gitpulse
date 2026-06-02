# gitpulse

> Terminal heatmap + stats for any GitHub profile. Like `gh` meets `neofetch`.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

![](https://img.shields.io/badge/stars-0-important?style=social)

**gitpulse** fetches your GitHub contribution graph via GraphQL and renders it as a **full-color ANSI heatmap** right in your terminal — plus repo stats, language breakdown, PR history, and more.

```
  octocat's Contribution Heatmap
  1523 contributions in the last year

  Su ░░░░░░░░░░▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Mo ░░░░░░░░░░▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Tu ░░░░░░░░░▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  We ░░░░░░░░░▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Th ░░░░░░░░░░▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Fr ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Sa ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░

  Less ░░ ▓▓ ██ More
```

## Features

- **Terminal heatmap** — full 256-color ANSI grid matching GitHub's green scale
- **Repository stats** — stars, forks, language breakdown, top repos
- **PR & issue history** — merged/open/closed breakdown with recent activity
- **HTML export** — standalone heatmap page ready for your portfolio
- **JSON export** — raw GraphQL response for custom analysis
- **Smart caching** — 2-hour TTL, skip with `--no-cache`

## Install

```bash
git clone https://github.com/YOUR_USERNAME/gitpulse.git
cd gitpulse
pip install -r requirements.txt
```

## Usage

```bash
# Basic — uses GITHUB_USER env var
export GITHUB_USER=torvalds
python gitpulse.py

# With token (avoids rate limits, 5k req/hr vs 60)
export GITHUB_TOKEN=ghp_xxxx
python gitpulse.py torvalds

# Export HTML
python gitpulse.py torvalds --html report.html

# Export raw JSON
python gitpulse.py torvalds --json data.json

# Skip cache for live data
python gitpulse.py --no-cache
```

### GitHub Token (recommended)

Without a token, the unauthenticated rate limit is 60 requests/hour.  
Create a token at **Settings → Developer settings → Personal access tokens → Fine-grained tokens** (no scopes needed for public data).

## Example Output

```
  Repository Stats
  ├─ Public repos : 138
  ├─ Total stars  : 8420
  ├─ Total forks  : 3120
  ├─ PRs merged   : 456
  ├─ PRs open     : 12
  ├─ Issues filed : 89
  └─ Top languages: Python(42), JavaScript(28), Rust(15), Go(10), TypeScript(8)

  Top Repositories
  1. linux  2850★  C  Linux kernel source tree
  2. gitpulse  152★  Python  Terminal GitHub contribution heatmap
  ...

  Recent Pull Requests
  ✓ merged  Fix memory leak in scheduler  (linux)
  ○ open    Add ARM64 support  (gitpulse)
  ...
```

## Why This Exists

GitHub's profile page only shows a tiny contribution graph. I wanted:

1. A **full-year view** in one screen — no scrolling
2. **Context** — stars, PRs, issues alongside the heatmap
3. **Offline** — cache data, view anytime
4. **Portfolio-ready** — export an HTML card for your personal site

Built in a single evening with GitHub's GraphQL API. No framework, no bloat — just `requests` and ANSI escape codes.

## Roadmap

- [ ] Multiple profile comparison mode
- [ ] Weekly / monthly streak detection
- [ ] SVG export for README badges
- [ ] GitHub Actions integration (auto-update profile card)

## License

MIT — use it, fork it, ship it.
