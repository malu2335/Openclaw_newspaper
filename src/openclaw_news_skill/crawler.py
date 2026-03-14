from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dateutil import parser as dt_parser
from playwright.sync_api import Page, sync_playwright
from readability import Document

from .models import Article, SourceResult
from .sources import NewsSource, SOURCES


def _normalize_links(links: Iterable[str], source: NewsSource) -> list[str]:
    seen: set[str] = set()
    filtered: list[str] = []
    homepage_host = urlparse(source.homepage_url).netloc

    for raw in links:
        link = (raw or "").strip()
        if not link.startswith("http"):
            continue
        if urlparse(link).netloc != homepage_host:
            continue
        if not any(k in link for k in source.article_url_keywords):
            continue
        if link in seen:
            continue
        seen.add(link)
        filtered.append(link)
    return filtered


def _extract_published_date(soup: BeautifulSoup) -> date | None:
    candidates = [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "article:published_time"}),
        ("meta", {"name": "pubdate"}),
        ("time", {}),
    ]
    for tag, attrs in candidates:
        node = soup.find(tag, attrs=attrs)
        if not node:
            continue
        text = node.get("content") if tag == "meta" else node.get("datetime") or node.get_text(strip=True)
        if not text:
            continue
        try:
            return dt_parser.parse(text).date()
        except Exception:
            continue
    return None


def _extract_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else "Untitled"


def _extract_paragraphs_from_html(html: str) -> list[str]:
    readable_html = Document(html).summary()
    body_soup = BeautifulSoup(readable_html, "html.parser")
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in body_soup.find_all("p")
        if p.get_text(" ", strip=True) and len(p.get_text(" ", strip=True)) >= 30
    ]
    if paragraphs:
        return paragraphs

    fallback = BeautifulSoup(html, "html.parser")
    return [
        p.get_text(" ", strip=True)
        for p in fallback.find_all("p")
        if p.get_text(" ", strip=True) and len(p.get_text(" ", strip=True)) >= 30
    ]


def _collect_homepage_links(page: Page, source: NewsSource) -> list[str]:
    page.goto(source.homepage_url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(2500)
    links: list[str] = page.eval_on_selector_all(
        "a[href]",
        "elements => elements.map(e => e.href).filter(Boolean)",
    )
    return _normalize_links(links, source)


def login_and_save_state(
    source_key: str,
    auth_dir: Path,
    headless: bool,
    email: str | None = None,
    password: str | None = None,
    manual: bool = False,
) -> Path:
    source = SOURCES[source_key]
    auth_dir.mkdir(parents=True, exist_ok=True)
    state_file = source.state_file(auth_dir)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(source.login_url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(2000)

        if email and password:
            # 各站点登录表单细节不同，使用更稳妥的“候选选择器轮询”策略。
            _try_fill(page, [
                "input[type='email']",
                "input[name='email']",
                "input#username",
                "input[name='username']",
            ], email)
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            _try_fill(page, [
                "input[type='password']",
                "input[name='password']",
                "input#password",
            ], password)
            page.keyboard.press("Enter")
            page.wait_for_timeout(6000)
        elif not manual:
            raise ValueError("未提供账号密码时，请使用 --manual 完成人工登录。")

        if manual:
            print(f"[{source.key}] 请在浏览器中完成登录后按回车继续保存登录态...")
            input()

        context.storage_state(path=str(state_file))
        context.close()
        browser.close()

    return state_file


def _try_fill(page: Page, selectors: list[str], value: str) -> None:
    for selector in selectors:
        locator = page.locator(selector).first
        if locator.count() == 0:
            continue
        try:
            locator.fill(value)
            return
        except Exception:
            continue


def fetch_articles_for_source(
    source_key: str,
    auth_dir: Path,
    target_date: date,
    max_articles: int,
    headless: bool,
) -> SourceResult:
    source = SOURCES[source_key]
    state_file = source.state_file(auth_dir)
    if not state_file.exists():
        raise FileNotFoundError(
            f"{source_key} 尚未登录，请先执行 login 子命令生成登录态文件: {state_file}"
        )

    articles: list[Article] = []
    links: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=str(state_file))
        page = context.new_page()
        links = _collect_homepage_links(page, source)
        candidate_links = links[: max_articles * 8]

        for url in candidate_links:
            if len(articles) >= max_articles:
                break
            article_page = context.new_page()
            try:
                article_page.goto(url, wait_until="domcontentloaded", timeout=90000)
                article_page.wait_for_timeout(2000)
                html = article_page.content()
            except Exception:
                article_page.close()
                continue
            finally:
                if not article_page.is_closed():
                    article_page.close()

            soup = BeautifulSoup(html, "html.parser")
            published = _extract_published_date(soup)
            if published and published != target_date:
                continue
            paragraphs = _extract_paragraphs_from_html(html)
            if len(paragraphs) < 3:
                continue
            articles.append(
                Article(
                    source=source.key,
                    url=url,
                    title_en=_extract_title(soup),
                    paragraphs_en=paragraphs[:20],
                    published_date=published,
                )
            )
        context.close()
        browser.close()

    return SourceResult(
        source=source.key,
        homepage_url=source.homepage_url,
        fetched_urls=links,
        articles=articles,
    )
