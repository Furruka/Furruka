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


WIDTH = 760
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
width="100%"
height="{HEIGHT}"
viewBox="0 0 {WIDTH} {HEIGHT}"
preserveAspectRatio="xMidYMid meet">

<rect width="100%" height="100%" rx="12" fill="{bg}"/>

<text x="28" y="42"
font-family="{font}"
font-size="22"
font-weight="700"
fill="{text}">
FURRUKA // RECENT ACTIVITY
</text>

<text x="28" y="66"
font-family="{font}"
font-size="11"
fill="{muted}">
LIVE PROJECT TELEMETRY
</text>

<line x1="28" y1="84" x2="732" y2="84"
stroke="{border}"/>

<rect x="28" y="106" width="462" height="510"
rx="10"
fill="{panel}"
stroke="{border}"/>

<text x="50" y="138"
font-family="{font}"
font-size="14"
font-weight="700"
fill="{text}">
RECENT COMMITS
</text>
'''

y = 172

if recent:
    for item in recent:
        date = item["date"].astimezone(timezone.utc)
        date_text = date.strftime("%Y-%m-%d %H:%M")

        repo = escape(item["repo"])
        message = escape(item["message"])

        if len(message) > 47:
            message = message[:44] + "..."

        svg += f'''
<circle cx="56" cy="{y - 4}" r="4" fill="{green}"/>

<text x="70" y="{y}"
font-family="{font}"
font-size="10"
fill="{muted}">
{date_text}
</text>

<text x="218" y="{y}"
font-family="{font}"
font-size="10"
font-weight="700"
fill="{accent}">
{repo}
</text>

<text x="70" y="{y + 21}"
font-family="{font}"
font-size="11"
fill="{text}">
{message}
</text>

<line x1="50" y1="{y + 40}" x2="468" y2="{y + 40}"
stroke="{border}"/>
'''

        y += 57
else:
    svg += f'''
<text x="50" y="190"
font-family="{font}"
font-size="12"
fill="{muted}">
No recent public commits found.
</text>
'''


svg += f'''
<rect x="506" y="106" width="226" height="510"
rx="10"
fill="{panel}"
stroke="{border}"/>

<text x="528" y="138"
font-family="{font}"
font-size="14"
font-weight="700"
fill="{text}">
ACTIVE REPOS
</text>
'''

y = 180

if top_repositories:
    for index, (repo, count) in enumerate(top_repositories, start=1):
        repo = escape(repo)

        if len(repo) > 18:
            repo = repo[:15] + "..."

        svg += f'''
<text x="528" y="{y}"
font-family="{font}"
font-size="11"
fill="{muted}">
{index:02d}
</text>

<text x="557" y="{y}"
font-family="{font}"
font-size="11"
font-weight="700"
fill="{text}">
{repo}
</text>

<text x="708" y="{y}"
font-family="{font}"
font-size="11"
text-anchor="end"
fill="{accent}">
{count}
</text>
'''

        y += 46
else:
    svg += f'''
<text x="528" y="180"
font-family="{font}"
font-size="11"
fill="{muted}">
No repository activity.
</text>
'''


updated = datetime.now(timezone.utc).strftime(
    "%Y-%m-%d %H:%M UTC"
)

svg += f'''
<line x1="528" y1="455" x2="710" y2="455"
stroke="{border}"/>

<text x="528" y="485"
font-family="{font}"
font-size="9"
fill="{muted}">
REPOSITORIES
</text>

<text x="710" y="485"
font-family="{font}"
font-size="9"
text-anchor="end"
fill="{text}">
{len(repositories)}
</text>

<text x="528" y="515"
font-family="{font}"
font-size="9"
fill="{muted}">
COMMITS INDEXED
</text>

<text x="710" y="515"
font-family="{font}"
font-size="9"
text-anchor="end"
fill="{text}">
{len(all_commits)}
</text>

<text x="528" y="545"
font-family="{font}"
font-size="9"
fill="{muted}">
UPDATED
</text>

<text x="710" y="545"
font-family="{font}"
font-size="9"
text-anchor="end"
fill="{text}">
{updated}
</text>

<text x="28" y="650"
font-family="{font}"
font-size="10"
fill="{muted}">
AUTOMATED VIA GITHUB ACTIONS
</text>

</svg>
'''

output = Path("profile/recent-activity.svg")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(svg, encoding="utf-8")

print(f"Repositories: {len(repositories)}")
print(f"Commits indexed: {len(all_commits)}")
print(f"Recent commits: {len(recent)}")
