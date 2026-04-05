import httpx
from fastapi import FastAPI, Request
from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
from claude_client import ask_iris

app = FastAPI()
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def send_message(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    message = data.get("message", {})
    user_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    # Ignore anyone who isn't Odin
    if not user_id or user_id not in ALLOWED_USER_IDS:
        return {"ok": True}

    if not text:
        return {"ok": True}

    reply = ask_iris(text)
    await send_message(chat_id, reply)

    return {"ok": True}


@app.get("/")
async def health():
    return {"status": "Iris is alive"}
