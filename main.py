import os
import httpx
from fastapi import FastAPI, Request, Response, HTTPException

app = FastAPI()

# Эти значения подтянутся из настроек Variables на Railway
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "TOKEN246")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")


# 1. Верификация вебхука в Meta (GET-запрос)
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")


# 2. Прием входящих сообщений от WhatsApp (POST-запрос)
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # Проверяем, что пришло именно сообщение, а не статус "доставлено/прочитано"
        if "messages" in value:
            message = value["messages"][0]
            sender_phone = message["from"]

            if message["type"] == "text":
                text_body = message["text"]["body"]
                await send_whatsapp_message(
                    sender_phone,
                    f"Привет с сервера Railway! Твое сообщение: {text_body}"
                )

    except (KeyError, IndexError):
        pass

    return {"status": "ok"}


# 3. Отправка ответа пользователю через Meta API
async def send_whatsapp_message(to_phone: str, text: str):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            print("Ошибка отправки:", response.text)