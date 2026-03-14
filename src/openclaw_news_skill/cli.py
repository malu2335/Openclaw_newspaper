from __future__ import annotations

import argparse
import os
from pathlib import Path

from .config import SkillConfig
from .sources import SOURCES


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NYT/WP/WSJ 每日双语新闻技能")
    sub = parser.add_subparsers(dest="command", required=True)

    login_cmd = sub.add_parser("login", help="登录并保存各站点 Cookie/会话")
    login_cmd.add_argument("--site", choices=["nyt", "wp", "wsj", "all"], default="all")
    login_cmd.add_argument("--manual", action="store_true", help="手动登录（浏览器中登录后回车）")
    login_cmd.add_argument("--headless", action="store_true", help="以无头模式启动浏览器")

    run_cmd = sub.add_parser("run", help="执行每日抓取+翻译+PDF 导出")
    run_cmd.add_argument("--date", default="today", help="today 或 YYYY-MM-DD")
    run_cmd.add_argument("--sources", default="nyt,wp,wsj", help="逗号分隔，如 nyt,wsj")
    run_cmd.add_argument("--output-dir", default=None, help="输出目录，默认读取 OUTPUT_DIR 或 output")
    run_cmd.add_argument("--max-articles", type=int, default=None, help="每个站点最大文章数")
    run_cmd.add_argument("--translation-provider", choices=["openai", "deepl"], default=None)
    run_cmd.add_argument("--enable-perplexity-check", action="store_true", help="启用 Perplexity 翻译准确性核查")
    run_cmd.add_argument("--disable-perplexity-check", action="store_true", help="关闭 Perplexity 翻译准确性核查")
    run_cmd.add_argument("--perplexity-model", default=None, help="Perplexity 模型，如 sonar-pro")

    return parser


def _env_name(site: str, field: str) -> str:
    return f"{site.upper()}_{field.upper()}"


def _run_login(args: argparse.Namespace, config: SkillConfig) -> None:
    from .crawler import login_and_save_state

    sites = list(SOURCES.keys()) if args.site == "all" else [args.site]
    for site in sites:
        email = os.getenv(_env_name(site, "email"))
        password = os.getenv(_env_name(site, "password"))
        state_file = login_and_save_state(
            source_key=site,
            auth_dir=config.auth_dir,
            headless=args.headless or config.browser_headless,
            email=email,
            password=password,
            manual=args.manual,
        )
        print(f"[ok] {site} 登录态已保存: {state_file}")


def _run_pipeline(args: argparse.Namespace, config: SkillConfig) -> None:
    from .pipeline import parse_target_date, run_daily_pipeline

    if args.output_dir:
        config.output_dir = Path(args.output_dir)
    if args.max_articles is not None:
        config.max_articles_per_source = args.max_articles
    if args.translation_provider:
        config.translation_provider = args.translation_provider
    if args.enable_perplexity_check:
        config.enable_perplexity_check = True
    if args.disable_perplexity_check:
        config.enable_perplexity_check = False
    if args.perplexity_model:
        config.perplexity_model = args.perplexity_model

    target_date = parse_target_date(args.date)
    if config.translation_provider == "openai":
        print(f"[info] 翻译模型: {config.openai_model}")

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    unsupported = [s for s in sources if s not in SOURCES]
    if unsupported:
        raise ValueError(f"不支持的来源: {unsupported}，可选: {list(SOURCES)}")

    output_pdf, articles = run_daily_pipeline(config, target_date=target_date, sources=sources)
    print(f"[ok] 生成完成: {output_pdf}")
    print(f"[ok] 共输出文章: {len(articles)}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    config = SkillConfig.from_env()
    config.auth_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "login":
        _run_login(args, config)
    elif args.command == "run":
        _run_pipeline(args, config)
    else:
        parser.error(f"未知命令: {args.command}")


if __name__ == "__main__":
    main()
