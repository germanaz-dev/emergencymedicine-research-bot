import os
import json
import html
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

today = datetime.now().strftime("%Y-%m-%d")
current_year = datetime.now().year
from_year = current_year - 5

filename = f"report-{today}.md"


# --- 0. LEER TEMA ---
with open("tema.txt", "r", encoding="utf-8") as f:
    tema = f.read().strip()


# =========================
# 1. PUBMED COMO EJE
# =========================

def pubmed_search(query, max_results=8):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results,
        "sort": "pub+date"
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    return data.get("esearchresult", {}).get("idlist", [])


def pubmed_fetch(pmids):
    if not pmids:
        return []

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    results = []

    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID", default="")

        title_node = article.find(".//ArticleTitle")
        title = "".join(title_node.itertext()).strip() if title_node is not None else ""
        title = html.unescape(title)

        journal = article.findtext(".//Journal/Title", default="")

        year = article.findtext(".//PubDate/Year", default="")
        medline_date = article.findtext(".//PubDate/MedlineDate", default="")
        pubdate = year or medline_date or "Fecha no disponible"

        abstract_parts = []
        for abstract_node in article.findall(".//AbstractText"):
            label = abstract_node.attrib.get("Label")
            text = "".join(abstract_node.itertext()).strip()

            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)

        abstract_text = "\n".join(abstract_parts).strip()

        authors = []
        for author in article.findall(".//Author"):
            last = author.findtext("LastName", default="")
            fore = author.findtext("ForeName", default="")
            collective = author.findtext("CollectiveName", default="")

            if collective:
                authors.append(collective)
            elif last or fore:
                authors.append(f"{fore} {last}".strip())

        publication_types = [
            pt.text for pt in article.findall(".//PublicationType")
            if pt.text
        ]

        doi = ""
        for aid in article.findall(".//ArticleId"):
            if aid.attrib.get("IdType") == "doi":
                doi = aid.text or ""

        results.append({
            "pmid": pmid,
            "title": title,
            "journal": journal,
            "date": pubdate,
            "authors": authors[:6],
            "publication_types": publication_types,
            "doi": doi,
            "abstract": abstract_text[:5000],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })

    return results


pubmed_query = f"""
({tema})
AND (
    systematic review[Publication Type]
    OR meta-analysis[Publication Type]
    OR randomized controlled trial[Publication Type]
    OR clinical trial[Publication Type]
    OR guideline[Publication Type]
    OR practice guideline[Publication Type]
    OR review[Publication Type]
)
AND ("{from_year}/01/01"[Date - Publication] : "3000"[Date - Publication])
"""

try:
    pubmed_ids = pubmed_search(pubmed_query, max_results=8)
    pubmed_results = pubmed_fetch(pubmed_ids)
except Exception as e:
    print("ERROR PUBMED:")
    print(e)
    pubmed_results = []


def format_pubmed(results):
    if not results:
        return "No se recuperaron resultados relevantes de PubMed."

    text = ""

    for r in results:
        abstract = r["abstract"] or "Abstract no disponible."

        text += f"""
--- PAPER PUBMED ---
Título: {r['title']}
Revista: {r['journal']}
Fecha: {r['date']}
Autores: {', '.join(r['authors'])}
Tipo de publicación: {', '.join(r['publication_types'])}
PMID: {r['pmid']}
DOI: {r['doi']}
URL: {r['url']}

Abstract:
{abstract}
"""

    return text


pubmed_text = format_pubmed(pubmed_results)


# =========================
# 2. TAVILY COMO CONTEXTO
# =========================

tavily_payload = {
    "api_key": TAVILY_API_KEY,
    "query": tema + " recent evidence clinical update emergency medicine review trial guideline",
    "search_depth": "advanced",
    "max_results": 8,
    "include_raw_content": True,
    "include_answer": False,
    "exclude_domains": [
        "merckmanuals.com",
        "msdmanuals.com",
        "wikipedia.org",
        "healthline.com",
        "webmd.com",
        "mayoclinic.org"
    ]
}

try:
    tavily_response = requests.post(
        "https://api.tavily.com/search",
        json=tavily_payload,
        timeout=60
    ).json()
except Exception as e:
    print("ERROR TAVILY:")
    print(e)
    tavily_response = {"results": []}


def source_text(r, max_chars=6000):
    raw = r.get("raw_content")
    snippet = r.get("content", "")
    text = raw if raw else snippet
    return text[:max_chars]


tavily_text = "\n\n".join([
    f"""
--- FUENTE WEB ---
Título: {r.get('title', '')}
URL: {r.get('url', '')}
Score: {r.get('score', '')}

Texto:
{source_text(r)}
"""
    for r in tavily_response.get("results", [])
])


# =========================
# 3. GEMINI CON FALLBACK
# =========================

gemini_models = [
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
]

prompt = f"""
Eres un médico de urgencias experto, editor científico y analista crítico de evidencia.

Tema de actualización:
{tema}

PAPERS RECUPERADOS DE PUBMED:
{pubmed_text}

CONTEXTO WEB COMPLEMENTARIO:
{tavily_text}

INSTRUCCIONES IMPORTANTES:
- PubMed es el eje principal.
- Tavily es solo contexto complementario, señales emergentes o fuentes institucionales.
- No uses manuales generales como fuente principal.
- No inventes PMID, DOI, autores ni revistas.
- Si la evidencia es débil, dilo claramente.
- Diferencia evidencia fuerte, moderada, débil y especulativa.
- El resultado debe ser largo, útil y clínicamente aplicable.
- Extensión orientativa: 1500 a 2200 palabras.
- Escribe para médicos de urgencias y residentes.
- Incluye implicaciones concretas para triaje, diagnóstico, tratamiento, seguridad y derivación.
- Añade una mirada crítica: qué NO sabemos, sesgos, límites y riesgos de sobrerreaccionar.

ESTRUCTURA DEL INFORME:

1. Resumen ejecutivo
2. Qué hay de nuevo o relevante
3. Evidencia científica principal
4. Evidencia por nivel
5. Implicaciones para medicina de urgencias
6. Qué cambia en la práctica
7. Qué NO sabemos todavía
8. Riesgos de interpretación excesiva
9. Bibliografía comentada
   - Separar PubMed
   - Separar otras fuentes web
"""


def gemini_call():
    last_error = None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 8192
        }
    }

    for model in gemini_models:
        for attempt in range(3):
            print(f"Intentando modelo: {model} | intento {attempt + 1}/3")

            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/{model}:generateContent?key={GEMINI_API_KEY}"
            )

            try:
                response = requests.post(url, json=payload, timeout=120)
                res = response.json()

                if "candidates" in res:
                    print(f"Modelo usado: {model}")
                    return res["candidates"][0]["content"]["parts"][0]["text"], model

                print(f"Error con {model}:")
                print(res)
                last_error = res

                time.sleep(10)

            except Exception as e:
                print(f"Excepción con {model}:")
                print(e)
                last_error = str(e)
                time.sleep(10)

    fallback_text = f"""
## Informe no generado automáticamente

No se pudo generar el informe porque todos los modelos disponibles devolvieron error o estaban saturados.

### Tema

{tema}

### Datos sí recuperados

- PubMed: {len(pubmed_results)} resultados recuperados.
- Tavily: {len(tavily_response.get("results", []))} resultados recuperados.

### Último error registrado

```text
{last_error}
