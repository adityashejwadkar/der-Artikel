"""Entry point: generate today's German lesson and send it via Telegram.

Run daily by the `.github/workflows/german-lesson.yml` scheduled workflow.
Required environment variables:
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, OPENAI_API_KEY
Optional:
  OPENAI_MODEL (defaults to gpt-4o-mini)
"""

import sys

from content import generate_lesson
from telegram_client import send_lesson


def main() -> None:
    lesson = generate_lesson()
    send_lesson(lesson)
    print(f"Sent German lesson for {lesson['date']} (grammar: {lesson['grammar_topic']}).")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - surface any failure to the Action log
        print(f"Failed to send German lesson: {exc!r}", file=sys.stderr)
        raise
