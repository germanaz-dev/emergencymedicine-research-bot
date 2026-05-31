import os
import requests
from datetime import datetime

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Leer tema de la semana
with open("tema.txt", "r") as f:
    tema = f.read().strip()

# --- 1. BUSQUEDA CON TAVILY ---
tavily_url = "https://api.tavily.com/search"

tavily_payload = {
    "api_key": TAVILY_API_KEY,
    "query": tema,
    "search_depth": "advanced",
    "max_results": 5
}

tavily_response = requests.post(tavily_url, json=tavily_payload).json()

results_text = "\n\n".join([
    f"{r['title']}\n{r['content']}\n{r['url']}"
    for r in tavily_response.get("results", [])
])

# --- 2. ANALISIS CON GEMINI ---
gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

prompt = f"""
Eres un médico de urgencias experto.

Tema: {tema}

Información recopilada:
{results_text}

Genera un informe en español con:

1. Resumen ejecutivo
2. Novedades recientes
3. Nivel de evidencia
4. Implicaciones clínicas
5. Ideas aplicables en urgencias
6. Bibliografía (urls)
"""

gemini_payload = {
    "contents": [
        {
            "parts": [{"text": prompt}]
        }
    ]
}

gemini_response = requests.post(gemini_url, json=gemini_payload).json()

gemini_response = requests.post(gemini_url, json=gemini_payload).json()

if "candidates" not in gemini_response:
    print("ERROR DE GEMINI:")
    print(gemini_response)
    raise SystemExit(1)

output = gemini_response["candidates"][0]["content"]["parts"][0]["text"]

# --- 3. GUARDAR INFORME ---
today = datetime.now().strftime("%Y-%m-%d")
filename = f"report-{today}.md"

with open(filename, "w") as f:
    f.write(f"# Informe diario\n\n")
    f.write(f"**Tema:** {tema}\n\n")
    f.write(output)

print(f"Generado {filename}")
