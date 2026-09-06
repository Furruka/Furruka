import os
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

PER_PAGE = 100
MAX_REPOSITORIES = 50
COMMITS_PER_REPOSITORY = 20
LOG_ENTRIES = 10


# ============================================================
# GitHub API
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


def api_get(url: str, params=None):
    response = session.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


# ============================================================
# Helpers
# ============================================================

def escape_xml(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def shorten(text: str, maximum: int) -> str:
    if len(text) <= maximum:
        return text

    return text[:maximum - 3] + "..."


def classify(repository: str, message: str) -> str:
    """
    Automatically classify a commit.

    Repository name and commit message are both considered.
    """

    text = (
        f"{repository} {message}"
        .lower()
    )

    if any(
        keyword in text
        for keyword in (
            "kernel",
            "linux",
            "dts",
            "driver",
            "gki",
        )
    ):
        return "KERNEL"

    if any(
        keyword in text
        for keyword in (
            "android",
            "aosp",
            "gsi",
            "rom",
        )
    ):
        return "ANDROID"

    if any(
        keyword in text
        for keyword in (
            "twrp",
            "orangefox",
            "recovery",
        )
    ):
        return "RECOVERY"

    if any(
        keyword in text
        for keyword in (
            "drm",
            "dsi",
            "dsc",
            "display",
            "panel",
            "kms",
        )
    ):
        return "DISPLAY"

    if any(
        keyword in text
        for keyword in (
            "dns",
            "nft",
            "network",
            "router",
            "proxy",
            "tproxy",
            "ipv6",
        )
    ):
        return "NETWORKING"

    if any(
        keyword in text
        for keyword in (
            "wayland",
            "plasma",
            "desktop",
            "kde",
        )
    ):
        return "DESKTOP"

    if any(
        keyword in text
        for keyword in (
            "build",
            "ci",
            "github",
            "action",
            "workflow",
        )
    ):
        return "TOOLING"

    return "GENERAL"


# ============================================================
# Repository discovery
# ============================================================

def get_repositories():
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

    result = []

    for repo in repositories:
        name = repo.get("name", "")

        # Never include the profile repository.
        if name.lower() == PROFILE_REPO:
            continue

        if repo.get("disabled"):
            continue

        result.append(repo)

    return result


# ============================================================
# Commit discovery
# ============================================================

def get_commits(repo):
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
            f"Skipping {owner}/{name}: {exc}"
        )
        return []


# ============================================================
# Collect activity
# ============================================================

repositories = get_repositories()

repositories = repositories[
    :MAX_REPOSITORIES
]

entries = []

for repo in repositories:
    repo_name = repo["name"]

    print(
        f"Scanning {repo['full_name']}"
    )

    commits = get_commits(repo)

    for commit in commits:
        commit_data = commit.get(
            "commit",
            {},
        )

        author = commit_data.get(
            "author",
            {},
        )

        date_string = author.get(
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

        entries.append(
            {
                "repo": repo_name,
                "message": message,
                "date": commit_date,
                "category": classify(
                    repo_name,
                    message,
                ),
                "sha": commit.get(
                    "sha",
                    "",
                )[:7],
            }
        )


# ============================================================
# Sort and deduplicate
# ============================================================

entries.sort(
    key=lambda item: item["date"],
    reverse=True,
)

seen = set()
unique_entries = []

for entry in entries:
    key = (
        entry["repo"],
        entry["sha"],
    )

    if key in seen:
        continue

    seen.add(key)
    unique_entries.append(entry)

entries = unique_entries[
    :LOG_ENTRIES
]


# ============================================================
# SVG
# ============================================================

WIDTH = 760
HEIGHT = 720

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

<text
x="28"
y="42"
font-family="{FONT}"
font-size="22"
font-weight="700"
fill="{TEXT}">
FURRUKA // DEVELOPER LOG
</text>

<text
x="28"
y="66"
font-family="{FONT}"
font-size="11"
fill="{MUTED}">
AUTOMATED DEVELOPMENT HISTORY
</text>

<line
x1="28"
y1="84"
x2="732"
y2="84"
stroke="{BORDER}"/>

<rect
x="28"
y="106"
width="704"
height="555"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="50"
y="140"
font-family="{FONT}"
font-size="14"
font-weight="700"
fill="{TEXT}">
RECENT DEVELOPMENT
</text>
'''


# ============================================================
# Render log entries
# ============================================================

y = 178

for entry in entries:

    date = entry["date"].astimezone(
        timezone.utc
    )

    date_text = date.strftime(
        "%Y-%m-%d"
    )

    repo = shorten(
        entry["repo"],
        24,
    )

    message = shorten(
        entry["message"],
        66,
    )

    category = entry["category"]

    repo = escape_xml(repo)
    message = escape_xml(message)
    category = escape_xml(category)

    svg += f'''
<circle
cx="55"
cy="{y - 4}"
r="4"
fill="{GREEN}"/>

<text
x="70"
y="{y}"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
{date_text}
</text>

<text
x="162"
y="{y}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{ACCENT}">
{repo}
</text>

<text
x="70"
y="{y + 22}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{MUTED}">
[{category}]
</text>

<text
x="162"
y="{y + 22}"
font-family="{FONT}"
font-size="11"
fill="{TEXT}">
{message}
</text>

<line
x1="50"
y1="{y + 40}"
x2="710"
y2="{y + 40}"
stroke="{BORDER}"/>
'''

    y += 52


# ============================================================
# Empty state
# ============================================================

if not entries:
    svg += f'''
<text
x="50"
y="185"
font-family="{FONT}"
font-size="12"
fill="{MUTED}">
No development activity found.
</text>
'''


# ============================================================
# Footer
# ============================================================

updated = datetime.now(
    timezone.utc
).strftime(
    "%Y-%m-%d %H:%M UTC"
)

svg += f'''
<text
x="50"
y="695"
font-family="{FONT}"
font-size="9"
fill="{MUTED}">
UPDATED {updated} · GENERATED BY GITHUB ACTIONS
</text>

</svg>
'''


# ============================================================
# Write output
# ============================================================

output = Path(
    "profile/developer-log.svg"
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
# Console
# ============================================================

print()
print("=" * 60)
print("Furruka Developer Log")
print("=" * 60)
print(
    f"Repositories scanned : "
    f"{len(repositories)}"
)
print(
    f"Commits discovered   : "
    f"{len(entries)}"
)
print(
    f"Output               : "
    f"{output}"
)
print("=" * 60)
