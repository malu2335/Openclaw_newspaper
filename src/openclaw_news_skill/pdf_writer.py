from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from .models import Article


def _build_styles():
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ZHTitle",
            parent=styles["Heading1"],
            fontName="STSong-Light",
            fontSize=17,
            leading=22,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ZHBody",
            parent=styles["BodyText"],
            fontName="STSong-Light",
            fontSize=11,
            leading=17,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ENBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Meta",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            textColor=colors.grey,
            fontSize=9,
            leading=12,
            spaceAfter=10,
        )
    )
    return styles


def write_bilingual_pdf(output_dir: Path, target_date: date, articles: list[Article]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"daily_news_bilingual_{target_date.isoformat()}.pdf"
    styles = _build_styles()

    story = [
        Paragraph("NYT / WP / WSJ 每日新闻双语学习资料", styles["ZHTitle"]),
        Paragraph(f"生成日期：{target_date.isoformat()}", styles["ZHBody"]),
        Paragraph("English + Chinese | for study reference only", styles["Meta"]),
        Spacer(1, 0.4 * cm),
    ]

    for idx, article in enumerate(articles, start=1):
        story.append(Paragraph(f"{idx}. [{article.source.upper()}] {article.title_en}", styles["Heading2"]))
        if article.title_zh:
            story.append(Paragraph(article.title_zh, styles["ZHTitle"]))
        story.append(Paragraph(article.url, styles["Meta"]))
        if article.published_date:
            story.append(Paragraph(f"Published: {article.published_date.isoformat()}", styles["Meta"]))
        story.append(HRFlowable(color=colors.lightgrey, thickness=0.6))
        story.append(Spacer(1, 0.2 * cm))

        paragraph_count = min(len(article.paragraphs_en), len(article.paragraphs_zh))
        for i in range(paragraph_count):
            story.append(Paragraph(article.paragraphs_en[i], styles["ENBody"]))
            story.append(Paragraph(article.paragraphs_zh[i], styles["ZHBody"]))
            story.append(Spacer(1, 0.1 * cm))

        story.append(PageBreak())

    doc = SimpleDocTemplate(
        str(out_file),
        pagesize=A4,
        leftMargin=1.7 * cm,
        rightMargin=1.7 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Daily Bilingual News {target_date.isoformat()}",
    )
    doc.build(story)
    return out_file
