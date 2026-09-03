import os
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from content import generate_lesson


class GenerateLessonRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env_patcher = patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "test-key",
                "GEMINI_MAX_ATTEMPTS": "3",
                "GEMINI_RETRY_INITIAL_DELAY_SECONDS": "2",
            },
            clear=False,
        )
        self.env_patcher.start()

    def tearDown(self) -> None:
        self.env_patcher.stop()

    def _build_client(self, side_effect):
        client = MagicMock()
        client.models.generate_content.side_effect = side_effect
        return client

    @patch("content.time.sleep")
    @patch("content._is_retryable_generation_error")
    @patch("content.genai.Client")
    def test_retries_on_retryable_error(self, mock_client_cls, mock_is_retryable, mock_sleep):
        response = MagicMock()
        response.parsed.model_dump.return_value = {
            "article_title_de": "Titel",
            "article_de": "Artikel",
            "article_summary_en": "Summary",
            "grammar_explanation_en": "Explanation",
            "grammar_examples": ["Beispiel"],
            "vocabulary": [],
        }
        client = self._build_client([RuntimeError("temporary"), response])
        mock_client_cls.return_value = client
        mock_is_retryable.side_effect = [True]

        lesson = generate_lesson(today=date(2026, 9, 3))

        self.assertEqual(client.models.generate_content.call_count, 2)
        mock_sleep.assert_called_once_with(2)
        self.assertEqual(lesson["date"], "2026-09-03")

    @patch("content.time.sleep")
    @patch("content._is_retryable_generation_error")
    @patch("content.genai.Client")
    def test_non_retryable_error_fails_immediately(self, mock_client_cls, mock_is_retryable, mock_sleep):
        client = self._build_client(RuntimeError("fatal"))
        mock_client_cls.return_value = client
        mock_is_retryable.return_value = False

        with self.assertRaises(RuntimeError):
            generate_lesson(today=date(2026, 9, 3))

        self.assertEqual(client.models.generate_content.call_count, 1)
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
