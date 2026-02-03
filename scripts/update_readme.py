import os
import requests
import re
from datetime import datetime

GITHUB_TOKEN = os.getenv('GH_TOKEN')
USERNAME = os.getenv('GITHUB_REPOSITORY').split('/')[0]

if not GITHUB_TOKEN:
    raise Exception("GH_TOKEN environment variable not set.")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json"
}

def run_query(query, variables=None):
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=HEADERS)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

def get_user_stats():
    # Query to get total commits, PRs, issues, and stars
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
        }
        repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
          totalCount
        }
        pullRequests(first: 1) {
          totalCount
        }
        issues(first: 1) {
          totalCount
        }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            stargazerCount
          }
        }
      }
    }
    """
    
    result = run_query(query, {"login": USERNAME})
    user = result['data']['user']
    
    total_commits = user['contributionsCollection']['totalCommitContributions'] + user['contributionsCollection']['restrictedContributionsCount']
    total_prs = user['pullRequests']['totalCount']
    total_issues = user['issues']['totalCount']
    total_stars = sum(repo['stargazerCount'] for repo in user['repositories']['nodes'])
    
    return {
        "commits": total_commits,
        "prs": total_prs,
        "issues": total_issues,
        "stars": total_stars,
        "repos": user['repositories']['nodes']  # Pass repos for detailed stats if needed
    }

def get_repo_contribution_stats():
    # Query to get top repositories by contributions (commits)
    query = """
    query($login: String!) {
      user(login: $login) {
        repositoriesContributedTo(first: 5, contributionTypes: [COMMIT], orderBy: {field: PUSHED_AT, direction: DESC}) {
          nodes {
            name
            owner {
              login
            }
            stargazerCount
            primaryLanguage {
              name
              color
            }
          }
        }
      }
    }
    """
    result = run_query(query, {"login": USERNAME})
    return result['data']['user']['repositoriesContributedTo']['nodes']

def update_readme(stats, top_repos):
    readme_path = "README.md"
    with open(readme_path, "r") as f:
        content = f.read()
    
    # Generate Stats Table
    stats_markdown = f"""
| 🌟 Stars | 🔨 Commits | 🔀 PRs | 🐛 Issues |
| :---: | :---: | :---: | :---: |
| {stats['stars']} | {stats['commits']} | {stats['prs']} | {stats['issues']} |

### 🏆 Top Contributed Repositories

| Repository | ⭐ Stars | 💻 Language |
| :--- | :---: | :--- |
"""
    
    for repo in top_repos:
        lang_name = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else "N/A"
        lang_color = repo['primaryLanguage']['color'] if repo['primaryLanguage'] else "#ccc"
        # Using a simple circle character for color if markdown supports it, or just text
        stats_markdown += f"| [{repo['owner']['login']}/{repo['name']}](https://github.com/{repo['owner']['login']}/{repo['name']}) | {repo['stargazerCount']} | <span style='color: {lang_color}'>●</span> {lang_name} |\n"

    # Replace content between markers
    pattern = r"<!--START_SECTION:stats-->(.*?)<!--END_SECTION:stats-->"
    replacement = f"<!--START_SECTION:stats-->{stats_markdown}<!--END_SECTION:stats-->"
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open(readme_path, "w") as f:
        f.write(new_content)

if __name__ == "__main__":
    print(f"Fetching stats for {USERNAME}...")
    stats = get_user_stats()
    top_repos = get_repo_contribution_stats()
    print(f"Stats fetched. Top repos: {len(top_repos)}")
    update_readme(stats, top_repos)
    print("README updated successfully.")
