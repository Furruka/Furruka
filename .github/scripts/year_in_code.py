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

# Current year.
YEAR = datetime.now(timezone.utc).year

PER_PAGE = 100

# Avoid absurdly large requests on huge accounts.
MAX_PAGES_PER_REPO = 20


# ============================================================
# HTTP session
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


def api_get(url: str, params=None):
    """GET JSON from GitHub API."""

    response = session.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# XML escaping
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


# ============================================================
# Repository discovery
# ============================================================

def get_repositories():
    """
    Get all repositories owned by the user.

    Forks are included because the user may actively
    maintain their fork.
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

        name = repo.get("name", "")

        if name.lower() == PROFILE_REPO:
            continue

        if repo.get("disabled"):
            continue

        result.append(repo)

    return result


# ============================================================
# Get commits for a repository/year
# ============================================================

def get_year_commits(repo):
    """
    Get commits authored by USER during YEAR.

    GitHub's commit endpoint supports author/since/until
    filters and up to 100 results per page.
    """

    owner = repo["owner"]["login"]
    name = repo["name"]

    since = f"{YEAR}-01-01T00:00:00Z"
    until = f"{YEAR + 1}-01-01T00:00:00Z"

    commits = []

    for page in range(1, MAX_PAGES_PER_REPO + 1):

        try:

            data = api_get(
                f"{API}/repos/{owner}/{name}/commits",
                {
                    "author": USER,
                    "since": since,
                    "until": until,
                    "per_page": PER_PAGE,
                    "page": page,
                },
            )

        except requests.HTTPError as exc:

            print(
                f"Skipping {owner}/{name}: {exc}"
            )

            break

        if not data:
            break

        commits.extend(data)

        if len(data) < PER_PAGE:
            break

    return commits


# ============================================================
# Collect repositories
# ============================================================

repositories = get_repositories()

print(
    f"Repositories discovered: {len(repositories)}"
)


# ============================================================
# Statistics
# ============================================================

total_commits = 0

active_days = set()

monthly_commits = Counter()

repository_commits = Counter()

weekday_commits = Counter()

hour_commits = Counter()

language_activity = Counter()


# ============================================================
# Scan repositories
# ============================================================

for repo in repositories:

    full_name = repo["full_name"]

    print(
        f"[{YEAR}] Scanning {full_name}"
    )

    commits = get_year_commits(repo)

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

        try:

            commit_date = datetime.fromisoformat(
                date_string.replace(
                    "Z",
                    "+00:00",
                )
            )

        except ValueError:

            continue

        total_commits += 1

        active_days.add(
            commit_date.date()
        )

        monthly_commits[
            commit_date.month
        ] += 1

        weekday_commits[
            commit_date.weekday()
        ] += 1

        hour_commits[
            commit_date.hour
        ] += 1

        repository_commits[
            repo["name"]
        ] += 1


# ============================================================
# Derived statistics
# ============================================================

months = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]

weekdays = [
    "MON",
    "TUE",
    "WED",
    "THU",
    "FRI",
    "SAT",
    "SUN",
]


if monthly_commits:

    most_active_month_number = max(
        monthly_commits,
        key=monthly_commits.get,
    )

else:

    most_active_month_number = 1


most_active_month = months[
    most_active_month_number - 1
]


if weekday_commits:

    most_active_weekday_number = max(
        weekday_commits,
        key=weekday_commits.get,
    )

else:

    most_active_weekday_number = 0


most_active_weekday = weekdays[
    most_active_weekday_number
]


if hour_commits:

    most_active_hour = max(
        hour_commits,
        key=hour_commits.get,
    )

else:

    most_active_hour = 0


if repository_commits:

    top_repository = (
        repository_commits
        .most_common(1)[0]
    )

    top_repository_name = top_repository[0]

    top_repository_commits = top_repository[1]

else:

    top_repository_name = "None"

    top_repository_commits = 0


# ============================================================
# SVG configuration
# ============================================================

WIDTH = 760
HEIGHT = 780

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
# Helpers
# ============================================================

def bar(value, maximum, width=24):
    """Generate a compact text bar."""

    if maximum <= 0:
        return "░" * width

    ratio = value / maximum

    filled = round(
        ratio * width
    )

    filled = max(
        0,
        min(
            width,
            filled,
        ),
    )

    return (
        "█" * filled
        + "░" * (width - filled)
    )


def shorten(text, maximum=20):
    """Shorten long repository names."""

    if len(text) <= maximum:
        return text

    return text[:maximum - 3] + "..."


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


<!-- Header -->

<text
x="28"
y="42"
font-family="{FONT}"
font-size="22"
font-weight="700"
fill="{TEXT}">
FURRUKA // {YEAR} IN CODE
</text>

<text
x="28"
y="66"
font-family="{FONT}"
font-size="11"
fill="{MUTED}">
YEARLY DEVELOPMENT TELEMETRY
</text>

<line
x1="28"
y1="84"
x2="732"
y2="84"
stroke="{BORDER}"/>


<!-- Overview cards -->

<rect
x="28"
y="106"
width="165"
height="92"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="48"
y="134"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
COMMITS
</text>

<text
x="48"
y="170"
font-family="{FONT}"
font-size="26"
font-weight="700"
fill="{TEXT}">
{total_commits}
</text>


<rect
x="207"
y="106"
width="165"
height="92"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="227"
y="134"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
ACTIVE DAYS
</text>

<text
x="227"
y="170"
font-family="{FONT}"
font-size="26"
font-weight="700"
fill="{TEXT}">
{len(active_days)}
</text>


<rect
x="386"
y="106"
width="165"
height="92"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="406"
y="134"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
REPOSITORIES
</text>

<text
x="406"
y="170"
font-family="{FONT}"
font-size="26"
font-weight="700"
fill="{TEXT}">
{len(repository_commits)}
</text>


<rect
x="565"
y="106"
width="167"
height="92"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="585"
y="134"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
TOP PROJECT
</text>

<text
x="585"
y="160"
font-family="{FONT}"
font-size="11"
font-weight="700"
fill="{ACCENT}">
{escape_xml(shorten(top_repository_name, 18))}
</text>

<text
x="585"
y="180"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
{top_repository_commits} commits
</text>


<!-- Monthly activity -->

<rect
x="28"
y="220"
width="704"
height="330"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="50"
y="252"
font-family="{FONT}"
font-size="14"
font-weight="700"
fill="{TEXT}">
MONTHLY ACTIVITY
</text>
'''


# ============================================================
# Monthly chart
# ============================================================

max_monthly = max(
    monthly_commits.values(),
    default=1,
)

y = 285

for month_index in range(1, 13):

    count = monthly_commits.get(
        month_index,
        0,
    )

    month_name = months[
        month_index - 1
    ]

    bar_width = int(
        480
        * count
        / max_monthly
    )

    svg += f'''
<text
x="50"
y="{y}"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
{month_name}
</text>

<rect
x="105"
y="{y - 11}"
width="480"
height="12"
rx="3"
fill="#21262d"/>

<rect
x="105"
y="{y - 11}"
width="{bar_width}"
height="12"
rx="3"
fill="{GREEN}"/>

<text
x="610"
y="{y}"
font-family="{FONT}"
font-size="10"
text-anchor="end"
fill="{TEXT}">
{count}
</text>
'''

    y += 21


# ============================================================
# Bottom panels
# ============================================================

svg += f'''
<rect
x="28"
y="570"
width="338"
height="155"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="50"
y="602"
font-family="{FONT}"
font-size="14"
font-weight="700"
fill="{TEXT}">
PEAK ACTIVITY
</text>

<text
x="50"
y="636"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
MONTH
</text>

<text
x="180"
y="636"
font-family="{FONT}"
font-size="11"
font-weight="700"
fill="{ACCENT}">
{most_active_month}
</text>

<text
x="50"
y="662"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
WEEKDAY
</text>

<text
x="180"
y="662"
font-family="{FONT}"
font-size="11"
font-weight="700"
fill="{ACCENT}">
{most_active_weekday}
</text>

<text
x="50"
y="688"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
HOUR
</text>

<text
x="180"
y="688"
font-family="{FONT}"
font-size="11"
font-weight="700"
fill="{ACCENT}">
{most_active_hour:02d}:00 UTC
</text>


<rect
x="394"
y="570"
width="338"
height="155"
rx="10"
fill="{PANEL}"
stroke="{BORDER}"/>

<text
x="416"
y="602"
font-family="{FONT}"
font-size="14"
font-weight="700"
fill="{TEXT}">
TOP PROJECTS
</text>
'''


# ============================================================
# Top repositories list
# ============================================================

y = 632

for index, (
    repo_name,
    count,
) in enumerate(
    repository_commits.most_common(5),
    start=1,
):

    short_name = shorten(
        repo_name,
        22,
    )

    svg += f'''
<text
x="416"
y="{y}"
font-family="{FONT}"
font-size="10"
fill="{MUTED}">
{index:02d}
</text>

<text
x="445"
y="{y}"
font-family="{FONT}"
font-size="10"
font-weight="700"
fill="{TEXT}">
{escape_xml(short_name)}
</text>

<text
x="708"
y="{y}"
font-family="{FONT}"
font-size="10"
text-anchor="end"
fill="{ACCENT}">
{count}
</text>
'''

    y += 20


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
x="28"
y="752"
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
    "profile/year-in-code.svg"
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
print(f"Furruka {YEAR} In Code")
print("=" * 60)

print(
    f"Repositories discovered : "
    f"{len(repositories)}"
)

print(
    f"Repositories with commits: "
    f"{len(repository_commits)}"
)

print(
    f"Total commits           : "
    f"{total_commits}"
)

print(
    f"Active days             : "
    f"{len(active_days)}"
)

print(
    f"Most active month       : "
    f"{most_active_month}"
)

print(
    f"Most active weekday     : "
    f"{most_active_weekday}"
)

print(
    f"Most active hour        : "
    f"{most_active_hour:02d}:00 UTC"
)

print(
    f"Top repository          : "
    f"{top_repository_name}"
)

print(
    f"Output                  : "
    f"{output}"
)

print("=" * 60)
