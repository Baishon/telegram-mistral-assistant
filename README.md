# Telegram Mistral inline-бот

Бот работает через Telegram Bot API, без входа в личный аккаунт и без кода подтверждения. В любом чате, включая личный диалог с другим человеком, введи `@имя_бота запрос`, дождись ответа Mistral в списке результатов и выбери готовый ответ, чтобы отправить его в чат.

Пример:

```text
@my_mistral_helper_bot Объясни, что такое Python в двух предложениях
```

> Telegram требует выбрать inline-результат вручную. Inline-ответы не всегда содержат `inline_message_id`, необходимый боту для редактирования уже отправленного сообщения, поэтому эта версия генерирует ответ до отправки результата в чат.

## Настройка

1. Установите Python 3.10 или новее.
2. Откройте `@BotFather` в Telegram, выполните `/newbot` и сохраните выданный токен.
3. В `@BotFather` выполните `/setinline`, выберите своего бота и задайте текст-подсказку. Это включает ввод `@имя_бота запрос` в любых чатах.
4. Скопируйте `.env.example` в `.env` и заполните:
   - `BOT_TOKEN` — токен, выданный `@BotFather`;
   - `MISTRAL_API_KEY` — секретный API-ключ Mistral;
   - `MISTRAL_AGENT_ID` — ID агента Mistral (значение вида `ag_...`);
   - `MISTRAL_AGENT_VERSION` — необязательно, версия агента, по умолчанию `0`.
5. Установите зависимости:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

6. Запустите обработчик команд:

   ```powershell
   python main.py
   ```

## Где задавать токены

Настройки находятся в корневом файле `.env` рядом с `main.py`:

- `BOT_TOKEN` — токен Telegram-бота от `@BotFather`; не публикуйте его.
- `MISTRAL_API_KEY` — секретный ключ API Mistral.
- `MISTRAL_AGENT_ID` — ID агента Mistral, не API-ключ.
- `MISTRAL_AGENT_VERSION` — версия агента, по умолчанию `0`.

Не добавляйте `.env` в Git и не отправляйте его другим людям.

## Ограничения

- В любом чате запрос вводится как `@имя_бота запрос`; дождись появления готового ответа и выбери его.
- Каждый запрос передается указанному агенту Mistral отдельным вызовом.
- Ответ длиннее лимита Telegram (4096 символов) обрезается.
- Скрипт должен быть запущен, чтобы обрабатывать команды.

## Termux

```sh
pkg update
pkg install git python
git clone https://github.com/Baishon/telegram-mistral-assistant.git
cd telegram-mistral-assistant
cp .env.example .env
nano .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
