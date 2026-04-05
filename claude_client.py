import anthropic
from config import CLAUDE_API_KEY
from vault import get_vault_context, append_to_inbox
from system_prompt import SYSTEM_PROMPT

_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

_WRITE_TRIGGERS = ("add idea:", "add to inbox:", "note that", "jot down", "legg til", "skriv at")


def _is_write_request(text: str) -> tuple[bool, str]:
    lower = text.lower()
    for trigger in _WRITE_TRIGGERS:
        if lower.startswith(trigger):
            content = text[len(trigger):].strip()
            return True, content
    return False, ""


def ask_iris(user_message: str) -> str:
    is_write, content = _is_write_request(user_message)
    if is_write:
        success = append_to_inbox(content)
        if success:
            return f'Got it. Added to your Inbox: "{content}"'
        else:
            return "I couldn't write to your vault right now. Check the GitHub connection."

    vault_context = get_vault_context()
    full_system = SYSTEM_PROMPT + "\n\n" + vault_context

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=full_system,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
