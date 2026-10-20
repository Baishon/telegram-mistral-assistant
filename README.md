# Telegram Mistral inline-бот

Бот работает через Telegram Bot API, без входа в личный аккаунт и без кода подтверждения. В любом чате, включая личный диалог с другим человеком, введи `@имя_бота запрос` и выбери результат. В чат отправится сообщение бота «Обдумываю…», которое бот затем отредактирует, заменив его ответом Mistral.

Пример:

```text
@my_mistral_helper_bot Объясни, что такое Python в двух предложениях
```

> Telegram требует выбрать inline-результат вручную. Бот не может сам отправить сообщение до выбора результата.

## Настройка

1. Установите Python 3.10 или новее.
2. Откройте `@BotFather` в Telegram, выполните `/newbot` и сохраните выданный токен.
3. В `@BotFather` выполните `/setinline`, выберите своего бота и задайте текст-подсказку. Это включает ввод `@имя_бота запрос` в любых чатах.
4. В `@BotFather` выполните `/setinlinefeedback`, выберите своего бота и включите отправку уведомлений о выбранных inline-результатах. Это необходимо, чтобы бот мог получить запрос после отправки сообщения и отредактировать «Обдумываю…» на ответ.
5. Скопируйте `.env.example` в `.env` и заполните:
   - `BOT_TOKEN` — токен, выданный `@BotFather`;
   - `MISTRAL_API_KEY` — секретный API-ключ Mistral;
   - `MISTRAL_AGENT_ID` — ID агента Mistral (значение вида `ag_...`);
   - `MISTRAL_AGENT_VERSION` — необязательно, версия агента, по умолчанию `0`.
6. Установите зависимости:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

7. Запустите обработчик команд:

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

- В любом чате запрос вводится как `@имя_бота запрос`; нужно выбрать результат «Обдумываю…».
- Для последующего редактирования сообщения через Telegram настройка `/setinlinefeedback` у BotFather должна быть включена.
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
