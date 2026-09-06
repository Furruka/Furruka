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

# The Profile README repository must not appear in the log.
PROFILE_REPO = USER.lower()

# GitHub API pagination.
PER_PAGE = 100

# Maximum repositories to scan.
MAX_REPOSITORIES = 50

# Commits fetched from each repository.
COMMITS_PER_REPOSITORY = 100

# Number of entries shown in the Developer Log.
LOG_ENTRIES = 10


# ============================================================
# HTTP session
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


def api_get(url: str, params=None):
    """
    Perform a GET request against GitHub API.
    """

    response = session.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# XML helpers
# ============================================================

def escape_xml(text: str) -> str:
    """
    Escape text so it can safely be inserted into SVG/XML.
    """

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def shorten(text: str, maximum: int) -> str:
    """
    Shorten a string without exceeding maximum length.
    """

    if len(text) <= maximum:
        return text

    return text[:maximum - 3] + "..."


def wrap_message(text: str, maximum: int = 58):
    """
    Wrap a commit message into at most two lines.

    We prefer breaking on spaces.
    The second line is also capped.
    """

    text = text.strip()

    if not text:
        return ["(no commit message)"]

    if len(text) <= maximum:
        return [text]

    first_part = text[:maximum]

    split_at = first_part.rfind(" ")

    # Avoid an absurdly short first line.
    if split_at < int(maximum * 0.55):
        split_at = maximum

    line1 = text[:split_at].strip()
    line2 = text[split_at:].strip()

    if len(line2) > maximum:
        line2 = line2[:maximum - 3] + "..."

    return [
        line1,
        line2,
    ]


# ============================================================
# Automatic category detection
# ============================================================

def classify(repository: str, message: str) -> str:
    """
    Automatically classify a commit from repository name
    and commit message.
    """

    text = (
        f"{repository} {message}"
        .lower()
    )

    # Display / graphics first because names like
    # "kernel-display" should ideally be DISPLAY.
    if any(
        keyword in text
        for keyword in (
            "drm",
            "dsi",
            "dsc",
            "display",
            "panel",
            "kms",
            "ovl",
            "rdma",
            "mipi",
        )
    ):
        return "DISPLAY"

    if any(
        keyword in text
        for keyword in (
            "kernel",
            "linux",
            "device tree",
            "devicetree",
            "dts",
            "driver",
            "gki",
            "upstream",
            "mainline",
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
            "magisk",
            "vendor",
            "system_ext",
        )
    ):
        return "ANDROID"

    if any(
        keyword in text
        for keyword in (
            "twrp",
            "orangefox",
            "recovery",
            "boot image",
            "ramdisk",
        )
    ):
        return "RECOVERY"

    if any(
        keyword in text
        for keyword in (
            "dns",
            "nftables",
            "nft",
            "network",
            "router",
            "proxy",
            "tproxy",
            "ipv6",
            "dnsmasq",
            "smartdns",
        )
    ):
        return "NETWORKING"

    if any(
        keyword in text
        for keyword in (
            "wayland",
            "plasma",
            "kde",
            "desktop",
            "kwin",
            "avalonia",
            "gui",
        )
    ):
        return "DESKTOP"

    if any(
        keyword in text
        for keyword in (
            "github",
            "action",
            "actions",
            "workflow",
            "ci",
            "build",
            "release",
            "automation",
        )
    ):
        return "TOOLING"

    return "GENERAL"


# ============================================================
# Repository discovery
# ============================================================

def get_repositories():
    """
    Get all repositories belonging to the user.

    Forks are intentionally included.
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

    result = []

    for repo in repositories:

        name = repo.get(
            "name",
            "",
        )

        # Exclude the Profile README repository.
        if name.lower() == PROFILE_REPO:
            continue

        # Ignore disabled repositories.
        if repo.get("disabled"):
            continue

        result.append(repo)

    return result


# ============================================================
# Commit discovery
# ============================================================

def get_commits(repo):
    """
    Get commits authored by the current GitHub user.
    """

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
            f"Skipping "
            f"{owner}/{name}: "
            f"{exc}"
        )

        return []


# ============================================================
# Collect repositories
# ============================================================

repositories = get_repositories()

repositories_to_scan = repositories[
    :MAX_REPOSITORIES
]

print(
    f"Repositories discovered: "
    f"{len(repositories)}"
)

print(
    f"Repositories scanned: "
    f"{len(repositories_to_scan)}"
)


# ============================================================
# Collect commits
# ============================================================

entries = []

for repo in repositories_to_scan:

    repo_name = repo["name"]

    print(
        f"Scanning "
        f"{repo['full_name']}"
    )

    commits = get_commits(repo)

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
            .get(
                "message",
                "",
            )
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
# Sort newest first
# ============================================================

entries.sort(
    key=lambda item: item["date"],
    reverse=True,
)


# ============================================================
# Deduplicate commits
# ============================================================

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

    unique_entries.append(
        entry
    )


entries = unique_entries[
    :LOG_ENTRIES
]


# ============================================================
# SVG Configuration
# ============================================================

WIDTH = 760

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
# Prepare display entries
# ============================================================

rendered_entries = []

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

    category = entry[
        "category"
    ]

    message_lines = wrap_message(
        entry["message"],
        58,
    )

    rendered_entries.append(
        {
            "date": escape_xml(
                date_text
            ),
            "repo": escape_xml(
                repo
            ),
            "category": escape_xml(
                category
            ),
            "message_lines": [
                escape_xml(
                    line
                )
                for line
                in message_lines
            ],
        }
    )


# ============================================================
# Dynamic layout calculation
# ============================================================

PANEL_TOP = 106

ENTRY_START_Y = 178

ENTRY_SINGLE_HEIGHT = 58

ENTRY_DOUBLE_EXTRA = 18

ENTRY_SEPARATOR_GAP = 4

PANEL_BOTTOM_PADDING = 52

FOOTER_HEIGHT = 55


entries_height = 0

for entry in rendered_entries:

    line_count = len(
        entry["message_lines"]
    )

    entries_height += (
        ENTRY_SINGLE_HEIGHT
        + (
            ENTRY_DOUBLE_EXTRA
            if line_count > 1
            else 0
        )
        + ENTRY_SEPARATOR_GAP
    )


if not rendered_entries:

    entries_height = 90


PANEL_HEIGHT = (
    (ENTRY_START_Y - PANEL_TOP)
    + entries_height
    + PANEL_BOTTOM_PADDING
)


FOOTER_Y = (
    PANEL_TOP
    + PANEL_HEIGHT
    + 32
)


HEIGHT = (
    PANEL_TOP
    + PANEL_HEIGHT
    + FOOTER_HEIGHT
)


# ============================================================
# SVG Header
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
y="{PANEL_TOP}"
width="704"
height="{PANEL_HEIGHT}"
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
# Render commits
# ============================================================

y = ENTRY_START_Y

if rendered_entries:

    for entry in rendered_entries:

        message_lines = entry[
            "message_lines"
        ]

        # Commit date.
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
{entry["date"]}
</text>

<text
x="162"
y="{y}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{ACCENT}">
{entry["repo"]}
</text>
'''

        # Category.
        svg += f'''
<text
x="70"
y="{y + 22}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{MUTED}">
[{entry["category"]}]
</text>
'''

        # First commit message line.
        svg += f'''
<text
x="162"
y="{y + 22}"
font-family="{FONT}"
font-size="11"
fill="{TEXT}">
{message_lines[0]}
</text>
'''

        # Optional second line.
        if len(message_lines) > 1:

            svg += f'''
<text
x="162"
y="{y + 40}"
font-family="{FONT}"
font-size="11"
fill="{TEXT}">
{message_lines[1]}
</text>
'''

            separator_y = y + 58

        else:

            separator_y = y + 40

        # Separator.
        svg += f'''
<line
x1="50"
y1="{separator_y}"
x2="710"
y2="{separator_y}"
stroke="{BORDER}"/>
'''

        # Dynamically move the next entry down.
        y += (
            ENTRY_SINGLE_HEIGHT
            + (
                ENTRY_DOUBLE_EXTRA
                if len(message_lines) > 1
                else 0
            )
            + ENTRY_SEPARATOR_GAP
        )

else:

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
y="{FOOTER_Y}"
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
# Console output
# ============================================================

print()
print("=" * 60)
print("Furruka Developer Log")
print("=" * 60)

print(
    f"Repositories discovered : "
    f"{len(repositories)}"
)

print(
    f"Repositories scanned    : "
    f"{len(repositories_to_scan)}"
)

print(
    f"Entries discovered      : "
    f"{len(entries)}"
)

print(
    f"Entries rendered        : "
    f"{len(rendered_entries)}"
)

print(
    f"SVG height              : "
    f"{HEIGHT}px"
)

print(
    f"Output                  : "
    f"{output}"
)

print("=" * 60)
