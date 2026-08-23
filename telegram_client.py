"""Minimal Telegram Bot API client for sending the daily lesson."""

import html
import os

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Telegram hard-limits a single message to 4096 UTF-16 code units. Stay
# comfortably under that so formatting overhead doesn't push us over.
MAX_MESSAGE_LENGTH = 3500


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def build_messages(lesson: dict) -> list[str]:
    """Format the lesson dict into one or more HTML-formatted Telegram messages."""
    vocab_lines = []
    for entry in lesson["vocabulary"]:
        article = entry.get("article") or ""
        word = f"{article} {entry['word']}".strip()
        vocab_lines.append(
            f"• <b>{_escape(word)}</b> — {_escape(entry['english'])}\n"
            f"   <i>{_escape(entry['example_de'])}</i>"
        )

    grammar_examples = "\n".join(f"• {_escape(ex)}" for ex in lesson["grammar_examples"])

    header = (
        f"🇩🇪 <b>German Lesson — {_escape(lesson['date'])}</b>\n"
        f"Level: B1 → B2\n"
    )

    article_section = (
        f"\n📰 <b>{_escape(lesson['article_title_de'])}</b>\n\n"
        f"{_escape(lesson['article_de'])}\n\n"
        f"<i>Summary: {_escape(lesson['article_summary_en'])}</i>\n"
    )

    grammar_section = (
        f"\n📖 <b>Grammar: {_escape(lesson['grammar_topic'])}</b>\n\n"
        f"{_escape(lesson['grammar_explanation_en'])}\n\n"
        f"{grammar_examples}\n"
    )

    vocab_section = "\n📝 <b>Vocabulary</b>\n\n" + "\n".join(vocab_lines)

    sections = [header + article_section, grammar_section, vocab_section]

    messages: list[str] = []
    for section in sections:
        if messages and len(messages[-1]) + len(section) <= MAX_MESSAGE_LENGTH:
            messages[-1] += section
        elif len(section) <= MAX_MESSAGE_LENGTH:
            messages.append(section)
        else:
            # A single section is too long on its own; hard-split it.
            for i in range(0, len(section), MAX_MESSAGE_LENGTH):
                messages.append(section[i : i + MAX_MESSAGE_LENGTH])

    return messages


def send_message(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    response = requests.post(
        TELEGRAM_API.format(token=token),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()


def send_lesson(lesson: dict) -> None:
    for message in build_messages(lesson):
        send_message(message)
