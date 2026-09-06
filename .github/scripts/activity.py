import os
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter

USER = os.environ["GITHUB_USER"]
TOKEN = os.environ["GITHUB_TOKEN"]

API = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2026-03-10",
}

session = requests.Session()
session.headers.update(HEADERS)


def api_get(url, params=None):
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def get_repositories():
    repos = []

    for page in range(1, 11):
        data = api_get(
            f"{API}/users/{USER}/repos",
            {
                "type": "owner",
                "per_page": 100,
                "page": page,
            },
        )

        if not data:
            break

        repos.extend(data)

        if len(data) < 100:
            break

    return [
        repo
        for repo in repos
        if not repo.get("fork", False)
        and not repo.get("archived", False)
        and not repo.get("disabled", False)
    ]


def get_commits(repo, since, until):
    owner = repo["owner"]["login"]
    name = repo["name"]

    commits = []

    for page in range(1, 11):
        data = api_get(
            f"{API}/repos/{owner}/{name}/commits",
            {
                "author": USER,
                "since": since,
                "until": until,
                "per_page": 100,
                "page": page,
            },
        )

        if not data:
            break

        commits.extend(data)

        if len(data) < 100:
            break

    return commits


now = datetime.now(timezone.utc)
start = now - timedelta(days=365)

since = start.strftime("%Y-%m-%dT%H:%M:%SZ")
until = now.strftime("%Y-%m-%dT%H:%M:%SZ")

day_hour = Counter()
repo_commits = Counter()

repositories = get_repositories()

for repo in repositories:
    try:
        commits = get_commits(repo, since, until)

        for commit in commits:
            date_string = (
                commit.get("commit", {})
                .get("author", {})
                .get("date")
            )

            if not date_string:
                continue

            dt = datetime.fromisoformat(
                date_string.replace("Z", "+00:00")
            )

            day_hour[(dt.weekday(), dt.hour)] += 1
            repo_commits[repo["name"]] += 1

    except Exception as exc:
        print(f"Skipping {repo['full_name']}: {exc}")


total = sum(day_hour.values())

if total:
    busiest_day = max(
        range(7),
        key=lambda d: sum(day_hour[(d, h)] for h in range(24)),
    )

    busiest_hour = max(
        range(24),
        key=lambda h: sum(day_hour[(d, h)] for d in range(7)),
    )
else:
    busiest_day = 0
    busiest_hour = 0


days = [
    "MON",
    "TUE",
    "WED",
    "THU",
    "FRI",
    "SAT",
    "SUN",
]

values = [
    day_hour[(d, h)]
    for d in range(7)
    for h in range(24)
]

maximum = max(values) if values else 1


def level(value):
    ratio = value / maximum

    if value == 0:
        return "░"

    if ratio < 0.25:
        return "░"

    if ratio < 0.50:
        return "▒"

    if ratio < 0.75:
        return "▓"

    return "█"


rows = []

for hour_start in range(0, 24, 4):
    cells = []

    for day in range(7):
        value = sum(
            day_hour[(day, hour)]
            for hour in range(hour_start, min(hour_start + 4, 24))
        )

        cells.append(level(value))

    rows.append(
        f"{hour_start:02d}-{(hour_start + 4):02d}  "
        + "  ".join(cells)
    )


top_repos = repo_commits.most_common(5)

repo_lines = []

for name, count in top_repos:
    repo_lines.append(f"{name}: {count}")

if not repo_lines:
    repo_lines.append("No public commit data found.")


svg_width = 900
svg_height = 470

font = "JetBrains Mono, DejaVu Sans Mono, monospace"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
width="{svg_width}" height="{svg_height}"
viewBox="0 0 {svg_width} {svg_height}">

<rect width="100%" height="100%" fill="#0d1117"/>

<text x="40" y="48"
font-family="{font}"
font-size="26"
font-weight="700"
fill="#f0f6fc">
FURRUKA // SYSTEM ACTIVITY
</text>

<text x="40" y="78"
font-family="{font}"
font-size="13"
fill="#8b949e">
LAST 365 DAYS · UTC
</text>

<line x1="40" y1="98" x2="860" y2="98"
stroke="#30363d"/>

<text x="185" y="130"
font-family="{font}"
font-size="13"
fill="#8b949e">
{"   ".join(days)}
</text>
'''

y = 160

for row in rows:
    svg += f'''
<text x="40" y="{y}"
font-family="{font}"
font-size="17"
fill="#c9d1d9">
{row}
</text>
'''
    y += 38


svg += f'''
<line x1="40" y1="410" x2="860" y2="410"
stroke="#30363d"/>

<text x="40" y="438"
font-family="{font}"
font-size="13"
fill="#8b949e">
COMMITS
</text>

<text x="125" y="438"
font-family="{font}"
font-size="13"
fill="#f0f6fc">
{total}
</text>

<text x="240" y="438"
font-family="{font}"
font-size="13"
fill="#8b949e">
PEAK DAY
</text>

<text x="330" y="438"
font-family="{font}"
font-size="13"
fill="#f0f6fc">
{days[busiest_day]}
</text>

<text x="450" y="438"
font-family="{font}"
font-size="13"
fill="#8b949e">
PEAK HOUR
</text>

<text x="555" y="438"
font-family="{font}"
font-size="13"
fill="#f0f6fc">
{busiest_hour:02d}:00
</text>

<text x="40" y="462"
font-family="{font}"
font-size="11"
fill="#6e7681">
Generated automatically by GitHub Actions
</text>

</svg>
'''

os.makedirs("profile", exist_ok=True)

with open("profile/activity.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print(f"Repositories: {len(repositories)}")
print(f"Commits: {total}")
print(f"Busiest day: {days[busiest_day]}")
print(f"Busiest hour: {busiest_hour:02d}:00")
