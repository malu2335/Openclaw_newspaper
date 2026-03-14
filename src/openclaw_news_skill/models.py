from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class Article:
    source: str
    url: str
    title_en: str
    paragraphs_en: list[str] = field(default_factory=list)
    title_zh: str = ""
    paragraphs_zh: list[str] = field(default_factory=list)
    published_date: date | None = None


@dataclass(slots=True)
class SourceResult:
    source: str
    homepage_url: str
    fetched_urls: list[str]
    articles: list[Article]
