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
        if "## Unsorted" in current:
            new_content = current.replace("## Unsorted\n_Raw captures — dump here first_\n", f"## Unsorted\n_Raw captures — dump here first_\n\n- {text}\n", 1)
        else:
            new_content = current.rstrip() + f"\n- {text}\n"
        _repo.update_file(path, "iris: add to inbox", new_content, file.sha)
        return True
    except GithubException:
        return False


def add_task_to_daily(task: str) -> bool:
    today = date.today().strftime("%Y-%m-%d")
    path = f"Daily/{today}.md"
    try:
        file = _repo.get_contents(path)
        current = file.decoded_content.decode("utf-8")
        if "## Tasks" in current:
            new_content = current.replace("## Tasks\n", f"## Tasks\n- [ ] {task}\n", 1)
        else:
            new_content = current + f"\n- [ ] {task}\n"
        _repo.update_file(path, "iris: add task", new_content, file.sha)
        return True
    except GithubException:
        return False


def mark_tasks_completed(items: list[str]) -> tuple[int, int]:
    """Check off matching tasks or add new completed ones. Returns (matched, added)."""
    today = date.today().strftime("%Y-%m-%d")
    path = f"Daily/{today}.md"
    try:
        file = _repo.get_contents(path)
        current = file.decoded_content.decode("utf-8")
        lines = current.split("\n")
        matched = 0
        to_add = []

        for item in items:
            item = item.strip()
            if not item:
                continue
            found = False
            for i, line in enumerate(lines):
                if line.startswith("- [ ]") and item.lower() in line.lower():
                    lines[i] = line.replace("- [ ]", "- [x]", 1)
                    matched += 1
                    found = True
                    break
            if not found:
                to_add.append(item)

        if to_add:
            in_tasks = False
            last_task_idx = -1
            tasks_header_idx = -1
            for i, line in enumerate(lines):
                if line.strip() == "## Tasks":
                    in_tasks = True
                    tasks_header_idx = i
                elif in_tasks:
                    if line.startswith("- ["):
                        last_task_idx = i
                    elif line.startswith("---") or (line.startswith("##") and line.strip() != "## Tasks"):
                        break

            insert_at = last_task_idx + 1 if last_task_idx >= 0 else (tasks_header_idx + 1 if tasks_header_idx >= 0 else len(lines))
            for j, a in enumerate(to_add):
                lines.insert(insert_at + j, f"- [x] {a}")

        new_content = "\n".join(lines)
        _repo.update_file(path, "iris: mark tasks completed", new_content, file.sha)
        return matched, len(to_add)
    except GithubException:
        return 0, 0


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
