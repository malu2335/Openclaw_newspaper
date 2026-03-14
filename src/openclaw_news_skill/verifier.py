from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import Article, TranslationVerification, VerificationIssue


class TranslationVerifier(Protocol):
    def verify(self, article: Article) -> TranslationVerification:
        ...


@dataclass(slots=True)
class NoopVerifier:
    reason: str = "未启用核查"

    def verify(self, article: Article) -> TranslationVerification:
        return TranslationVerification(
            checker="none",
            status="not_checked",
            confidence=0.0,
            summary=self.reason,
            issues=[],
        )


def _clip(text: str, max_len: int = 600) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1] + "…"


@dataclass(slots=True)
class PerplexityVerifier:
    api_key: str
    model: str = "sonar-pro"
    max_pairs: int = 8

    def __post_init__(self) -> None:
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.perplexity.ai")

    @retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
    def verify(self, article: Article) -> TranslationVerification:
        pairs = []
        pair_count = min(len(article.paragraphs_en), len(article.paragraphs_zh), self.max_pairs)
        for i in range(pair_count):
            pairs.append(
                {
                    "index": i + 1,
                    "en": _clip(article.paragraphs_en[i]),
                    "zh": _clip(article.paragraphs_zh[i]),
                }
            )

        if pair_count == 0:
            return TranslationVerification(
                checker="perplexity",
                status="not_checked",
                confidence=0.0,
                summary="缺少中英段落，无法核查。",
                issues=[],
            )

        payload = {
            "source": article.source.upper(),
            "url": article.url,
            "title_en": _clip(article.title_en, 300),
            "title_zh": _clip(article.title_zh, 300),
            "paragraph_pairs": pairs,
        }

        system_prompt = (
            "You are a strict bilingual news translation QA reviewer. "
            "Your job is to check whether Chinese translation is faithful to the English source. "
            "Focus on factual consistency: names, numbers, dates, entities, quote attribution, "
            "causal relations, negation, modality, and policy/economic terminology."
        )
        user_prompt = (
            "Review the translation accuracy and return ONLY a JSON object.\n"
            "Required JSON schema:\n"
            "{\n"
            '  "status": "pass|warn|fail",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "summary_zh": "简体中文总结，1-2句",\n'
            '  "issues": [\n'
            "    {\n"
            '      "severity": "high|medium|low",\n'
            '      "finding": "问题描述（简中）",\n'
            '      "source_excerpt_en": "英文摘录",\n'
            '      "translation_excerpt_zh": "中文摘录",\n'
            '      "suggestion": "修正建议（简中）"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "If no major issue, keep issues empty.\n"
            f"Input:\n{json.dumps(payload, ensure_ascii=False)}"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        parsed = _parse_json(content)
        return _to_verification(parsed)


def _parse_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _to_verification(raw: dict[str, Any]) -> TranslationVerification:
    if not raw:
        return TranslationVerification(
            checker="perplexity",
            status="warn",
            confidence=0.3,
            summary="Perplexity 返回格式无法解析，建议人工抽检。",
            issues=[],
        )

    status = str(raw.get("status", "warn")).lower().strip()
    if status not in {"pass", "warn", "fail"}:
        status = "warn"

    try:
        confidence = float(raw.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(confidence, 1.0))

    issues_raw = raw.get("issues", [])
    issues: list[VerificationIssue] = []
    if isinstance(issues_raw, list):
        for item in issues_raw[:8]:
            if not isinstance(item, dict):
                continue
            issues.append(
                VerificationIssue(
                    severity=str(item.get("severity", "medium")).lower().strip() or "medium",
                    finding=str(item.get("finding", "")).strip(),
                    source_excerpt_en=str(item.get("source_excerpt_en", "")).strip(),
                    translation_excerpt_zh=str(item.get("translation_excerpt_zh", "")).strip(),
                    suggestion=str(item.get("suggestion", "")).strip(),
                )
            )

    return TranslationVerification(
        checker="perplexity",
        status=status,
        confidence=confidence,
        summary=str(raw.get("summary_zh", "")).strip() or "无摘要",
        issues=issues,
    )


def build_verifier(
    *,
    enable_perplexity_check: bool,
    perplexity_api_key: str | None,
    perplexity_model: str,
    max_pairs: int,
) -> TranslationVerifier:
    if not enable_perplexity_check:
        return NoopVerifier(reason="未启用 Perplexity 核查")
    if not perplexity_api_key:
        raise ValueError("已启用 Perplexity 核查，但未配置 PERPLEXITY_API_KEY")
    return PerplexityVerifier(
        api_key=perplexity_api_key,
        model=perplexity_model,
        max_pairs=max_pairs,
    )
