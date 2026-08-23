# derArtikel

**der Artikel** is a German Telegram bot for B2 learners, featuring engaging
German stories, grammar lessons, article practice, and vocabulary to build
practical language skills.

Every morning at 8:00 AM IST it sends a Telegram message with:

- 📰 A short German article (B1→B2 level) with an English summary
- 📖 A grammar lesson (topics rotate daily through a B1→B2 syllabus)
- 📝 8-10 vocabulary words drawn from the article, with gender articles,
  English meanings, and example sentences

Content is generated fresh each day by the Google Gemini API and delivered
via a GitHub Actions scheduled workflow
(`.github/workflows/german-lesson.yml`) — no server to run yourself.

## One-time setup

### 1. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`,
   and follow the prompts. It gives you a **bot token** like
   `123456789:AAExampleTokenAbcDefGhi`.
2. Start a chat with your new bot (search its username and send `/start`),
   or add it to a group/channel you want lessons posted in.

### 2. Get your chat ID

- For a personal DM with the bot: message the bot anything, then open
  `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and
  read `message.chat.id` from the JSON response.
- Alternatively, message [@userinfobot](https://t.me/userinfobot) to get
  your numeric user ID (works as the chat ID for DMs).
- For a group/channel, add the bot as a member/admin, send a message in it,
  then check the same `getUpdates` URL — group chat IDs are negative
  numbers.

### 3. Get a Gemini API key

Create one at <https://aistudio.google.com/apikey>. The free tier is
generous enough for one lesson a day; no billing setup is required to get
started.

### 4. Add repository secrets

In this repo: **Settings → Secrets and variables → Actions → New repository
secret**, and add:

| Secret name          | Value                |
| --------------------- | -------------------- |
| `TELEGRAM_BOT_TOKEN`  | Token from BotFather |
| `TELEGRAM_CHAT_ID`    | Chat ID from step 2  |
| `GEMINI_API_KEY`      | Key from step 3      |

Optionally set the `GEMINI_MODEL` env var in the workflow file to use a
different model (defaults to `gemini-3.6-flash`).

### 5. Done

The workflow runs automatically every day at 08:00 IST (02:30 UTC). To send
a lesson right now to test it, go to **Actions → Daily German Lesson → Run
workflow**.

## Changing the delivery time

Edit the `cron` schedule in `.github/workflows/german-lesson.yml`. GitHub
Actions cron is always in UTC — convert your desired local time to UTC.

## Running locally

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
export GEMINI_API_KEY=...
python main.py
```

## Customizing content

- `content.py` — `GRAMMAR_TOPICS` is the B1→B2 grammar syllabus (rotates
  one topic per day); `TOPIC_CATEGORIES` rotates the article's subject area
  by weekday. Edit either list to change what gets covered.
- `telegram_client.py` — message formatting (HTML) and Telegram sending
  logic.
