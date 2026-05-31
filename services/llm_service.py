"""LLM service for AI-powered receipt field extraction via OpenAI-compatible API."""

import json
import logging
from typing import Optional
from datetime import datetime
from openai import OpenAI

from config import LLM_SYSTEM_PROMPT, LLM_USER_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LlamaService:
    """Extracts receipt fields via any OpenAI-compatible API (DeepSeek, Groq, etc.)."""

    _MAX_INPUT_CHARS = 2000

    def __init__(self, api_key: str, model: str, base_url: str,
                 enabled: bool = True):
        self.enabled = enabled
        self._model = model
        if not enabled:
            logger.warning("LLM service disabled via config")
            self._client = None
        elif not api_key:
            logger.warning(
                "LLM_API_KEY not set — LLM receipt parsing disabled. "
                "Set the LLM_API_KEY environment variable or edit config.py"
            )
            self._client = None
        else:
            logger.info("LLM service enabled with model %s at %s", model, base_url)
            self._client = OpenAI(api_key=api_key, base_url=base_url)

    def warm_up(self):
        pass

    def extract_receipt_fields(self, raw_text: str) -> Optional[dict]:
        if self._client is None:
            return None

        truncated = self._truncate(raw_text)
        logger.info("=== LLM API CALL ===")
        logger.info("Model: %s", self._model)
        logger.info("OCR input text (%d chars):\n%s", len(raw_text), raw_text)

        user_content = LLM_USER_PROMPT.replace("{ocr_text}", truncated)

        messages = [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.0,
                max_tokens=256,
            )
            text = response.choices[0].message.content.strip()
            logger.info("LLM raw response:\n%s", text)
        except Exception as exc:
            logger.warning("LLM API call failed: %s", exc)
            return None

        result = self._parse_output(text)
        if result:
            result = self._fix_date_year(result)
            logger.info("LLM extracted fields: %s", result)
        else:
            logger.warning("LLM output parsing failed — output was: %.200s", text)
        logger.info("=== LLM API END ===")
        return result

    @staticmethod
    def _truncate(text: str) -> str:
        if len(text) <= LlamaService._MAX_INPUT_CHARS:
            return text
        return "...\n" + text[-LlamaService._MAX_INPUT_CHARS:]

    @staticmethod
    def _parse_output(text: str) -> Optional[dict]:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            logger.warning("No JSON found in API output: %.100s", text)
            return None

        json_str = text[start:end + 1]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from API: %.100s", json_str)
            return None

        result = {}
        if "amount" in data and data["amount"] is not None:
            try:
                result["amount"] = float(data["amount"])
            except (ValueError, TypeError):
                pass
        if "date" in data and data["date"]:
            result["date"] = str(data["date"])
        if "store_name" in data and data["store_name"]:
            result["store_name"] = str(data["store_name"])

        if not result:
            return None
        return result

    @staticmethod
    def _fix_date_year(result: dict) -> dict:
        """Force the current year on the date if it differs from the actual year."""
        date_str = result.get("date")
        if not date_str:
            return result

        try:
            from datetime import datetime
            now = datetime.now()
            current_year = now.year

            parts = date_str.split("-")
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 4 and int(year) != current_year:
                    result["date"] = f"{day}-{month}-{current_year}"
                    logger.info("Fixed date year from %s to %s", year, current_year)
        except (ValueError, IndexError):
            pass

        return result
