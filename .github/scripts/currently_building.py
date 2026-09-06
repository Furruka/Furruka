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

PROFILE_REPO = USER.lower()

PER_PAGE = 100

MAX_REPOSITORIES = 50

COMMITS_PER_REPOSITORY = 100

# Only consider activity from this period.
ACTIVITY_DAYS = 60

# Number of projects to display.
PROJECT_COUNT = 4


# ============================================================
# HTTP session
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
# XML helpers
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


def shorten(text: str, maximum: int):
    if len(text) <= maximum:
        return text

    return text[:maximum - 3] + "..."


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

        name = repo.get(
            "name",
            "",
        )

        # Never include profile repository.
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
# Classification
# ============================================================

CATEGORY_RULES = {
    "KERNEL": (
        "kernel",
        "linux",
        "dts",
        "devicetree",
        "device tree",
        "driver",
        "gki",
        "mainline",
        "upstream",
        "boot",
    ),

    "ANDROID": (
        "android",
        "aosp",
        "gsi",
        "rom",
        "vendor",
        "system_ext",
        "framework",
    ),

    "RECOVERY": (
        "twrp",
        "orangefox",
        "recovery",
        "ramdisk",
        "boot image",
    ),

    "DISPLAY": (
        "drm",
        "dsi",
        "dsc",
        "display",
        "panel",
        "kms",
        "mipi",
        "ovl",
        "rdma",
    ),

    "BLUETOOTH": (
        "bluetooth",
        "bluez",
        "ble",
        "hogp",
    ),

    "HID": (
        "hid",
        "usbmuxd",
        "input",
        "pointer",
        "keyboard",
        "mouse",
        "touch",
    ),

    "IOS": (
        "iphone",
        "ipad",
        "ios",
        "avfoundation",
        "coremedia",
        "usbmux",
    ),

    "DESKTOP": (
        "wayland",
        "plasma",
        "kde",
        "kwin",
        "desktop",
        "avalonia",
        "gtk",
        "qt",
        "gui",
    ),

    "NETWORKING": (
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
    ),

    "TOOLING": (
        "github",
        "actions",
        "workflow",
        "build",
        "ci",
        "release",
        "automation",
    ),
}


def detect_categories(repository, commits):

    text_parts = [repository]

    for commit in commits:
        text_parts.append(
            commit.get(
                "message",
                "",
            )
        )

    text = " ".join(
        text_parts
    ).lower()

    scores = Counter()

    for category, keywords in CATEGORY_RULES.items():

        for keyword in keywords:

            if keyword in text:
                scores[category] += 1

    return scores


# ============================================================
# Collect recent activity
# ============================================================

repositories = get_repositories()

now = datetime.now(
    timezone.utc
)

activity_since = (
    now
    - timedelta(
        days=ACTIVITY_DAYS
    )
)

project_scores = {}

all_recent_commits = []


for repo in repositories[:MAX_REPOSITORIES]:

    repo_name = repo["name"]

    print(
        f"Scanning {repo['full_name']}"
    )

    commits = get_commits(repo)

    recent_commits = []

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

        try:

            commit_date = datetime.fromisoformat(
                date_string.replace(
                    "Z",
                    "+00:00",
                )
            )

        except ValueError:

            continue

        if commit_date < activity_since:
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

        recent_commits.append(
            {
                "date": commit_date,
                "message": message,
                "repo": repo_name,
            }
        )

        all_recent_commits.append(
            {
                "date": commit_date,
                "message": message,
                "repo": repo_name,
            }
        )

    if not recent_commits:
        continue

    categories = detect_categories(
        repo_name,
        recent_commits,
    )

    commit_count = len(
        recent_commits
    )

    # Activity score:
    #
    # commit count has the largest effect,
    # categories add contextual weight,
    # recency provides a small bonus.
    #
    # This is deliberately simple and explainable.
    score = commit_count * 10

    score += sum(
        categories.values()
    ) * 3

    newest = max(
        item["date"]
        for item in recent_commits
    )

    age_days = max(
        0,
        (
            now - newest
        ).days
    )

    score += max(
        0,
        ACTIVITY_DAYS - age_days
    )

    project_scores[
        repo_name
    ] = {
        "score": score,
        "commits": commit_count,
        "categories": categories,
        "newest": newest,
    }


# ============================================================
# Rank projects
# ============================================================

ranked_projects = sorted(
    project_scores.items(),
    key=lambda item: (
        item[1]["score"],
        item[1]["commits"],
        item[1]["newest"],
    ),
    reverse=True,
)

ranked_projects = ranked_projects[
    :PROJECT_COUNT
]


# ============================================================
# SVG helpers
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


def project_height(project):

    categories = project[
        "categories"
    ]

    # Maximum of three category labels.
    category_count = min(
        3,
        len(categories),
    )

    return (
        104
        + category_count * 19
    )


# ============================================================
# Dynamic SVG height
# ============================================================

HEADER_HEIGHT = 106

PROJECT_START_Y = 178

BOTTOM_PADDING = 60

if ranked_projects:

    projects_height = sum(
        project_height(
            data
        )
        for _, data
        in ranked_projects
    )

else:

    projects_height = 120


PANEL_HEIGHT = (
    (
        PROJECT_START_Y
        - HEADER_HEIGHT
    )
    + projects_height
    + BOTTOM_PADDING
)

FOOTER_HEIGHT = 55

FOOTER_Y = (
    HEADER_HEIGHT
    + PANEL_HEIGHT
    + 32
)

HEIGHT = (
    HEADER_HEIGHT
    + PANEL_HEIGHT
    + FOOTER_HEIGHT
)


# ============================================================
# Start SVG
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
FURRUKA // CURRENTLY BUILDING
</text>

<text
x="28"
y="66"
font-family="{FONT}"
font-size="11"
fill="{MUTED}">
ACTIVE PROJECTS · LAST {ACTIVITY_DAYS} DAYS
</text>

<line
x1="28"
y1="84"
x2="732"
y2="84"
stroke="{BORDER}"/>

<rect
x="28"
y="{HEADER_HEIGHT}"
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
ACTIVE NOW
</text>
'''


# ============================================================
# Render projects
# ============================================================

y = PROJECT_START_Y


if ranked_projects:

    for index, (
        repo_name,
        data,
    ) in enumerate(
        ranked_projects,
        start=1,
    ):

        categories = data[
            "categories"
        ]

        category_names = [
            name
            for name, _score
            in categories.most_common()
        ][:3]

        newest = data[
            "newest"
        ].astimezone(
            timezone.utc
        )

        date_text = newest.strftime(
            "%Y-%m-%d"
        )

        display_repo = shorten(
            repo_name,
            30,
        )

        svg += f'''
<circle
cx="55"
cy="{y - 4}"
r="5"
fill="{GREEN}"/>

<text
x="72"
y="{y}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{MUTED}">
{index:02d}
</text>

<text
x="104"
y="{y}"
font-family="{FONT}"
font-size="13"
font-weight="700"
fill="{ACCENT}">
{escape_xml(display_repo)}
</text>

<text
x="680"
y="{y}"
font-family="{FONT}"
font-size="10"
text-anchor="end"
fill="{MUTED}">
{data["commits"]} commits
</text>
'''

        # Categories.
        category_y = y + 22

        if category_names:

            category_text = (
                " · ".join(
                    category_names
                )
            )

            svg += f'''
<text
x="104"
y="{category_y}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{MUTED}">
{escape_xml(category_text)}
</text>
'''

        else:

            svg += f'''
<text
x="104"
y="{category_y}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{MUTED}">
GENERAL
</text>
'''

        svg += f'''
<text
x="104"
y="{category_y + 20}"
font-family="{FONT}"
font-size="10"
fill="{TEXT}">
active through {date_text}
</text>

<line
x1="50"
y1="{category_y + 39}"
x2="710"
y2="{category_y + 39}"
stroke="{BORDER}"/>
'''

        y += project_height(
            data
        )


else:

    svg += f'''
<text
x="50"
y="185"
font-family="{FONT}"
font-size="12"
fill="{MUTED}">
No active projects found in the last
{ACTIVITY_DAYS} days.
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
# Write SVG
# ============================================================

output = Path(
    "profile/currently-building.svg"
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
print("Furruka Currently Building")
print("=" * 60)

print(
    f"Repositories discovered : "
    f"{len(repositories)}"
)

print(
    f"Activity window          : "
    f"{ACTIVITY_DAYS} days"
)

print(
    f"Active projects          : "
    f"{len(ranked_projects)}"
)

for index, (
    repo_name,
    data,
) in enumerate(
    ranked_projects,
    start=1,
):

    categories = ", ".join(
        name
        for name, _score
        in data[
            "categories"
        ].most_common(3)
    )

    print(
        f"{index}. "
        f"{repo_name} "
        f"({data['commits']} commits) "
        f"[{categories}]"
    )

print(
    f"Output                   : "
    f"{output}"
)

print("=" * 60)
