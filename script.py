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

# generar imagen bonita con modelo g para portada
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

response = client.models.generate_images(
    model="imagen-4.0-fast-generate-001",
    prompt=cover_prompt,
    config=types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="16:9",
    )
)

image = Image.open(BytesIO(response.generated_images[0].image.image_bytes))

today = datetime.now().strftime("%Y-%m-%d")
image_filename = f"cover-{today}.png"
image.save(image_filename)
