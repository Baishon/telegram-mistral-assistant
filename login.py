import os
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from telethon.errors import SessionPasswordNeededError
from telethon import TelegramClient


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def get_credentials() -> tuple[int, str, str]:
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    session_name = os.getenv("TELEGRAM_SESSION", "data/user_session").strip()

    if not api_id or not api_hash:
        raise RuntimeError(
            "Заполните TELEGRAM_API_ID и TELEGRAM_API_HASH в файле .env "
            "(получить их можно на https://my.telegram.org)."
        )

    try:
        parsed_api_id = int(api_id)
    except ValueError as exc:
        raise RuntimeError("TELEGRAM_API_ID должен быть числом.") from exc

    session_path = Path(session_name)
    if not session_path.is_absolute():
        session_path = ROOT_DIR / session_path
    session_path.parent.mkdir(parents=True, exist_ok=True)

    return parsed_api_id, api_hash, str(session_path)


async def main() -> None:
    api_id, api_hash, session_path = get_credentials()
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()

    try:
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"Аккаунт уже авторизован: {me.first_name or 'аккаунт'}")
            print(f"Файл сессии: {session_path}.session")
            return

        phone = input("Введите номер телефона в международном формате (+...): ").strip()
        if not phone:
            raise RuntimeError("Номер телефона не может быть пустым.")

        sent_code = await client.send_code_request(phone)
        delivery = type(sent_code.type).__name__
        delivery_messages = {
            "SentCodeTypeApp": "код отправлен в Telegram на уже авторизованное устройство",
            "SentCodeTypeSms": "код отправлен по SMS",
            "SentCodeTypeCall": "ожидается звонок с кодом",
            "SentCodeTypeFlashCall": "ожидается автоматический звонок",
        }
        print(
            "Telegram принял запрос на вход: "
            f"{delivery_messages.get(delivery, delivery)}."
        )
        if sent_code.timeout:
            print(f"Если доставка задерживается, подождите {sent_code.timeout} сек.")

        code = input("Введите код из Telegram: ").strip()
        if not code:
            raise RuntimeError("Код подтверждения не может быть пустым.")

        try:
            await client.sign_in(phone, code, phone_code_hash=sent_code.phone_code_hash)
        except SessionPasswordNeededError:
            password = getpass("Введите пароль двухэтапной аутентификации: ")
            await client.sign_in(password=password)

        me = await client.get_me()
        print(f"Вход выполнен: {me.first_name or 'аккаунт'}")
        print(f"Файл сессии: {session_path}.session")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
