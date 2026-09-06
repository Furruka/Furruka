import os
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests


# ============================================================
# Configuration
# ============================================================

USER = os.environ["GITHUB_USER"]
TOKEN = os.environ["GITHUB_TOKEN"]

API = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Profile repository should never be counted as a development repo.
PROFILE_REPO = USER.lower()

# Limit API usage.
MAX_REPOSITORIES = 30
COMMITS_PER_REPOSITORY = 10
RECENT_COMMITS_TO_DISPLAY = 8


# ============================================================
# HTTP session
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


def api_get(url: str, params=None):
    """GET JSON data from GitHub API."""

    response = session.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


# ============================================================
# Repository discovery
# ============================================================

def get_repositories():
    """Get user's non-fork, non-archived repositories."""

    repositories = []

    for page in range(1, 11):
        data = api_get(
            f"{API}/users/{USER}/repos",
            {
                "type": "owner",
                "sort": "pushed",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            },
        )

        if not data:
            break

        repositories.extend(data)

        if len(data) < 100:
            break

    filtered = []

    for repo in repositories:
        name = repo.get("name", "")

        # Exclude:
        # - profile README repository
        # - forks
        # - archived repositories
        # - disabled repositories
        if name.lower() == PROFILE_REPO:
            continue

        if repo.get("fork"):
            continue

        if repo.get("archived"):
            continue

        if repo.get("disabled"):
            continue

        filtered.append(repo)

    return filtered


# ============================================================
# Commit discovery
# ============================================================

def get_repository_commits(repo):
    """Get recent commits authored by this GitHub user."""

    owner = repo["owner"]["login"]
    name = repo["name"]

    try:
        return api_get(
            f"{API}/repos/{owner}/{name}/commits",
            {
                "author": USER,
                "per_page": COMMITS_PER_REPOSITORY,
            },
        )

    except requests.HTTPError as exc:
        print(
            f"Skipping {owner}/{name}: "
            f"{exc}"
        )
        return []


# ============================================================
# XML escaping
# ============================================================

def escape_xml(text: str) -> str:
    """Escape text for safe insertion into SVG/XML."""

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# ============================================================
# Data collection
# ============================================================

repositories = get_repositories()

# Only inspect the most recently pushed repositories.
repositories_to_scan = repositories[:MAX_REPOSITORIES]

all_commits = []

for repo in repositories_to_scan:
    commits = get_repository_commits(repo)

    for commit in commits:
        commit_data = commit.get("commit", {})
        author_data = commit_data.get("author", {})

        date_string = author_data.get("date")

        if not date_string:
            continue

        message = (
            commit_data
            .get("message", "")
            .splitlines()[0]
            .strip()
        )

        if not message:
            message = "(no commit message)"

        try:
            commit_date = datetime.fromisoformat(
                date_string.replace("Z", "+00:00")
            )
        except ValueError:
            continue

        all_commits.append(
            {
                "repo": repo["name"],
                "message": message,
                "date": commit_date,
                "sha": commit.get("sha", "")[:7],
            }
        )


# Newest first.
all_commits.sort(
    key=lambda item: item["date"],
    reverse=True,
)

recent_commits = all_commits[
    :RECENT_COMMITS_TO_DISPLAY
]


# ============================================================
# Repository activity ranking
# ============================================================

repo_activity = Counter()

for commit in all_commits:
    repo_activity[commit["repo"]] += 1

top_repositories = repo_activity.most_common(5)


# ============================================================
# SVG configuration
# ============================================================

WIDTH = 760
HEIGHT = 700

BACKGROUND = "#0d1117"
PANEL = "#161b22"
BORDER = "#30363d"
TEXT = "#f0f6fc"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
GREEN = "#3fb950"

FONT = "JetBrains Mono, DejaVu Sans Mono, monospace"


# ============================================================
# Repository name shortening
# ============================================================

def shorten_repository_name(name: str, maximum: int = 17) -> str:
    """
    Keep repository names inside the right-hand panel.

    Example:
        very-long-repository-name
        ->
        very-long-repo...
    """

    if len(name) <= maximum:
        return name

    return name[: maximum - 3] + "..."


# ============================================================
# SVG generation
# ============================================================

svg = f'''<svg
xmlns="http://www.w3.org/2000/svg"
width="100%"
height="{HEIGHT}"
viewBox="0 0 {WIDTH} {HEIGHT}"
preserveAspectRatio="xMidYMid meet">

<rect
x="0"
y="0"
width="100%"
height="100%"
rx="12"
fill="{BACKGROUND}"/>

<!-- Header -->

<text
x="28"
y="42"
font-family="{FONT}"
font-size="22"
font-weight="700"
fill="{TEXT}">
FURRUKA // RECENT ACTIVITY
</text>

<text
x="28"
y="66"
font-family="{FONT}"
font-size="11"
fill="{MUTED}">
LIVE PROJECT TELEMETRY
</text>

<line
x1="28"
y1="84"
x2="732"
y2="84"
stroke="{BORDER}"/>


<!-- Recent commits panel -->

<rect
x="28"
y="106"
width="462"
height="510"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="50"
y="138"
font-family="{FONT}"
font-size="14"
font-weight="700"
fill="{TEXT}">
RECENT COMMITS
</text>
'''


# ============================================================
# Recent commits
# ============================================================

y = 172

if recent_commits:

    for item in recent_commits:

        commit_date = item["date"].astimezone(
            timezone.utc
        )

        date_text = commit_date.strftime(
            "%Y-%m-%d %H:%M"
        )

        repo_name = shorten_repository_name(
            item["repo"],
            maximum=17,
        )

        message = item["message"]

        # Keep commit text inside the left panel.
        if len(message) > 49:
            message = message[:46] + "..."

        repo_name = escape_xml(repo_name)
        message = escape_xml(message)

        svg += f'''
<circle
cx="56"
cy="{y - 4}"
r="4"
fill="{GREEN}"/>

<text
x="70"
y="{y}"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
{date_text} UTC
</text>

<text
x="222"
y="{y}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{ACCENT}">
{repo_name}
</text>

<text
x="70"
y="{y + 21}"
font-family="{FONT}"
font-size="11"
fill="{TEXT}">
{message}
</text>

<line
x1="50"
y1="{y + 40}"
x2="468"
y2="{y + 40}"
stroke="{BORDER}"/>
'''

        y += 57

else:

    svg += f'''
<text
x="50"
y="190"
font-family="{FONT}"
font-size="12"
fill="{MUTED}">
No recent public commits found.
</text>
'''


# ============================================================
# Active repositories panel
# ============================================================

svg += f'''
<rect
x="506"
y="106"
width="226"
height="510"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="528"
y="138"
font-family="{FONT}"
font-size="14"
font-weight="700"
fill="{TEXT}">
ACTIVE REPOSITORIES
</text>
'''


# ============================================================
# Repository ranking
# ============================================================

y = 180

if top_repositories:

    for index, (repo_name, count) in enumerate(
        top_repositories,
        start=1,
    ):

        short_name = shorten_repository_name(
            repo_name,
            maximum=17,
        )

        short_name = escape_xml(short_name)

        svg += f'''
<text
x="528"
y="{y}"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
{index:02d}
</text>

<text
x="555"
y="{y}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{TEXT}">
{short_name}
</text>

<text
x="710"
y="{y}"
font-family="{FONT}"
font-size="10"
text-anchor="end"
fill="{ACCENT}">
{count}
</text>
'''

        y += 46

else:

    svg += f'''
<text
x="528"
y="180"
font-family="{FONT}"
font-size="11"
fill="{MUTED}">
No repository activity.
</text>
'''


# ============================================================
# Summary information
# ============================================================

updated = datetime.now(
    timezone.utc
).strftime(
    "%Y-%m-%d %H:%M UTC"
)

total_repositories = len(repositories)

total_commits_indexed = len(all_commits)


svg += f'''
<line
x1="528"
y1="455"
x2="710"
y2="455"
stroke="{BORDER}"/>

<text
x="528"
y="485"
font-family="{FONT}"
font-size="9"
fill="{MUTED}">
REPOSITORIES
</text>

<text
x="710"
y="485"
font-family="{FONT}"
font-size="9"
text-anchor="end"
fill="{TEXT}">
{total_repositories}
</text>

<text
x="528"
y="515"
font-family="{FONT}"
font-size="9"
fill="{MUTED}">
COMMITS INDEXED
</text>

<text
x="710"
y="515"
font-family="{FONT}"
font-size="9"
text-anchor="end"
fill="{TEXT}">
{total_commits_indexed}
</text>

<text
x="528"
y="545"
font-family="{FONT}"
font-size="9"
fill="{MUTED}">
UPDATED
</text>

<text
x="710"
y="545"
font-family="{FONT}"
font-size="9"
text-anchor="end"
fill="{TEXT}">
{updated}
</text>

<text
x="28"
y="650"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
AUTOMATED VIA GITHUB ACTIONS
</text>

</svg>
'''


# ============================================================
# Write SVG
# ============================================================

output = Path(
    "profile/recent-activity.svg"
)

output.parent.mkdir(
    parents=True,
    exist_ok=True,
)

output.write_text(
    svg,
    encoding="utf-8",
)


# ============================================================
# Console output
# ============================================================

print("=" * 60)
print("Furruka Recent Activity")
print("=" * 60)
print(f"Repositories found : {total_repositories}")
print(f"Repositories scanned: {len(repositories_to_scan)}")
print(f"Commits indexed    : {total_commits_indexed}")
print(f"Recent commits     : {len(recent_commits)}")
print(f"Output             : {output}")
print("=" * 60)
