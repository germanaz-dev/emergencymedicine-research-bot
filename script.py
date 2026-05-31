import os
import time
import json
import requests
from datetime import datetime

from google import genai


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

today = datetime.now().strftime("%Y-%m-%d")
filename = f"report-{today}.md"


# --- 0. LEER TEMA ---
with open("tema.txt", "r", encoding="utf-8") as f:
    tema = f.read().strip()


# --- 1. BÚSQUEDA CON TAVILY ---
tavily_url = "https://api.tavily.com/search"

tavily_payload = {
    "api_key": TAVILY_API_KEY,
    "query": tema,
    "search_depth": "advanced",
    "max_results": 5
}

tavily_response = requests.post(tavily_url, json=tavily_payload).json()

results_text = "\n\n".join([
    f"{r.get('title', '')}\n{r.get('content', '')}\n{r.get('url', '')}"
    for r in tavily_response.get("results", [])
])


# --- 2. GEMINI TEXTO ---
gemini_url = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)

prompt = f"""
Eres un médico de urgencias experto.

Tema: {tema}

Información recopilada:
{results_text}

INSTRUCCIONES:
- Prioriza evidencia científica.
- Diferencia evidencia fuerte, débil y especulativa.
- Evita blogs si no aportan valor.
- Señala limitaciones.
- No inventes bibliografía.
- Incluye URLs cuando estén disponibles.

Genera un informe en español con:

1. Resumen ejecutivo
2. Novedades recientes
3. Nivel de evidencia
4. Implicaciones clínicas
5. Qué cambia en urgencias
6. Qué NO sabemos
7. Bibliografía / fuentes
"""

gemini_payload = {
    "contents": [{"parts": [{"text": prompt}]}]
}

gemini_response = requests.post(gemini_url, json=gemini_payload).json()

if "candidates" not in gemini_response:
    print("ERROR GEMINI TEXTO:")
    print(gemini_response)
    raise SystemExit(1)

output = gemini_response["candidates"][0]["content"]["parts"][0]["text"]


# --- 3. IMAGEN CON GEMINI IMAGE ---
def generate_cover_image():
    client = genai.Client(api_key=GEMINI_API_KEY)

    image_prompt = f"""
Create a beautiful editorial hero image for a medical web article.

Topic: {tema}

Style:
elegant medical magazine header,
cinematic, realistic,
warm but serious clinical atmosphere,
soft light,
horizontal wide banner,
no text, no letters, no logos, no gore.
"""

    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-image",
                contents=[image_prompt],
            )

            for part in response.parts:
                if part.inline_data is not None:
                    image = part.as_image()
                    cover_file = f"cover-{today}.png"
                    image.save(cover_file)
                    print("Imagen generada correctamente")
                    return cover_file

                if part.text is not None:
                    print("Texto devuelto por modelo de imagen:")
                    print(part.text)

        except Exception as e:
            print(f"ERROR IMAGEN intento {attempt + 1}/5:")
            print(type(e))
            print(e)
            time.sleep(20)

    return None


image_filename = generate_cover_image()


# --- 4. DEBUG ---
with open(f"debug-tavily-{today}.json", "w", encoding="utf-8") as f:
    json.dump(tavily_response, f, indent=2, ensure_ascii=False)

with open(f"debug-input-gemini-{today}.txt", "w", encoding="utf-8") as f:
    f.write(results_text)

with open(f"debug-prompt-gemini-{today}.txt", "w", encoding="utf-8") as f:
    f.write(prompt)


# --- 5. GUARDAR INFORME ---
with open(filename, "w", encoding="utf-8") as f:
    f.write("# Informe diario\n\n")

    if image_filename:
        f.write(f"![Imagen de portada]({image_filename})\n\n")
    else:
        f.write("_No se pudo generar imagen en este run._\n\n")

    f.write(f"**Tema:** {tema}\n\n")
    f.write(output)

print(f"Generado {filename}")
