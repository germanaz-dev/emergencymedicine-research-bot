import os
import time
import requests
from datetime import datetime
from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

today = datetime.now().strftime("%Y-%m-%d")
filename = f"report-{today}.md"
image_filename = None


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


# --- 2. ANÁLISIS CON GEMINI ---
gemini_url = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)

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

if "candidates" not in gemini_response:
    print("ERROR DE GEMINI:")
    print(gemini_response)
    raise SystemExit(1)

output = gemini_response["candidates"][0]["content"]["parts"][0]["text"]


# --- 3. GENERAR IMAGEN CON IMAGEN 4 FAST ---
def generate_cover_image():
    client = genai.Client(api_key=GEMINI_API_KEY)

    cover_prompt = f"""
Beautiful editorial hero image for a medical web article about:
{tema}

Style:
elegant, cinematic, realistic, warm clinical atmosphere,
professional medical magazine cover,
horizontal wide banner,
soft light, high quality,
no text, no letters, no logos, no gore.
"""

    for attempt in range(3):
        try:
            response = client.models.generate_images(
                model="imagen-4.0-fast-generate-001",
                prompt=cover_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                )
            )

            image = Image.open(
                BytesIO(response.generated_images[0].image.image_bytes)
            )

            cover_file = f"cover-{today}.png"
            image.save(cover_file)

            with open(f"cover-prompt-{today}.txt", "w", encoding="utf-8") as f:
                f.write(cover_prompt)

            return cover_file

        except Exception as e:
            print(f"Error generando imagen, intento {attempt + 1}: {e}")
            time.sleep(5)

    return None


image_filename = generate_cover_image()


# --- 4. GUARDAR DEBUG OPCIONAL ---
with open(f"debug-tavily-{today}.json", "w", encoding="utf-8") as f:
    import json
    json.dump(tavily_response, f, indent=2, ensure_ascii=False)

with open(f"debug-input-gemini-{today}.txt", "w", encoding="utf-8") as f:
    f.write(results_text)

with open(f"debug-prompt-{today}.txt", "w", encoding="utf-8") as f:
    f.write(prompt)


# --- 5. GUARDAR INFORME ---
with open(filename, "w", encoding="utf-8") as f:
    f.write("# Informe diario\n\n")

    if image_filename:
        f.write(f"![Imagen de portada]({image_filename})\n\n")
    else:
        f.write("_No se pudo generar imagen de portada en este run._\n\n")

    f.write(f"**Tema:** {tema}\n\n")
    f.write(output)

print(f"Generado {filename}")
