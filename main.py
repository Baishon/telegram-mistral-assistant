import asyncio
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from httpx import HTTPError
from mistralai.client import Mistral
from mistralai.client.errors import MistralError, NoResponseError
from telegram import (
    ChosenInlineResult,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ChosenInlineResultHandler,
    ContextTypes,
    InlineQueryHandler,
)


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

MAX_TELEGRAM_MESSAGE_LENGTH = 4096
THINKING_TEXT = "Обдумываю…"
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

    result = make_result(
        THINKING_TEXT,
        THINKING_TEXT,
        f"Нажмите, чтобы отправить запрос: {prompt}",
    )
    await inline_query.answer([result], cache_time=0, is_personal=True)


async def handle_chosen_inline_result(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chosen: ChosenInlineResult | None = update.chosen_inline_result
    if chosen is None or not chosen.query.strip():
        return

    if not chosen.inline_message_id:
        logger.error(
            "Telegram не прислал inline_message_id. Включите inline feedback "
            "для этого бота через /setinlinefeedback в @BotFather."
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
            inputs=[{"role": "user", "content": chosen.query.strip()}],
        )
    except (MistralError, NoResponseError, HTTPError):
        logger.exception("Ошибка при запросе к Mistral")
        answer = (
            "Не получилось связаться с нейросетью. "
            "Проверьте настройки Mistral и попробуйте ещё раз."
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

        answer = answer.strip() or "Нейросеть вернула пустой ответ."
        if len(answer) > MAX_TELEGRAM_MESSAGE_LENGTH:
            answer = answer[: MAX_TELEGRAM_MESSAGE_LENGTH - 1].rstrip() + "…"

    try:
        await context.bot.edit_message_text(
            text=answer,
            inline_message_id=chosen.inline_message_id,
        )
    except TelegramError:
        logger.exception(
            "Не удалось отредактировать inline-сообщение. "
            "Проверьте настройку /setinlinefeedback в @BotFather."
        )


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
    application.add_handler(
        ChosenInlineResultHandler(handle_chosen_inline_result)
    )

    logger.info(
        "Inline-бот запущен. Выберите результат «Обдумываю…» в чате, "
        "чтобы бот заменил его ответом. Остановите Ctrl+C."
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
