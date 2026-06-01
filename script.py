import os, json, html, time, requests
import xml.etree.ElementTree as ET
from datetime import datetime

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

today = datetime.now().strftime("%Y-%m-%d")
from_year = datetime.now().year - 5
filename = f"report-{today}.md"

with open("tema.txt", "r", encoding="utf-8") as f:
    tema = f.read().strip()

def pubmed_search(query, max_results=8):
    r = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={"db": "pubmed", "term": query, "retmode": "json", "retmax": max_results, "sort": "pub+date"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])

def pubmed_fetch(pmids):
    if not pmids:
        return []
    r = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
        timeout=30,
    )
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID", default="")
        title_node = art.find(".//ArticleTitle")
        title = html.unescape("".join(title_node.itertext()).strip()) if title_node is not None else ""
        journal = art.findtext(".//Journal/Title", default="")
        year = art.findtext(".//PubDate/Year", default="") or art.findtext(".//PubDate/MedlineDate", default="")
        abstract = " ".join("".join(a.itertext()).strip() for a in art.findall(".//AbstractText"))
        ptypes = [p.text for p in art.findall(".//PublicationType") if p.text]
        doi = ""
        for aid in art.findall(".//ArticleId"):
            if aid.attrib.get("IdType") == "doi":
                doi = aid.text or ""
        out.append({
            "pmid": pmid,
            "title": title,
            "journal": journal,
            "date": year,
            "publication_types": ptypes,
            "doi": doi,
            "abstract": abstract[:5000],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })
    return out

pubmed_query = (
    f"({tema}) AND (systematic review[Publication Type] OR meta-analysis[Publication Type] "
    f"OR randomized controlled trial[Publication Type] OR clinical trial[Publication Type] "
    f"OR guideline[Publication Type] OR practice guideline[Publication Type] OR review[Publication Type]) "
    f'AND ("{from_year}/01/01"[Date - Publication] : "3000"[Date - Publication])'
)

try:
    pubmed_results = pubmed_fetch(pubmed_search(pubmed_query))
except Exception as e:
    print("ERROR PUBMED:", e)
    pubmed_results = []

pubmed_text = "\n\n".join(
    [
        "\n".join([
            "--- PAPER PUBMED ---",
            f"Título: {r['title']}",
            f"Revista: {r['journal']}",
            f"Fecha: {r['date']}",
            f"Tipo: {', '.join(r['publication_types'])}",
            f"PMID: {r['pmid']}",
            f"DOI: {r['doi']}",
            f"URL: {r['url']}",
            "",
            "Abstract:",
            r["abstract"] or "Abstract no disponible."
        ])
        for r in pubmed_results
    ]
) or "No se recuperaron resultados relevantes de PubMed."

tavily_payload = {
    "api_key": TAVILY_API_KEY,
    "query": tema + " recent evidence clinical update emergency medicine review trial guideline",
    "search_depth": "advanced",
    "max_results": 8,
    "include_raw_content": True,
    "include_answer": False,
    "exclude_domains": ["merckmanuals.com", "msdmanuals.com", "wikipedia.org", "healthline.com", "webmd.com", "mayoclinic.org"]
}

try:
    tavily_response = requests.post("https://api.tavily.com/search", json=tavily_payload, timeout=60).json()
except Exception as e:
    print("ERROR TAVILY:", e)
    tavily_response = {"results": []}

def source_text(r, max_chars=6000):
    return (r.get("raw_content") or r.get("content", ""))[:max_chars]

tavily_text = "\n\n".join(
    [
        "\n".join([
            "--- FUENTE WEB ---",
            f"Título: {r.get('title', '')}",
            f"URL: {r.get('url', '')}",
            f"Score: {r.get('score', '')}",
            "",
            "Texto:",
            source_text(r)
        ])
        for r in tavily_response.get("results", [])
    ]
) or "No se recuperaron fuentes web complementarias."

prompt = "\n".join([
    "Eres un médico de urgencias experto, editor científico y analista crítico de evidencia.",
    "",
    f"Tema de actualización: {tema}",
    "",
    "PAPERS RECUPERADOS DE PUBMED:",
    pubmed_text,
    "",
    "CONTEXTO WEB COMPLEMENTARIO:",
    tavily_text,
    "",
    "INSTRUCCIONES IMPORTANTES:",
    "- PubMed es el eje principal.",
    "- Tavily es solo contexto complementario.",
    "- No uses manuales generales como fuente principal.",
    "- No inventes PMID, DOI, autores ni revistas.",
    "- Diferencia evidencia fuerte, moderada, débil y especulativa.",
    "- Extensión orientativa: 1500 a 2200 palabras.",
    "- Escribe para médicos de urgencias y residentes.",
    "- Incluye implicaciones para triaje, diagnóstico, tratamiento, seguridad y derivación.",
    "",
    "ESTRUCTURA:",
    "1. Resumen ejecutivo",
    "2. Qué hay de nuevo o relevante",
    "3. Evidencia científica principal",
    "4. Evidencia por nivel",
    "5. Implicaciones para medicina de urgencias",
    "6. Qué cambia en la práctica",
    "7. Qué NO sabemos todavía",
    "8. Riesgos de interpretación excesiva",
    "9. Bibliografía comentada"
])

gemini_models = ["gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-3.5-flash"]

def gemini_call():
    last_error = None
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 8192}
    }

    for model in gemini_models:
        for attempt in range(3):
            print(f"Intentando modelo: {model} | intento {attempt + 1}/3")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            try:
                res = requests.post(url, json=payload, timeout=120).json()
                if "candidates" in res:
                    print(f"Modelo usado: {model}")
                    return res["candidates"][0]["content"]["parts"][0]["text"], model
                print(res)
                last_error = res
            except Exception as e:
                print(e)
                last_error = str(e)
            time.sleep(10)

    fallback = "\n".join([
        "## Informe no generado automáticamente",
        "",
        "No se pudo generar el informe porque todos los modelos disponibles devolvieron error o estaban saturados.",
        "",
        f"### Tema: {tema}",
        "",
        "### Datos sí recuperados",
        f"- PubMed: {len(pubmed_results)} resultados recuperados.",
        f"- Tavily: {len(tavily_response.get('results', []))} resultados recuperados.",
        "",
        "### Último error registrado",
        str(last_error),
        "",
        "Reintentar el workflow más tarde. Los archivos debug sí se han guardado."
    ])
    return fallback, "fallback-local"

output, model_used = gemini_call()
if model_used != "fallback-local":
    output = f"_Modelo usado: **{model_used}**_\n\n" + output

with open(f"debug-pubmed-{today}.json", "w", encoding="utf-8") as f:
    json.dump(pubmed_results, f, indent=2, ensure_ascii=False)

with open(f"debug-tavily-{today}.json", "w", encoding="utf-8") as f:
    json.dump(tavily_response, f, indent=2, ensure_ascii=False)

with open(f"debug-prompt-{today}.txt", "w", encoding="utf-8") as f:
    f.write(prompt)

with open(filename, "w", encoding="utf-8") as f:
    f.write("# Informe clínico v0.2\n\n")
    f.write(f"**Fecha:** {today}\n\n")
    f.write(f"**Tema:** {tema}\n\n")
    f.write("---\n\n")
    f.write(output)

print(f"Generado {filename}")
