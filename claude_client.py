import anthropic
from config import CLAUDE_API_KEY
from vault import get_vault_context, append_to_inbox, add_task_to_daily
from system_prompt import SYSTEM_PROMPT

_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# In-memory conversation history per user — resets on server restart
_history: dict[int, list] = {}
MAX_HISTORY = 20  # max messages to keep per user


def _get_history(user_id: int) -> list:
    return _history.get(user_id, [])


def _add_to_history(user_id: int, role: str, content: str) -> None:
    if user_id not in _history:
        _history[user_id] = []
    _history[user_id].append({"role": role, "content": content})
    if len(_history[user_id]) > MAX_HISTORY:
        _history[user_id] = _history[user_id][-MAX_HISTORY:]


# Write triggers — handled in code before Claude sees the message
_TASK_TRIGGERS = ("add task:", "legg til oppgave:")
_INBOX_TRIGGERS = ("add idea:", "add to inbox:", "note that", "jot down", "legg til:", "skriv at")


def _check_write(text: str) -> tuple[str, str] | None:
    """Returns (type, content) if this is a write request, else None."""
    lower = text.lower()
    for trigger in _TASK_TRIGGERS:
        if lower.startswith(trigger):
            return "task", text[len(trigger):].strip()
    for trigger in _INBOX_TRIGGERS:
        if lower.startswith(trigger):
            return "inbox", text[len(trigger):].strip()
    return None


def ask_iris(user_id: int, user_message: str) -> str:
    # Handle writes directly — never let Claude hallucinate these
    write = _check_write(user_message)
    if write:
        action, content = write
        if action == "task":
            success = add_task_to_daily(content)
            reply = f'Done. Added to today\'s tasks: "{content}"' if success else "Couldn't write to your vault right now."
        else:
            success = append_to_inbox(content)
            reply = f'Got it. Added to your Inbox: "{content}"' if success else "Couldn't write to your vault right now."
        _add_to_history(user_id, "user", user_message)
        _add_to_history(user_id, "assistant", reply)
        return reply

    # Build messages with history for context
    vault_context = get_vault_context()
    full_system = SYSTEM_PROMPT + "\n\n## Current Vault Context\n" + vault_context

    history = _get_history(user_id)
    messages = history + [{"role": "user", "content": user_message}]

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=full_system,
        messages=messages,
    )

    reply = response.content[0].text
    _add_to_history(user_id, "user", user_message)
    _add_to_history(user_id, "assistant", reply)
    return reply
