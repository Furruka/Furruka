import os
from collections import Counter
from datetime import datetime, timezone
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

PROFILE_REPO = USER.lower()

# How many recent commits to display.
RECENT_COMMITS_TO_DISPLAY = 8

# How many repositories to show on the right panel.
TOP_REPOSITORIES_TO_DISPLAY = 6

# GitHub returns max 100 items per page.
PER_PAGE = 100


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
# Get repositories
# ============================================================

def get_repositories():
    """
    Get all repositories owned by the user.

    Forks are INCLUDED.

    The profile repository is excluded separately.
    """

    repositories = []

    for page in range(1, 21):

        data = api_get(
            f"{API}/users/{USER}/repos",
            {
                "type": "all",
                "sort": "updated",
                "direction": "desc",
                "per_page": PER_PAGE,
                "page": page,
            },
        )

        if not data:
            break

        repositories.extend(data)

        if len(data) < PER_PAGE:
            break

    filtered = []

    for repo in repositories:

        name = repo.get("name", "")

        # Exclude our Profile README repository.
        if name.lower() == PROFILE_REPO:
            continue

        # Disabled repositories cannot be queried normally.
        if repo.get("disabled"):
            continue

        # IMPORTANT:
        # Fork repositories are intentionally NOT excluded.
        filtered.append(repo)

    return filtered


# ============================================================
# Get commits
# ============================================================

def get_repository_commits(repo):
    """
    Get recent commits authored by this user.

    The GitHub API's author parameter accepts
    the GitHub username.
    """

    owner = repo["owner"]["login"]
    name = repo["name"]

    try:

        return api_get(
            f"{API}/repos/{owner}/{name}/commits",
            {
                "author": USER,
                "per_page": PER_PAGE,
            },
        )

    except requests.HTTPError as exc:

        print(
            f"Skipping {owner}/{name}: {exc}"
        )

        return []


# ============================================================
# XML escaping
# ============================================================

def escape_xml(text: str) -> str:
    """Escape text before inserting it into SVG."""

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# ============================================================
# Repository discovery
# ============================================================

repositories = get_repositories()

print(
    f"Repositories discovered: {len(repositories)}"
)


# ============================================================
# Commit collection
# ============================================================

all_commits = []

for repo in repositories:

    print(
        f"Scanning: "
        f"{repo['full_name']}"
    )

    commits = get_repository_commits(repo)

    for commit in commits:

        commit_data = commit.get(
            "commit",
            {},
        )

        author_data = commit_data.get(
            "author",
            {},
        )

        date_string = author_data.get(
            "date"
        )

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
                date_string.replace(
                    "Z",
                    "+00:00",
                )
            )

        except ValueError:

            continue

        all_commits.append(
            {
                "repo": repo["name"],
                "message": message,
                "date": commit_date,
                "sha": commit.get(
                    "sha",
                    "",
                )[:7],
            }
        )


# ============================================================
# Sort commits
# ============================================================

all_commits.sort(
    key=lambda item: item["date"],
    reverse=True,
)


recent_commits = (
    all_commits[
        :RECENT_COMMITS_TO_DISPLAY
    ]
)


# ============================================================
# Repository activity
# ============================================================

repo_activity = Counter()

for commit in all_commits:

    repo_activity[
        commit["repo"]
    ] += 1


top_repositories = (
    repo_activity
    .most_common(
        TOP_REPOSITORIES_TO_DISPLAY
    )
)


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

FONT = (
    "JetBrains Mono, "
    "DejaVu Sans Mono, "
    "monospace"
)


# ============================================================
# Repository name shortening
# ============================================================

def shorten_repository_name(
    name: str,
    maximum: int = 17,
) -> str:

    if len(name) <= maximum:
        return name

    return (
        name[: maximum - 3]
        + "..."
    )


# ============================================================
# Generate SVG
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


<!-- HEADER -->

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


<!-- RECENT COMMITS -->

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
# Recent commits panel
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

        if len(message) > 49:
            message = (
                message[:46]
                + "..."
            )

        repo_name = escape_xml(
            repo_name
        )

        message = escape_xml(
            message
        )

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
No recent commits found.
</text>
'''


# ============================================================
# ACTIVE REPOSITORIES
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

    for index, (
        repo_name,
        count,
    ) in enumerate(
        top_repositories,
        start=1,
    ):

        short_name = shorten_repository_name(
            repo_name,
            maximum=17,
        )

        short_name = escape_xml(
            short_name
        )

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
# Summary
# ============================================================

updated = datetime.now(
    timezone.utc
).strftime(
    "%Y-%m-%d %H:%M UTC"
)

total_repositories = len(
    repositories
)

total_commits_indexed = len(
    all_commits
)

active_repository_count = len(
    repo_activity
)


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
ACTIVE
</text>

<text
x="710"
y="515"
font-family="{FONT}"
font-size="9"
text-anchor="end"
fill="{TEXT}">
{active_repository_count}
</text>

<text
x="528"
y="545"
font-family="{FONT}"
font-size="9"
fill="{MUTED}">
COMMITS INDEXED
</text>

<text
x="710"
y="545"
font-family="{FONT}"
font-size="9"
text-anchor="end"
fill="{TEXT}">
{total_commits_indexed}
</text>

<text
x="528"
y="575"
font-family="{FONT}"
font-size="9"
fill="{MUTED}">
UPDATED
</text>

<text
x="710"
y="575"
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
# Write output
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

print()
print("=" * 60)
print("Furruka Recent Activity")
print("=" * 60)
print(
    f"Repositories discovered : "
    f"{total_repositories}"
)
print(
    f"Repositories with commits: "
    f"{active_repository_count}"
)
print(
    f"Commits indexed         : "
    f"{total_commits_indexed}"
)
print(
    f"Recent commits displayed: "
    f"{len(recent_commits)}"
)
print(
    f"Output                  : "
    f"{output}"
)
print("=" * 60)
