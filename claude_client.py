import anthropic
from config import CLAUDE_API_KEY
from vault import get_vault_context, append_to_inbox, add_task_to_daily, mark_tasks_completed
from system_prompt import SYSTEM_PROMPT

_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# In-memory conversation history per user — resets on server restart
_history: dict[int, list] = {}
MAX_HISTORY = 20  # max messages to keep per user

TOOLS = [
    {
        "name": "add_task",
        "description": (
            "Add a task to Odin's daily note. Use this whenever Odin mentions something he needs to do, buy, fix, book, call, or handle — "
            "even if phrased casually (e.g. 'I want to buy a chair', 'remind me to call the dentist', 'I should fix the bike'). "
            "Write the task as a short, actionable item."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Short actionable task description."}
            },
            "required": ["task"],
        },
    },
    {
        "name": "add_to_inbox",
        "description": (
            "Add an idea, thought, or loose note to Odin's vault Inbox. Use this for ideas, things to explore later, "
            "or anything that isn't an immediate actionable task."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The idea or note to capture."}
            },
            "required": ["content"],
        },
    },
    {
        "name": "mark_completed",
        "description": "Mark one or more tasks as completed in today's daily note.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Task descriptions to mark as done.",
                }
            },
            "required": ["items"],
        },
    },
]


def _get_history(user_id: int) -> list:
    return _history.get(user_id, [])


def _add_to_history(user_id: int, role: str, content) -> None:
    if user_id not in _history:
        _history[user_id] = []
    _history[user_id].append({"role": role, "content": content})
    if len(_history[user_id]) > MAX_HISTORY:
        _history[user_id] = _history[user_id][-MAX_HISTORY:]


def _execute_tool(name: str, inputs: dict) -> str:
    if name == "add_task":
        success = add_task_to_daily(inputs["task"])
        return "ok" if success else "error: vault write failed"
    elif name == "add_to_inbox":
        success = append_to_inbox(inputs["content"])
        return "ok" if success else "error: vault write failed"
    elif name == "mark_completed":
        matched, added = mark_tasks_completed(inputs["items"])
        return f"matched={matched} added={added}"
    return "error: unknown tool"


def ask_iris(user_id: int, user_message: str) -> str:
    vault_context = get_vault_context()
    full_system = SYSTEM_PROMPT + "\n\n## Current Vault Context\n" + vault_context

    history = _get_history(user_id)
    messages = history + [{"role": "user", "content": user_message}]

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=full_system,
        messages=messages,
        tools=TOOLS,
    )

    # Tool use loop — Claude may call one or more tools before giving a final reply
    while response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages = messages + [
            {"role": "assistant", "content": response.content},
            {"role": "user", "content": tool_results},
        ]

        response = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=full_system,
            messages=messages,
            tools=TOOLS,
        )

    reply = next(
        (block.text for block in response.content if hasattr(block, "text")),
        "Something went wrong — no reply from Iris."
    )

    # Store only the user message and final text reply in history (not raw tool blocks)
    _add_to_history(user_id, "user", user_message)
    _add_to_history(user_id, "assistant", reply)
    return reply
