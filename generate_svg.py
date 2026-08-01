#!/usr/bin/env python3
"""
Generates dark_mode.svg and light_mode.svg — a neofetch-style GitHub profile
card with live stats pulled from the GitHub API.

Run manually:   python generate_svg.py
Run in CI:      GitHub Actions workflow does this automatically (see
                 .github/workflows/update-readme.yml)

Auth: set GITHUB_TOKEN in the environment to avoid low unauthenticated
rate limits. GitHub Actions provides this automatically via secrets.GITHUB_TOKEN.
"""

import os
import sys
import datetime
import requests

# ---------------------------------------------------------------------------
# EDIT THIS SECTION — your personal info (everything the API can't know)
# ---------------------------------------------------------------------------
CONFIG = {
    "username": os.environ.get("GH_USERNAME", "heyyoimsyaziq"),
    "os": "Ubuntu 24.04.1 LTS",
    "host": "Your City, Your Country",
    "birthdate": "2003-01-01",  # YYYY-MM-DD, used to compute "Uptime" (age)
    "role": "Student / Junior Developer",
    "ide": "VSCode",
    "languages_programming": "Python, JavaScript",
    "languages_computer": "HTML, CSS, JSON",
    "languages_real": "English, Malay",
    "hobbies": "Gaming, Reading",
    "interests": "Software Engineering, AI",
    "email": "you@example.com",
    "linkedin": "your-linkedin-handle",
}

GITHUB_API = "https://api.github.com"


def gh_headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_uptime(birthdate_str):
    birth = datetime.date.fromisoformat(birthdate_str)
    today = datetime.date.today()
    years = today.year - birth.year
    months = today.month - birth.month
    days = today.day - birth.day
    if days < 0:
        months -= 1
        # approximate days in previous month
        days += 30
    if months < 0:
        years -= 1
        months += 12
    return f"{years} years, {months} months, {days} days"


def fetch_user(username):
    r = requests.get(f"{GITHUB_API}/users/{username}", headers=gh_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_all_repos(username):
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=gh_headers(),
            params={"per_page": 100, "page": page, "type": "owner"},
            timeout=15,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def fetch_commit_count(username):
    """Uses the commit search API. Only counts commits on the default
    branch of repos GitHub has indexed, so this is an approximation."""
    r = requests.get(
        f"{GITHUB_API}/search/commits",
        headers=gh_headers(),
        params={"q": f"author:{username}"},
        timeout=15,
    )
    if r.status_code != 200:
        return 0
    return r.json().get("total_count", 0)


def fetch_lines_of_code(username, repos):
    """Sums additions/deletions across owned, non-fork repos using the
    contributor-stats API. GitHub computes these stats asynchronously —
    on a repo's first request it may return 202 (not ready yet), in which
    case that repo is skipped for this run."""
    additions = 0
    deletions = 0
    for repo in repos:
        if repo.get("fork"):
            continue
        name = repo["name"]
        r = requests.get(
            f"{GITHUB_API}/repos/{username}/{name}/stats/contributors",
            headers=gh_headers(),
            timeout=15,
        )
        if r.status_code != 200:
            continue
        for contributor in r.json() or []:
            if contributor.get("author", {}).get("login") != username:
                continue
            for week in contributor.get("weeks", []):
                additions += week.get("a", 0)
                deletions += week.get("d", 0)
    return additions, deletions


def build_stats():
    username = CONFIG["username"]
    user = fetch_user(username)
    repos = fetch_all_repos(username)

    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    commit_count = fetch_commit_count(username)
    additions, deletions = fetch_lines_of_code(username, repos)

    return {
        "uptime": get_uptime(CONFIG["birthdate"]),
        "repos": user.get("public_repos", len(repos)),
        "stars": total_stars,
        "commits": commit_count,
        "followers": user.get("followers", 0),
        "additions": additions,
        "deletions": deletions,
    }


# ---------------------------------------------------------------------------
# SVG rendering
# ---------------------------------------------------------------------------

def render_svg(stats, theme="dark"):
    if theme == "dark":
        bg = "#0d1117"
        fg = "#c9d1d9"
        key = "#79c0ff"
        accent = "#7ee787"
        dim = "#8b949e"
        art_stroke = "#30363d"
    else:
        bg = "#ffffff"
        fg = "#24292f"
        key = "#0969da"
        accent = "#1a7f37"
        dim = "#57606a"
        art_stroke = "#d0d7de"

    lines = [
        (f"{CONFIG['username']}@github", None, "header"),
        ("-" * 46, None, "rule"),
        ("OS", CONFIG["os"], "kv"),
        ("Uptime", stats["uptime"], "kv"),
        ("Host", CONFIG["host"], "kv"),
        ("Role", CONFIG["role"], "kv"),
        ("IDE", CONFIG["ide"], "kv"),
        ("Languages.Programming", CONFIG["languages_programming"], "kv"),
        ("Languages.Computer", CONFIG["languages_computer"], "kv"),
        ("Languages.Real", CONFIG["languages_real"], "kv"),
        ("Hobbies", CONFIG["hobbies"], "kv"),
        ("Interests", CONFIG["interests"], "kv"),
        ("", None, "blank"),
        ("Contact", None, "section"),
        ("Email", CONFIG["email"], "kv"),
        ("LinkedIn", CONFIG["linkedin"], "kv"),
        ("", None, "blank"),
        ("GitHub Stats", None, "section"),
        ("Repos", str(stats["repos"]), "kv"),
        ("Stars", str(stats["stars"]), "kv"),
        ("Commits", str(stats["commits"]), "kv"),
        ("Followers", str(stats["followers"]), "kv"),
        (
            "Lines of Code",
            f"{stats['additions'] + stats['deletions']:,} (+{stats['additions']:,} / -{stats['deletions']:,})",
            "kv",
        ),
    ]

    line_height = 22
    top_pad = 40
    left_pad = 220
    width = 900
    height = top_pad * 2 + line_height * len(lines)

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="100%" height="100%" fill="{bg}" rx="10"/>',
        # simple decorative geometric mark (avoids using any copyrighted character art)
        f'<g stroke="{art_stroke}" stroke-width="2" fill="none">',
        f'<circle cx="100" cy="{height/2}" r="70"/>',
        f'<circle cx="100" cy="{height/2}" r="45"/>',
        f'<circle cx="100" cy="{height/2}" r="20"/>',
        f'<line x1="30" y1="{height/2}" x2="170" y2="{height/2}"/>',
        f'<line x1="100" y1="{height/2-70}" x2="100" y2="{height/2+70}"/>',
        "</g>",
        f'<g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="14">',
    ]

    y = top_pad
    for text, value, kind in lines:
        if kind == "header":
            svg_lines.append(f'<text x="{left_pad}" y="{y}" fill="{fg}" font-weight="700">{text}</text>')
        elif kind == "rule":
            svg_lines.append(f'<text x="{left_pad}" y="{y}" fill="{dim}">{text}</text>')
        elif kind == "section":
            svg_lines.append(f'<text x="{left_pad}" y="{y}" fill="{accent}" font-weight="700">- {text} -</text>')
        elif kind == "kv":
            dots = "." * max(3, 28 - len(text))
            svg_lines.append(
                f'<text x="{left_pad}" y="{y}">'
                f'<tspan fill="{key}" font-weight="600">{text}</tspan>'
                f'<tspan fill="{dim}">: {dots} </tspan>'
                f'<tspan fill="{fg}">{value}</tspan>'
                f"</text>"
            )
        y += line_height

    svg_lines.append("</g>")
    svg_lines.append("</svg>")
    return "\n".join(svg_lines)


def main():
    try:
        stats = build_stats()
    except requests.HTTPError as e:
        print(f"GitHub API error: {e}", file=sys.stderr)
        sys.exit(1)

    with open("dark_mode.svg", "w") as f:
        f.write(render_svg(stats, "dark"))
    with open("light_mode.svg", "w") as f:
        f.write(render_svg(stats, "light"))

    print("Generated dark_mode.svg and light_mode.svg")
    print(stats)


if __name__ == "__main__":
    main()
