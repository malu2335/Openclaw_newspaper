from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(slots=True)
class SkillConfig:
    output_dir: Path = Path("output")
    max_articles_per_source: int = 5
    translation_provider: str = "openai"
    openai_model: str = "gpt-4.1-mini"
    openai_api_key: str | None = None
    deepl_api_key: str | None = None
    perplexity_api_key: str | None = None
    perplexity_model: str = "sonar-pro"
    enable_perplexity_check: bool = False
    verification_max_pairs: int = 8
    auth_dir: Path = Path(".auth_states")
    browser_headless: bool = True

    @classmethod
    def from_env(cls) -> "SkillConfig":
        pplx_key = os.getenv("PERPLEXITY_API_KEY") or os.getenv("PPLX_API_KEY")
        default_enable_perplexity = bool(pplx_key)
        return cls(
            output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
            max_articles_per_source=int(os.getenv("MAX_ARTICLES_PER_SOURCE", "5")),
            translation_provider=os.getenv("TRANSLATION_PROVIDER", "openai").lower(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            deepl_api_key=os.getenv("DEEPL_API_KEY"),
            perplexity_api_key=pplx_key,
            perplexity_model=os.getenv("PERPLEXITY_MODEL", "sonar-pro"),
            enable_perplexity_check=_env_bool("ENABLE_PERPLEXITY_CHECK", default_enable_perplexity),
            verification_max_pairs=int(os.getenv("VERIFICATION_MAX_PAIRS", "8")),
            auth_dir=Path(os.getenv("AUTH_DIR", ".auth_states")),
            browser_headless=_env_bool("BROWSER_HEADLESS", True),
        )
