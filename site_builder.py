import json
import re
from pathlib import Path
from datetime import datetime

import markdown


ROOT = Path(".")
DOCS = Path("docs")
ARTICLES = DOCS / "articles"
RUNTIME = Path("runtime")

DOCS.mkdir(exist_ok=True)
ARTICLES.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

SITE_NAME = "Emergency Medicine Research"
SITE_SUBTITLE = "A living emergency medicine knowledge observatory"


# --------------------------------------------------
# CSS
# --------------------------------------------------

CSS = """
:root {
    --bg: #f7f7f5;
    --surface: #ffffff;
    --text: #171717;
    --muted: #6b6b6b;
    --border: #e3e3df;
    --accent: #7b1e1e;
    --max-width: 920px;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Helvetica,
        Arial,
        sans-serif;
    line-height: 1.65;
}

header {
    border-bottom: 1px solid var(--border);
    background: var(--surface);
}

.header-inner {
    max-width: var(--max-width);
    margin: auto;
    padding: 34px 24px;
}

.site-title {
    margin: 0;
    font-size: 1.9rem;
    letter-spacing: -0.03em;
}

.site-subtitle {
    color: var(--muted);
    margin-top: 5px;
}

main {
    max-width: var(--max-width);
    margin: auto;
    padding: 40px 24px 80px;
}

.hero {
    margin-bottom: 46px;
}

.hero h1 {
    font-size: 2.6rem;
    line-height: 1.1;
    letter-spacing: -0.04em;
    margin-bottom: 12px;
}

.hero p {
    color: var(--muted);
    font-size: 1.1rem;
}

.article-list {
    display: grid;
    gap: 18px;
}

.card {
    display: block;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    text-decoration: none;
    color: inherit;
    transition: transform 0.12s ease, border-color 0.12s ease;
}

.card:hover {
    transform: translateY(-2px);
    border-color: #bbb;
}

.card-date {
    color: var(--muted);
    font-size: 0.85rem;
}

.card-axis {
    display: inline-block;
    margin-left: 10px;
    color: var(--accent);
    font-size: 0.85rem;
}

.card h2 {
    margin: 8px 0 5px;
    font-size: 1.3rem;
    line-height: 1.3;
}

.card p {
    margin: 0;
    color: var(--muted);
}

.article {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 42px;
}

.article h1 {
    font-size: 2.5rem;
    line-height: 1.12;
    letter-spacing: -0.04em;
}

.article h2 {
    margin-top: 2.3rem;
}

.article h3 {
    margin-top: 1.8rem;
}

.article a {
    color: var(--accent);
}

.article-meta {
    color: var(--muted);
    margin-bottom: 32px;
}

.back {
    display: inline-block;
    margin-bottom: 24px;
    color: var(--muted);
    text-decoration: none;
}

footer {
    max-width: var(--max-width);
    margin: auto;
    padding: 30px 24px 60px;
    color: var(--muted);
    font-size: 0.85rem;
}

@media (max-width: 650px) {
    .article {
        padding: 25px;
    }

    .hero h1,
    .article h1 {
        font-size: 2rem;
    }
}
"""


(DOCS / "style.css").write_text(CSS, encoding="utf-8")


# --------------------------------------------------
# UTILIDADES
# --------------------------------------------------

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def read_selected_topic():
    selected_file = RUNTIME / "selected_topic.json"

    if not selected_file.exists():
        return {}

    try:
        return json.loads(selected_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def extract_topic(markdown_text):
    match = re.search(
        r"\*\*Tema:\*\*\s*(.+)",
        markdown_text
    )

    if match:
        return match.group(1).strip()

    return "Emergency Medicine Update"


def extract_summary(markdown_text):
    cleaned = re.sub(r"#.*", "", markdown_text)
    cleaned = re.sub(r"\*\*", "", cleaned)
    cleaned = re.sub(r"_", "", cleaned)
    cleaned = re.sub(r"\[(.*?)\]\(.*?\)", r"\\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) > 240:
        return cleaned[:237] + "..."

    return cleaned


def html_template(title, body):
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} — {SITE_NAME}</title>
    <link rel="stylesheet" href="../style.css">
</head>

<body>

<header>
    <div class="header-inner">
        <div class="site-title">{SITE_NAME}</div>
        <div class="site-subtitle">{SITE_SUBTITLE}</div>
    </div>
</header>

<main>
{body}
</main>

<footer>
    Automatically generated emergency medicine research observatory.
</footer>

</body>
</html>
"""


# --------------------------------------------------
# PROCESAR INFORMES
# --------------------------------------------------

reports = sorted(
    ROOT.glob("report-*.md"),
    reverse=True
)

articles = []

selected_topic = read_selected_topic()

for report in reports:

    md_text = report.read_text(encoding="utf-8")

    topic = extract_topic(md_text)

    date_match = re.search(
        r"report-(\\d{4}-\\d{2}-\\d{2})",
        report.name
    )

    date_text = (
        date_match.group(1)
        if date_match
        else "unknown"
    )

    axis = ""

    if selected_topic.get("date") == date_text:
        axis = (
            selected_topic
            .get("selected_topic", {})
            .get("axis", "")
        )

    article_slug = (
        f"{date_text}-{slugify(topic)[:60]}"
    )

    article_filename = (
        ARTICLES / f"{article_slug}.html"
    )

    html_content = markdown.markdown(
        md_text,
        extensions=[
            "tables",
            "fenced_code"
        ]
    )

    article_body = f"""
<a class="back" href="../index.html">← All articles</a>

<article class="article">

    <div class="article-meta">
        {date_text}
        {" · " + axis if axis else ""}
    </div>

    {html_content}

</article>
"""

    article_html = html_template(
        topic,
        article_body
    )

    article_filename.write_text(
        article_html,
        encoding="utf-8"
    )

    articles.append({
        "date": date_text,
        "topic": topic,
        "axis": axis,
        "summary": extract_summary(md_text),
        "file": f"articles/{article_slug}.html"
    })


# --------------------------------------------------
# INDEX
# --------------------------------------------------

cards = []

for article in articles:

    axis_html = (
        f'<span class="card-axis">{article["axis"]}</span>'
        if article["axis"]
        else ""
    )

    cards.append(
        f"""
<a class="card" href="{article['file']}">

    <div>
        <span class="card-date">{article['date']}</span>
        {axis_html}
    </div>

    <h2>{article['topic']}</h2>

    <p>{article['summary']}</p>

</a>
"""
    )


index_body = f"""
<section class="hero">

    <h1>Emergency Medicine,<br>one question at a time.</h1>

    <p>
        A continuously growing collection of evidence-based
        emergency medicine updates selected by a living curriculum.
    </p>

</section>

<section class="article-list">

{''.join(cards)}

</section>
"""


index_html = f"""<!doctype html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>{SITE_NAME}</title>

    <link rel="stylesheet" href="style.css">
</head>

<body>

<header>
    <div class="header-inner">
        <div class="site-title">{SITE_NAME}</div>
        <div class="site-subtitle">{SITE_SUBTITLE}</div>
    </div>
</header>

<main>

{index_body}

</main>

<footer>
    Evidence evolves. So does this site.
</footer>

</body>

</html>
"""


(DOCS / "index.html").write_text(
    index_html,
    encoding="utf-8"
)

print(
    f"Web generada: {len(articles)} artículos"
)
