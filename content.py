"""Generates the daily German lesson content via the Google Gemini API."""

import os
import time
from datetime import date

from google import genai
from google.genai import errors
from google.genai import types
from pydantic import BaseModel, Field

# CEFR B1 -> B2 grammar progression. One topic is picked per calendar day
# (deterministically, so re-running the same day yields the same topic) and
# the list repeats once exhausted.
GRAMMAR_TOPICS = [
    "Konjunktiv II (Wünsche, Höflichkeit, irreale Bedingungssätze)",
    "Passiv (Präsens und Präteritum)",
    "Kausale Nebensätze (weil, da)",
    "Konzessive Nebensätze (obwohl, trotzdem)",
    "Konditionale Nebensätze (wenn, falls)",
    "Relativsätze im Nominativ und Akkusativ",
    "Relativsätze im Dativ und Genitiv",
    "Genitiv und Genitivpräpositionen (wegen, trotz, während)",
    "Adjektivdeklination nach bestimmtem Artikel",
    "Adjektivdeklination nach unbestimmtem Artikel und ohne Artikel",
    "Modalverben in der Vergangenheit (Präteritum)",
    "Indirekte Rede und Konjunktiv I",
    "Zweiteilige Konnektoren (nicht nur...sondern auch, entweder...oder, sowohl...als auch)",
    "Partizip I und II als Adjektive",
    "Futur I (Vermutungen und Vorhersagen)",
    "Wechselpräpositionen (Wo? vs. Wohin?)",
    "Verben mit festen Präpositionen",
    "Infinitiv mit zu / um...zu / ohne...zu / statt...zu",
    "Reflexive Verben mit Akkusativ und Dativ",
    "N-Deklination (der Junge, der Name, der Student)",
    "Temporale Nebensätze (als, wenn, während, bevor, nachdem)",
    "Plusquamperfekt",
    "Passiv mit Modalverben",
    "Nominalisierung von Verben",
]

# Rotate the article's subject area by weekday for variety.
TOPIC_CATEGORIES = {
    0: "aktuelle Nachrichten und Politik",
    1: "Kultur, Kunst oder Musik",
    2: "Alltag und Gesellschaft in Deutschland",
    3: "Umwelt und Nachhaltigkeit",
    4: "Technologie und Wissenschaft",
    5: "Reisen und Geografie",
    6: "Gesundheit und Lebensstil",
}

DEFAULT_MODEL = "gemini-3.6-flash"
MAX_GENERATE_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 2


class VocabularyEntry(BaseModel):
    word: str
    article: str = Field(description="der/die/das for nouns, or empty string for non-nouns.")
    english: str
    example_de: str


class Lesson(BaseModel):
    article_title_de: str
    article_de: str = Field(description="180-220 word German article at CEFR B1-B2 level.")
    article_summary_en: str = Field(description="One or two sentence English summary of the article.")
    grammar_explanation_en: str = Field(
        description="Concise English explanation (~120-180 words) of the assigned grammar topic, referencing German examples."
    )
    grammar_examples: list[str] = Field(
        description="3-4 German example sentences (with English translation in parentheses) illustrating the grammar topic."
    )
    vocabulary: list[VocabularyEntry] = Field(
        min_length=8,
        max_length=10,
        description="8-10 useful B1-B2 vocabulary words/phrases drawn from the article.",
    )


def pick_grammar_topic(today: date) -> str:
    return GRAMMAR_TOPICS[today.toordinal() % len(GRAMMAR_TOPICS)]


def pick_topic_category(today: date) -> str:
    return TOPIC_CATEGORIES[today.weekday()]


def _is_retryable_generation_error(exc: Exception) -> bool:
    if isinstance(exc, errors.ServerError):
        status_code = getattr(exc, "status_code", None)
        if status_code in {429, 500, 502, 503, 504}:
            return True
        message = str(exc).upper()
        return "UNAVAILABLE" in message or "RESOURCE_EXHAUSTED" in message
    return False


def generate_lesson(today: date | None = None) -> dict:
    """Call the Gemini API and return the structured lesson content."""
    today = today or date.today()
    grammar_topic = pick_grammar_topic(today)
    topic_category = pick_topic_category(today)

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    system_prompt = (
        "You are an experienced German language tutor preparing a daily lesson "
        "for a self-study learner who currently reads/writes at CEFR B1 and is "
        "working towards B2. The article should be fully in German, natural and "
        "engaging, slightly stretching the learner (B1-B2), avoiding rare or "
        "archaic vocabulary. The grammar explanation and vocabulary glosses are "
        "in English so the learner can self-check."
    )

    user_prompt = (
        f"Date: {today.isoformat()}\n"
        f"Write a German article (180-220 words) about {topic_category}.\n"
        f"Assigned grammar focus for today: {grammar_topic}.\n"
        "Requirements:\n"
        "- article_de: the German article, 180-220 words, B1-B2 level.\n"
        "- article_summary_en: 1-2 sentence English summary.\n"
        "- grammar_explanation_en: explain the assigned grammar topic in English "
        "clearly enough for a B1 learner moving to B2, referencing how it could "
        "apply to the article's content.\n"
        "- grammar_examples: 3-4 German sentences demonstrating the grammar "
        "topic, each followed by its English translation in parentheses.\n"
        "- vocabulary: 8-10 useful words/phrases taken from the article, each "
        "with its article (der/die/das, or empty string if not a noun), an "
        "English meaning, and a German example sentence."
    )

    attempts = max(1, int(os.environ.get("GEMINI_MAX_ATTEMPTS", MAX_GENERATE_ATTEMPTS)))
    delay_seconds = max(1, int(os.environ.get("GEMINI_RETRY_INITIAL_DELAY_SECONDS", INITIAL_RETRY_DELAY_SECONDS)))
    for attempt in range(1, attempts + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=Lesson,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            break
        except Exception as exc:
            if attempt == attempts:
                raise
            if not _is_retryable_generation_error(exc):
                raise
            time.sleep(delay_seconds * (2 ** (attempt - 1)))

    lesson = response.parsed.model_dump()
    lesson["grammar_topic"] = grammar_topic
    lesson["topic_category"] = topic_category
    lesson["date"] = today.isoformat()
    return lesson
