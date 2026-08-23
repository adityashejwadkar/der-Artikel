"""Generates the daily German lesson content via the OpenAI API."""

import json
import os
from datetime import date

from openai import OpenAI

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

DEFAULT_MODEL = "gpt-4o-mini"

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "german_lesson",
        "schema": {
            "type": "object",
            "properties": {
                "article_title_de": {"type": "string"},
                "article_de": {
                    "type": "string",
                    "description": "180-220 word German article at CEFR B1-B2 level.",
                },
                "article_summary_en": {
                    "type": "string",
                    "description": "One or two sentence English summary of the article.",
                },
                "grammar_explanation_en": {
                    "type": "string",
                    "description": "Concise English explanation (~120-180 words) of the assigned grammar topic, referencing German examples.",
                },
                "grammar_examples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-4 German example sentences (with English translation in parentheses) illustrating the grammar topic. Ideally drawn from or related to the article.",
                },
                "vocabulary": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "word": {"type": "string"},
                            "article": {
                                "type": "string",
                                "description": "der/die/das for nouns, or empty string for non-nouns.",
                            },
                            "english": {"type": "string"},
                            "example_de": {"type": "string"},
                        },
                        "required": ["word", "article", "english", "example_de"],
                        "additionalProperties": False,
                    },
                    "minItems": 8,
                    "maxItems": 10,
                    "description": "Useful B1-B2 vocabulary drawn from the article.",
                },
            },
            "required": [
                "article_title_de",
                "article_de",
                "article_summary_en",
                "grammar_explanation_en",
                "grammar_examples",
                "vocabulary",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def pick_grammar_topic(today: date) -> str:
    return GRAMMAR_TOPICS[today.toordinal() % len(GRAMMAR_TOPICS)]


def pick_topic_category(today: date) -> str:
    return TOPIC_CATEGORIES[today.weekday()]


def generate_lesson(today: date | None = None) -> dict:
    """Call the OpenAI API and return the structured lesson content."""
    today = today or date.today()
    grammar_topic = pick_grammar_topic(today)
    topic_category = pick_topic_category(today)

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)

    system_prompt = (
        "You are an experienced German language tutor preparing a daily lesson "
        "for a self-study learner who currently reads/writes at CEFR B1 and is "
        "working towards B2. The article should be fully in German, natural and "
        "engaging, slightly stretching the learner (B1-B2), avoiding rare or "
        "archaic vocabulary. The grammar explanation and vocabulary glosses are "
        "in English so the learner can self-check. Respond only with the "
        "requested JSON."
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

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=RESPONSE_SCHEMA,
    )

    lesson = json.loads(completion.choices[0].message.content)
    lesson["grammar_topic"] = grammar_topic
    lesson["topic_category"] = topic_category
    lesson["date"] = today.isoformat()
    return lesson
