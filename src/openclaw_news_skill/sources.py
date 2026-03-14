from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class NewsSource:
    key: str
    homepage_url: str
    login_url: str
    article_url_keywords: tuple[str, ...]
    state_filename: str

    def state_file(self, auth_dir: Path) -> Path:
        return auth_dir / self.state_filename


SOURCES: dict[str, NewsSource] = {
    "nyt": NewsSource(
        key="nyt",
        homepage_url="https://www.nytimes.com/",
        login_url="https://myaccount.nytimes.com/auth/login",
        article_url_keywords=("/20", "/live/", "/briefing/"),
        state_filename="nyt_state.json",
    ),
    "wp": NewsSource(
        key="wp",
        homepage_url="https://www.washingtonpost.com/",
        login_url="https://www.washingtonpost.com/subscribe/signin/",
        article_url_keywords=("/202", "/world/", "/politics/", "/business/"),
        state_filename="wp_state.json",
    ),
    "wsj": NewsSource(
        key="wsj",
        homepage_url="https://www.wsj.com/",
        login_url="https://sso.accounts.dowjones.com/login-page",
        article_url_keywords=("/articles/", "/livecoverage/", "/world/", "/economy/"),
        state_filename="wsj_state.json",
    ),
    "newyorker": NewsSource(
        key="newyorker",
        homepage_url="https://www.newyorker.com/",
        login_url="https://www.newyorker.com/account/sign-in",
        article_url_keywords=("/news/", "/culture/", "/magazine/", "/story/"),
        state_filename="newyorker_state.json",
    ),
    "wired": NewsSource(
        key="wired",
        homepage_url="https://www.wired.com/",
        login_url="https://www.wired.com/account/sign-in",
        article_url_keywords=("/story/",),
        state_filename="wired_state.json",
    ),
}


SOURCE_ALIASES: dict[str, str] = {
    "wierd": "wired",
    "new-yorker": "newyorker",
    "new_yorker": "newyorker",
}


def normalize_source_key(raw: str) -> str:
    key = raw.strip().lower()
    return SOURCE_ALIASES.get(key, key)
