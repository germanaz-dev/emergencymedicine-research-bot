import json
import re
import html
from pathlib import Path

import markdown


# ==================================================
# CONFIG
# ==================================================

ROOT = Path(".")
DOCS = Path("docs")
ARTICLES = DOCS / "articles"
SYLLABUS_FILE = Path("curriculum/syllabus.json")
SELECTED_TOPIC_FILE = Path("runtime/selected_topic.json")

SITE_NAME = "Emergency Medicine Research"
SITE_SUBTITLE = "A living emergency medicine knowledge observatory"

DOCS.mkdir(exist_ok=True)
ARTICLES.mkdir(parents=True, exist_ok=True)


# ==================================================
# AXIS LABELS
# ==================================================

AXIS_NAMES = {
    "critical_care": "Critical Care",
    "cardinal_symptoms": "Presenting Complaints",
    "cardiovascular": "Cardiovascular",
    "respiratory": "Respiratory",
    "neurology": "Neurology",
    "infectious": "Infectious Disease",
    "trauma_toxicology": "Trauma & Toxicology",
    "metabolic_internal": "Internal Medicine",
    "vulnerable_populations": "Special Populations",
    "pocus_procedures": "POCUS & Procedures",
    "systems_safety": "Systems & Safety",
    "prehospital": "Prehospital",
    "innovation": "Innovation",
}


# ==================================================
# CSS
# ==================================================

CSS = """
:root {
    --bg: #f6f6f3;
    --surface: #ffffff;
    --text: #171717;
    --muted: #6d6d68;
    --border: #deded8;
    --accent: #7b2020;
    --soft: #f0efeb;
    --max-width: 960px;
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
    background: var(--surface);
    border-bottom: 1px solid var(--border);
}

.header-inner {
    max-width: var(--max-width);
    margin: auto;
    padding: 30px 24px;
}

.site-title {
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: -0.03em;
}

.site-subtitle {
    margin-top: 4px;
    color: var(--muted);
}

main {
    max-width: var(--max-width);
    margin: auto;
    padding: 46px 24px 80px;
}

.hero {
    margin-bottom: 48px;
}

.hero h1 {
    margin: 0 0 14px;
    max-width: 760px;
    font-size: 3rem;
    line-height: 1.06;
    letter-spacing: -0.05em;
}

.hero p {
    max-width: 700px;
    margin: 0;
    color: var(--muted);
    font-size: 1.08rem;
}

.stats {
    margin-top: 22px;
    color: var(--muted);
    font-size: 0.9rem;
}

.article-list {
    display: grid;
    gap: 18px;
}

.card {
    display: block;
    padding: 25px 27px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 13px;
    color: inherit;
    text-decoration: none;
    transition:
        transform 0.12s ease,
        border-color 0.12s ease;
}

.card:hover {
    transform: translateY(-2px);
    border-color: #bab9b2;
}

.card-meta {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 9px;
}

.card-date {
    color: var(--muted);
    font-size: 0.83rem;
}

.badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 999px;
    background: var(--soft);
    color: var(--accent);
    font-size: 0.76rem;
    font-weight: 600;
}

.card h2 {
    margin: 0 0 8px;
    font-size: 1.35rem;
    line-height: 1.28;
    letter-spacing: -0.02em;
}

.card p {
    margin: 0;
    color: var(--muted);
}

.article {
    padding: 44px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 13px;
}

.article h1 {
    margin-top: 0;
    font-size: 2.5rem;
    line-height: 1.12;
    letter-spacing: -0.04em;
}

.article h2 {
    margin-top: 2.3rem;
}

.article h3 {
    margin-top: 1.7rem;
}

.article a {
    color: var(--accent);
    overflow-wrap: anywhere;
}

.article-meta {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 28px;
    color: var(--muted);
}

.back {
    display: inline-block;
    margin-bottom: 24px;
    color: var(--muted);
    text-decoration: none;
}

.back:hover {
    color: var(--text);
}

footer {
    max-width: var(--max-width);
    margin: auto;
    padding: 30px 24px 60px;
    color: var(--muted);
    font-size: 0.84rem;
}

@media (max-width: 650px) {
    .hero h1 {
        font-size: 2.2rem;
    }

    .article {
        padding: 24px;
    }

    .article h1 {
        font-size: 2rem;
    }
}
"""

(DOCS / "style.css").write_text(CSS, encoding="utf-8")


# ==================================================
# HELPERS
# ==================================================

def load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass

    return default


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def extract_topic(markdown_text):
    match = re.search(
        r"\*\*Tema:\*\*\s*(.+)",
        markdown_text,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return "Emergency Medicine Update"


def extract_date(markdown_text, filename):
    match = re.search(
        r"\*\*Fecha:\*\*\s*(\d{4}-\d{2}-\d{2})",
        markdown_text,
    )

    if match:
        return match.group(1)

    match = re.search(
        r"report-(\d{4}-\d{2}-\d{2})",
        filename,
    )

    if match:
        return match.group(1)

    return ""


def clean_markdown(text):
    patterns = [
        r"_Modelo usado:.*?_",
        r"\*\*Modelo usado:\*\*.*",
        r"No se pudo generar imagen en este run\.?",
        r"Imagen de portada no generada\.?",
        r"Image generation failed\.?",
    ]

    for pattern in patterns:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

    return text


def strip_front_metadata(text):
    lines = text.splitlines()
    cleaned = []

    for line in lines:
        if re.match(
            r"\*\*(Fecha|Tema|Modelo usado):\*\*",
            line,
            flags=re.IGNORECASE,
        ):
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def extract_summary(markdown_text):
    text = clean_markdown(markdown_text)

    match = re.search(
        r"#+\s*(?:\d+\.\s*)?Resumen ejecutivo\s*(.*?)(?=\n#+\s|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        summary = match.group(1)
    else:
        summary = strip_front_metadata(text)

    summary = re.sub(r"#+\s*", "", summary)
    summary = re.sub(r"\*\*", "", summary)
    summary = re.sub(r"__", "", summary)
    summary = re.sub(r"_", "", summary)
    summary = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", summary)
    summary = re.sub(r"\s+", " ", summary).strip()

    if len(summary) > 320:
        summary = summary[:317].rsplit(" ", 1)[0] + "..."

    return summary


# ==================================================
# SYLLABUS LOOKUP
# ==================================================

syllabus = load_json(SYLLABUS_FILE, [])

topic_index = {}

for item in syllabus:
    title = item.get("title", "").strip().lower()

    if title:
        topic_index[title] = item


def find_axis(topic):
    key = topic.strip().lower()

    if key in topic_index:
        return topic_index[key].get("axis", "")

    topic_words = set(key.split())

    best_match = None
    best_overlap = 0

    for item in syllabus:
        candidate_words = set(
            item.get("title", "").lower().split()
        )

        overlap = len(
            topic_words.intersection(candidate_words)
        )

        if overlap > best_overlap:
            best_overlap = overlap
            best_match = item

    if best_match and best_overlap >= 2:
        return best_match.get("axis", "")

    return ""


def axis_label(axis):
    if not axis:
        return ""

    return AXIS_NAMES.get(
        axis,
        axis.replace("_", " ").title(),
    )


# ==================================================
# ARTICLE TEMPLATE
# ==================================================

def article_template(title, body):
    safe_title = html.escape(title)

    return f"""<!doctype html>
<html lang="en">

<head>

    <meta charset="utf-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <title>{safe_title} — {SITE_NAME}</title>

    <link
        rel="stylesheet"
        href="../style.css"
    >

</head>

<body>

<header>
    <div class="header-inner">

        <div class="site-title">
            {SITE_NAME}
        </div>

        <div class="site-subtitle">
            {SITE_SUBTITLE}
        </div>

    </div>
</header>

<main>
{body}
</main>

<footer>
    Evidence evolves. So does this site.
</footer>

</body>

</html>
"""


# ==================================================
# BUILD ARTICLES
# ==================================================

reports = sorted(
    ROOT.glob("report-*.md"),
    reverse=True,
)

articles = []


for report in reports:

    raw_markdown = report.read_text(
        encoding="utf-8"
    )

    cleaned_markdown = clean_markdown(
        raw_markdown
    )

    topic = extract_topic(
        cleaned_markdown
    )

    date_text = extract_date(
        cleaned_markdown,
        report.name,
    )

    axis = find_axis(topic)
    axis_name = axis_label(axis)

    article_slug = (
        f"{date_text}-{slugify(topic)[:70]}"
    )

    article_path = (
        ARTICLES / f"{article_slug}.html"
    )

    article_markdown = strip_front_metadata(
        cleaned_markdown
    )

    rendered_html = markdown.markdown(
        article_markdown,
        extensions=[
            "tables",
            "fenced_code",
        ],
    )

    badge_html = ""

    if axis_name:
        badge_html = (
            f'<span class="badge">'
            f'{html.escape(axis_name)}'
            f'</span>'
        )

    article_body = f"""
<a
    class="back"
    href="../index.html"
>
    ← All articles
</a>

<article class="article">

    <div class="article-meta">

        <span>
            {html.escape(date_text)}
        </span>

        {badge_html}

    </div>

    {rendered_html}

</article>
"""

    final_html = article_template(
        topic,
        article_body,
    )

    article_path.write_text(
        final_html,
        encoding="utf-8",
    )

    articles.append({
        "date": date_text,
        "topic": topic,
        "axis": axis_name,
        "summary": extract_summary(cleaned_markdown),
        "file": f"articles/{article_slug}.html",
    })


# ==================================================
# INDEX CARDS
# ==================================================

cards = []

for article in articles:

    badge_html = ""

    if article["axis"]:
        badge_html = (
            f'<span class="badge">'
            f'{html.escape(article["axis"])}'
            f'</span>'
        )

    card = f"""
<a
    class="card"
    href="{article['file']}"
>

    <div class="card-meta">

        <span class="card-date">
            {html.escape(article['date'])}
        </span>

        {badge_html}

    </div>

    <h2>
        {html.escape(article['topic'])}
    </h2>

    <p>
        {html.escape(article['summary'])}
    </p>

</a>
"""

    cards.append(card)


# ==================================================
# BUILD INDEX
# ==================================================

article_count = len(articles)

index_html = f"""<!doctype html>
<html lang="en">

<head>

    <meta charset="utf-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <title>{SITE_NAME}</title>

    <link
        rel="stylesheet"
        href="style.css"
    >

</head>

<body>

<header>
    <div class="header-inner">

        <div class="site-title">
            {SITE_NAME}
        </div>

        <div class="site-subtitle">
            {SITE_SUBTITLE}
        </div>

    </div>
</header>

<main>

<section class="hero">

    <h1>
        Emergency Medicine,<br>
        one question at a time.
    </h1>

    <p>
        A continuously growing collection of evidence-based
        emergency medicine updates selected by a living curriculum.
    </p>

    <div class="stats">
        {article_count} published research updates
    </div>

</section>


<section class="article-list">

    {''.join(cards)}

</section>

</main>


<footer>
    Evidence evolves. So does this site.
</footer>

</body>

</html>
"""

(DOCS / "index.html").write_text(
    index_html,
    encoding="utf-8",
)

print(
    f"Web v0.5 generada: {article_count} artículos"
)
