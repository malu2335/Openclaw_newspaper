from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import deepl
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential


class Translator(Protocol):
    def translate(self, text: str) -> str:
        ...


@dataclass(slots=True)
class OpenAITranslator:
    api_key: str
    model: str = "gpt-4.1-mini"
    base_url: str | None = None

    def __post_init__(self) -> None:
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
    def translate(self, text: str) -> str:
        prompt = (
            "You are a professional news translator.\n"
            "Translate the following English news text into accurate, natural Simplified Chinese.\n"
            "Rules:\n"
            "1) Preserve facts, numbers, dates, names, and attributions exactly.\n"
            "2) Keep journalistic tone and concise style.\n"
            "3) Do not add interpretations not in source.\n"
            "4) Use common Chinese media terminology.\n"
            "Return only translated Chinese text.\n\n"
            f"Source text:\n{text}"
        )
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=0.1,
        )
        return response.output_text.strip()


@dataclass(slots=True)
class DeepLTranslator:
    api_key: str

    def __post_init__(self) -> None:
        self.client = deepl.Translator(self.api_key)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
    def translate(self, text: str) -> str:
        result = self.client.translate_text(
            text,
            source_lang="EN",
            target_lang="ZH",
            preserve_formatting=True,
            formality="prefer_more",
        )
        return str(result).strip()


def build_translator(
    provider: str,
    openai_api_key: str | None,
    deepl_api_key: str | None,
    openai_model: str,
    openai_base_url: str | None = None,
) -> Translator:
    provider = provider.lower().strip()
    if provider == "openai":
        if not openai_api_key:
            raise ValueError("TRANSLATION_PROVIDER=openai 时必须设置 OPENAI_API_KEY 或 OPENCLAW_API_KEY")
        return OpenAITranslator(api_key=openai_api_key, model=openai_model, base_url=openai_base_url)
    if provider == "deepl":
        if not deepl_api_key:
            raise ValueError("TRANSLATION_PROVIDER=deepl 时必须设置 DEEPL_API_KEY")
        return DeepLTranslator(api_key=deepl_api_key)
    raise ValueError(f"不支持的翻译提供方: {provider}")
