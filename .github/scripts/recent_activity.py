import os
from datetime import datetime, timezone
from pathlib import Path

import requests

USER = os.environ["GITHUB_USER"]
TOKEN = os.environ["GITHUB_TOKEN"]

API = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
}

session = requests.Session()
session.headers.update(HEADERS)


def get(url, params=None):
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def get_repositories():
    repositories = []

    for page in range(1, 11):
        data = get(
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

    return [
        repo
        for repo in repositories
        if not repo.get("fork")
        and not repo.get("archived")
        and not repo.get("disabled")
    ]


def get_recent_commits(repo):
    owner = repo["owner"]["login"]
    name = repo["name"]

    try:
        return get(
            f"{API}/repos/{owner}/{name}/commits",
            {
                "author": USER,
                "per_page": 10,
            },
        )
    except requests.HTTPError:
        return []


repositories = get_repositories()

all_commits = []

for repo in repositories[:30]:
    for commit in get_recent_commits(repo):
        commit_data = commit.get("commit", {})
        author = commit_data.get("author", {})

        date = author.get("date")
        message = commit_data.get("message", "").splitlines()[0]

        if not date:
            continue

        all_commits.append(
            {
                "repo": repo["name"],
                "message": message,
                "date": datetime.fromisoformat(
                    date.replace("Z", "+00:00")
                ),
                "sha": commit.get("sha", "")[:7],
            }
        )


all_commits.sort(
    key=lambda item: item["date"],
    reverse=True,
)

recent = all_commits[:8]

repo_activity = {}

for commit in all_commits:
    repo_activity[commit["repo"]] = (
        repo_activity.get(commit["repo"], 0) + 1
    )

top_repositories = sorted(
    repo_activity.items(),
    key=lambda item: item[1],
    reverse=True,
)[:5]


def escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


WIDTH = 1000
HEIGHT = 700

bg = "#0d1117"
panel = "#161b22"
border = "#30363d"
text = "#f0f6fc"
muted = "#8b949e"
accent = "#58a6ff"
green = "#3fb950"

font = "JetBrains Mono, DejaVu Sans Mono, monospace"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
width="{WIDTH}"
height="{HEIGHT}"
viewBox="0 0 {WIDTH} {HEIGHT}">

<rect width="100%" height="100%" fill="{bg}"/>

<text x="42" y="48"
font-family="{font}"
font-size="26"
font-weight="700"
fill="{text}">
FURRUKA // RECENT ACTIVITY
</text>

<text x="42" y="76"
font-family="{font}"
font-size="13"
fill="{muted}">
LIVE PROJECT TELEMETRY
</text>

<line x1="42" y1="96" x2="958" y2="96"
stroke="{border}"/>

<rect x="42" y="120" width="610" height="500"
rx="10"
fill="{panel}"
stroke="{border}"/>

<text x="68" y="155"
font-family="{font}"
font-size="16"
font-weight="700"
fill="{text}">
RECENT COMMITS
</text>
'''

y = 195

if recent:
    for item in recent:
        date = item["date"].astimezone(timezone.utc)
        date_text = date.strftime("%Y-%m-%d %H:%M")

        repo = escape(item["repo"])
        message = escape(item["message"])

        if len(message) > 58:
            message = message[:55] + "..."

        svg += f'''
<circle cx="74" cy="{y - 5}" r="5" fill="{green}"/>

<text x="92" y="{y}"
font-family="{font}"
font-size="12"
fill="{muted}">
{date_text} UTC
</text>

<text x="250" y="{y}"
font-family="{font}"
font-size="12"
font-weight="700"
fill="{accent}">
{repo}
</text>

<text x="92" y="{y + 24}"
font-family="{font}"
font-size="13"
fill="{text}">
{message}
</text>

<line x1="68" y1="{y + 45}" x2="625" y2="{y + 45}"
stroke="{border}"/>
'''

        y += 58
else:
    svg += f'''
<text x="68" y="205"
font-family="{font}"
font-size="13"
fill="{muted}">
No recent public commits found.
</text>
'''


svg += f'''
<rect x="680" y="120" width="278" height="500"
rx="10"
fill="{panel}"
stroke="{border}"/>

<text x="705" y="155"
font-family="{font}"
font-size="16"
font-weight="700"
fill="{text}">
ACTIVE REPOSITORIES
</text>
'''

y = 200

if top_repositories:
    for index, (repo, count) in enumerate(top_repositories, start=1):
        repo = escape(repo)

        svg += f'''
<text x="706" y="{y}"
font-family="{font}"
font-size="13"
fill="{muted}">
{index:02d}
</text>

<text x="745" y="{y}"
font-family="{font}"
font-size="13"
font-weight="700"
fill="{text}">
{repo}
</text>

<text x="915" y="{y}"
font-family="{font}"
font-size="13"
text-anchor="end"
fill="{accent}">
{count}
</text>
'''

        y += 55
else:
    svg += f'''
<text x="706" y="200"
font-family="{font}"
font-size="13"
fill="{muted}">
No repository activity.
</text>
'''


updated = datetime.now(timezone.utc).strftime(
    "%Y-%m-%d %H:%M UTC"
)

svg += f'''
<line x1="705" y1="510" x2="935" y2="510"
stroke="{border}"/>

<text x="705" y="540"
font-family="{font}"
font-size="11"
fill="{muted}">
REPOSITORIES
</text>

<text x="935" y="540"
font-family="{font}"
font-size="11"
text-anchor="end"
fill="{text}">
{len(repositories)}
</text>

<text x="705" y="570"
font-family="{font}"
font-size="11"
fill="{muted}">
COMMITS INDEXED
</text>

<text x="935" y="570"
font-family="{font}"
font-size="11"
text-anchor="end"
fill="{text}">
{len(all_commits)}
</text>

<text x="705" y="600"
font-family="{font}"
font-size="10"
fill="{muted}">
UPDATED
</text>

<text x="935" y="600"
font-family="{font}"
font-size="10"
text-anchor="end"
fill="{text}">
{updated}
</text>

</svg>
'''

output = Path("profile/recent-activity.svg")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(svg, encoding="utf-8")

print(f"Repositories: {len(repositories)}")
print(f"Commits indexed: {len(all_commits)}")
print(f"Recent commits: {len(recent)}")
