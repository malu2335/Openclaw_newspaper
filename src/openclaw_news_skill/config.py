from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SkillConfig:
    output_dir: Path = Path("output")
    max_articles_per_source: int = 5
    translation_provider: str = "openai"
    openai_model: str = "gpt-4.1-mini"
    openai_api_key: str | None = None
    deepl_api_key: str | None = None
    auth_dir: Path = Path(".auth_states")
    browser_headless: bool = True

    @classmethod
    def from_env(cls) -> "SkillConfig":
        return cls(
            output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
            max_articles_per_source=int(os.getenv("MAX_ARTICLES_PER_SOURCE", "5")),
            translation_provider=os.getenv("TRANSLATION_PROVIDER", "openai").lower(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            deepl_api_key=os.getenv("DEEPL_API_KEY"),
            auth_dir=Path(os.getenv("AUTH_DIR", ".auth_states")),
            browser_headless=os.getenv("BROWSER_HEADLESS", "true").lower() == "true",
        )
