# OpenClaw Skill：NYT / WP / WSJ 每日双语新闻 PDF

本仓库提供一个可执行的 OpenClaw Skill 模板，用于：

1. 抓取 **NYT / Washington Post / WSJ** 每日新闻（支持登录态）
2. 将英文新闻翻译为高质量简体中文
3. 导出中英双语 PDF（英文段落 + 中文段落对照）

> 说明：请确保你对对应站点有合法账号订阅，并遵守各站点服务条款。

---

## 目录结构

```text
.
├── skill.yaml
├── requirements.txt
└── src/openclaw_news_skill
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    ├── config.py
    ├── crawler.py
    ├── models.py
    ├── pdf_writer.py
    ├── pipeline.py
    └── translate.py
```

---

## 1) 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

---

## 2) 配置环境变量

建议创建 `.env`（或由 OpenClaw 平台 Secret 注入）：

```bash
# 翻译服务（二选一）
export TRANSLATION_PROVIDER=openai
export OPENAI_API_KEY=your_openai_key
export OPENAI_MODEL=gpt-4.1-mini

# 如果使用 DeepL：
# export TRANSLATION_PROVIDER=deepl
# export DEEPL_API_KEY=your_deepl_key

# 抓取参数
export OUTPUT_DIR=output
export MAX_ARTICLES_PER_SOURCE=5
export AUTH_DIR=.auth_states
export BROWSER_HEADLESS=true

# 登录凭据（可选，若不提供则可用 --manual）
export NYT_EMAIL=...
export NYT_PASSWORD=...
export WP_EMAIL=...
export WP_PASSWORD=...
export WSJ_EMAIL=...
export WSJ_PASSWORD=...
```

---

## 3) 登录并保存会话

### 自动登录（提供账号密码）

```bash
PYTHONPATH=src python -m openclaw_news_skill.cli login --site all --headless
```

### 手动登录（推荐用于有 MFA 场景）

```bash
PYTHONPATH=src python -m openclaw_news_skill.cli login --site all --manual
```

执行后会在 `.auth_states/` 下写入站点登录态文件（cookie/storage state）。

---

## 4) 执行每日抓取 + 翻译 + 生成 PDF

```bash
PYTHONPATH=src python -m openclaw_news_skill.cli run --date today --sources nyt,wp,wsj
```

指定日期：

```bash
PYTHONPATH=src python -m openclaw_news_skill.cli run --date 2026-03-14
```

输出示例：

```text
output/daily_news_bilingual_2026-03-14.pdf
```

---

## 5) 翻译准确性建议（重点）

为了“译文考究、准确”：

1. 首选 `OPENAI` 或 `DeepL`，并使用低温度设置（本实现已默认 `temperature=0.1`）。
2. 保留事实要素：人名、机构名、数字、时间、引述归属，不做二次演绎。
3. 建议在生产环境加入术语库（金融、宏观、法律术语）并做自动术语一致性检查。
4. 对关键信息（数字、时间、地名）可增加“回译一致性抽样”质检流程。

---

## 6) OpenClaw 接入

- `skill.yaml` 已包含：
  - 权限声明（network/browser/filesystem）
  - 默认入口命令
  - 每日定时触发示例（`0 7 * * *`）

你可按平台规范修改 `author`、`triggers`、`config` 等字段。

