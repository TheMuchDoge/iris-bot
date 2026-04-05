from datetime import date
from github import Github, GithubException
from config import GITHUB_TOKEN, GITHUB_VAULT_REPO

_github = Github(GITHUB_TOKEN)
_repo = _github.get_repo(GITHUB_VAULT_REPO)


def read_file(path: str) -> str:
    try:
        content = _repo.get_contents(path)
        return content.decoded_content.decode("utf-8")
    except GithubException:
        return ""


def append_to_inbox(text: str) -> bool:
    path = "Ideas/Inbox.md"
    try:
        file = _repo.get_contents(path)
        current = file.decoded_content.decode("utf-8")
        new_content = current.rstrip() + f"\n- {text}\n"
        _repo.update_file(path, f"iris: add to inbox", new_content, file.sha)
        return True
    except GithubException:
        return False


def get_vault_context() -> str:
    today = date.today().strftime("%Y-%m-%d")
    files = {
        "Home": "Home.md",
        "Today": f"Daily/{today}.md",
        "Inbox": "Ideas/Inbox.md",
    }
    context_parts = []
    for label, path in files.items():
        content = read_file(path)
        if content:
            context_parts.append(f"### {label} ({path})\n{content}")
    return "\n\n".join(context_parts) if context_parts else "No vault context loaded."
