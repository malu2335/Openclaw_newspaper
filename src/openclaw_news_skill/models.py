from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class VerificationIssue:
    severity: str
    finding: str
    source_excerpt_en: str
    translation_excerpt_zh: str
    suggestion: str = ""


@dataclass(slots=True)
class TranslationVerification:
    checker: str = ""
    status: str = "not_checked"
    confidence: float = 0.0
    summary: str = ""
    issues: list[VerificationIssue] = field(default_factory=list)


@dataclass(slots=True)
class Article:
    source: str
    url: str
    title_en: str
    paragraphs_en: list[str] = field(default_factory=list)
    title_zh: str = ""
    paragraphs_zh: list[str] = field(default_factory=list)
    published_date: date | None = None
    verification: TranslationVerification = field(default_factory=TranslationVerification)


@dataclass(slots=True)
class SourceResult:
    source: str
    homepage_url: str
    fetched_urls: list[str]
    articles: list[Article]
