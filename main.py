import asyncio
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from httpx import HTTPError
from mistralai.client import Mistral
from mistralai.client.errors import MistralError, NoResponseError
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import Application, InlineQueryHandler, ContextTypes


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

MAX_TELEGRAM_MESSAGE_LENGTH = 4096
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Не задана обязательная настройка {name} в файле .env.")
    return value


def create_ai_client() -> Mistral:
    required_setting("MISTRAL_AGENT_ID")
    return Mistral(api_key=required_setting("MISTRAL_API_KEY"))


def make_result(title: str, text: str, description: str = "") -> InlineQueryResultArticle:
    return InlineQueryResultArticle(
        id=uuid.uuid4().hex,
        title=title,
        description=description[:256] or None,
        input_message_content=InputTextMessageContent(
            text[:MAX_TELEGRAM_MESSAGE_LENGTH]
        ),
    )


async def handle_inline_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    inline_query = update.inline_query
    if inline_query is None:
        return

    prompt = inline_query.query.strip()
    if not prompt:
        await inline_query.answer(
            [
                make_result(
                    "Напишите запрос после имени бота",
                    "Например: @имя_бота объясни, что такое Python",
                    "Затем выберите результат, чтобы отправить ответ в чат.",
                )
            ],
            cache_time=0,
            is_personal=True,
        )
        return

    ai: Mistral = context.application.bot_data["mistral"]
    agent_id: str = context.application.bot_data["agent_id"]
    agent_version: int = context.application.bot_data["agent_version"]

    try:
        response = await asyncio.to_thread(
            ai.beta.conversations.start,
            agent_id=agent_id,
            agent_version=agent_version,
            inputs=[{"role": "user", "content": prompt}],
        )
    except (MistralError, NoResponseError, HTTPError):
        logger.exception("Ошибка при запросе к Mistral")
        result = make_result(
            "Не удалось получить ответ",
            "Не получилось связаться с нейросетью. Проверьте настройки Mistral и попробуйте ещё раз.",
        )
    else:
        answer = ""
        for output in reversed(getattr(response, "outputs", None) or []):
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
            result = make_result(
                "Нейросеть вернула пустой ответ",
                "Попробуйте переформулировать запрос.",
            )
        else:
            answer = answer.strip()
            if len(answer) > MAX_TELEGRAM_MESSAGE_LENGTH:
                answer = answer[: MAX_TELEGRAM_MESSAGE_LENGTH - 1].rstrip() + "…"
            result = make_result("Ответ нейросети", answer, answer)

    await inline_query.answer([result], cache_time=0, is_personal=True)


def main() -> None:
    try:
        agent_version = int(os.getenv("MISTRAL_AGENT_VERSION", "0").strip())
    except ValueError as exc:
        raise RuntimeError("MISTRAL_AGENT_VERSION должен быть числом.") from exc

    application = (
        Application.builder()
        .token(required_setting("BOT_TOKEN"))
        .build()
    )
    application.bot_data["mistral"] = create_ai_client()
    application.bot_data["agent_id"] = required_setting("MISTRAL_AGENT_ID")
    application.bot_data["agent_version"] = agent_version
    application.add_handler(InlineQueryHandler(handle_inline_query))

    logger.info("Inline-бот запущен. Остановите его сочетанием Ctrl+C.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
