from __future__ import annotations

from datetime import date, datetime

from .config import SkillConfig
from .crawler import fetch_articles_for_source
from .models import Article
from .pdf_writer import write_bilingual_pdf
from .translate import Translator, build_translator
from .verifier import TranslationVerifier, build_verifier


def parse_target_date(raw_date: str) -> date:
    raw = raw_date.strip().lower()
    if raw == "today":
        return date.today()
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _translate_article(article: Article, translator: Translator, verifier: TranslationVerifier) -> Article:
    article.title_zh = translator.translate(article.title_en)
    article.paragraphs_zh = [translator.translate(p) for p in article.paragraphs_en]
    article.verification = verifier.verify(article)
    return article


def run_daily_pipeline(config: SkillConfig, target_date: date, sources: list[str]) -> tuple[str, list[Article]]:
    translator = build_translator(
        provider=config.translation_provider,
        openai_api_key=config.openai_api_key,
        deepl_api_key=config.deepl_api_key,
        openai_model=config.openai_model,
        openai_base_url=config.openai_base_url,
    )
    verifier = build_verifier(
        enable_perplexity_check=config.enable_perplexity_check,
        perplexity_api_key=config.perplexity_api_key,
        perplexity_model=config.perplexity_model,
        max_pairs=config.verification_max_pairs,
    )

    all_articles: list[Article] = []
    for source_key in sources:
        result = fetch_articles_for_source(
            source_key=source_key,
            auth_dir=config.auth_dir,
            target_date=target_date,
            max_articles=config.max_articles_per_source,
            headless=config.browser_headless,
        )
        for article in result.articles:
            all_articles.append(_translate_article(article, translator, verifier))

    if not all_articles:
        raise RuntimeError("未抓取到可用文章，请检查登录态、订阅权限或日期过滤条件。")

    output_pdf = write_bilingual_pdf(config.output_dir, target_date, all_articles)
    return str(output_pdf), all_articles
