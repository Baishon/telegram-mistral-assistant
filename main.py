import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from httpx import HTTPError
from mistralai.client import Mistral
from mistralai.client.errors import MistralError, NoResponseError
from telethon import TelegramClient, events


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

MAX_TELEGRAM_MESSAGE_LENGTH = 4096


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Не задана обязательная настройка {name} в файле .env.")
    return value


def create_client() -> TelegramClient:
    try:
        api_id = int(required_setting("TELEGRAM_API_ID"))
    except ValueError as exc:
        raise RuntimeError("TELEGRAM_API_ID должен быть числом.") from exc

    api_hash = required_setting("TELEGRAM_API_HASH")
    session_name = os.getenv("TELEGRAM_SESSION", "data/user_session").strip()
    session_path = Path(session_name)
    if not session_path.is_absolute():
        session_path = ROOT_DIR / session_path
    session_path.parent.mkdir(parents=True, exist_ok=True)

    return TelegramClient(str(session_path), api_id, api_hash)


def create_ai_client() -> Mistral:
    required_setting("MISTRAL_AGENT_ID")
    return Mistral(api_key=required_setting("MISTRAL_API_KEY"))


async def main() -> None:
    telegram = create_client()
    ai = create_ai_client()
    agent_id = required_setting("MISTRAL_AGENT_ID")
    try:
        agent_version = int(os.getenv("MISTRAL_AGENT_VERSION", "0").strip())
    except ValueError as exc:
        raise RuntimeError("MISTRAL_AGENT_VERSION должен быть числом.") from exc

    @telegram.on(events.NewMessage(outgoing=True))
    async def handle_personal_command(event: events.NewMessage.Event) -> None:
        text = event.raw_text.strip()
        parts = text.split(maxsplit=1)
        if not parts or parts[0].lower() != "/bot":
            return

        if len(parts) < 2 or not parts[1].strip():
            await event.edit("Использование: /bot ваш запрос")
            return

        prompt = parts[1].strip()
        await event.edit("Обдумываю…")

        try:
            response = await asyncio.to_thread(
                ai.beta.conversations.start,
                agent_id=agent_id,
                agent_version=agent_version,
                inputs=[{"role": "user", "content": prompt}],
            )
        except (MistralError, NoResponseError, HTTPError) as exc:
            print(f"Ошибка API нейросети: {exc}")
            await event.edit(
                "Не удалось получить ответ нейросети. Проверьте MISTRAL_API_KEY, "
                "настройки API и журнал запуска."
            )
            return

        outputs = getattr(response, "outputs", None)
        answer = ""
        for output in reversed(outputs or []):
            if getattr(output, "type", None) != "message.output":
                continue
            content = getattr(output, "content", None)
            if isinstance(content, str):
                answer = content
            elif isinstance(content, list):
                answer = "\n".join(
                    item.text
                    for item in content
                    if isinstance(getattr(item, "text", None), str)
                )
            if answer.strip():
                break

        if not answer.strip():
            await event.edit("Нейросеть вернула пустой ответ.")
            return

        answer = answer.strip()
        if len(answer) > MAX_TELEGRAM_MESSAGE_LENGTH:
            answer = answer[: MAX_TELEGRAM_MESSAGE_LENGTH - 1].rstrip() + "…"
        await event.edit(answer)

    await telegram.start()
    me = await telegram.get_me()
    print(f"Личный аккаунт подключен: {me.first_name or 'аккаунт'}")
    print("Отправьте в Telegram сообщение вида: /bot ваш запрос")

    await telegram.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
