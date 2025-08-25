import os
import json
import asyncio
import threading
import subprocess
from datetime import datetime
from flask import Flask, jsonify, request
from scraper import ejecutar_scraper  # tu función de scraping

app = Flask(__name__)

CACHE_FILE = "datos_cache.json"
REPO_URL = "https://github.com/yeifer125/iadatos.git"
REPO_PATH = "iadatos"


def cargar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar_cache(datos):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def actualizar_historial_git(nuevos_datos):
    try:
        if not os.path.exists(REPO_PATH):
            subprocess.run(["git", "clone", REPO_URL, REPO_PATH], check=True)

        # Copiar el cache al repositorio
        destino = os.path.join(REPO_PATH, "datos_cache.json")
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(nuevos_datos, f, ensure_ascii=False, indent=2)

        mensaje_commit = f"Añadidos {len(nuevos_datos)} productos al historial"

        # ✅ Configurar identidad de git antes de commitear
        subprocess.run(["git", "-C", REPO_PATH, "config", "user.email", "bot@render.com"], check=True)
        subprocess.run(["git", "-C", REPO_PATH, "config", "user.name", "Render Bot"], check=True)

        # Commit y push
        subprocess.run(["git", "-C", REPO_PATH, "add", "."], check=True)
        subprocess.run(["git", "-C", REPO_PATH, "commit", "-m", mensaje_commit], check=True)
        subprocess.run(["git", "-C", REPO_PATH, "push"], check=True)

        print(f"[{datetime.now()}] ✅ Historial actualizado y enviado a GitHub.")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Falló la operación de Git: {e}. Se continuará sin interrumpir el scraping.")


async def main_scraping():
    try:
        resultados = await ejecutar_scraper()
        if resultados:
            guardar_cache(resultados)
            actualizar_historial_git(resultados)
            print(f"[{datetime.now()}] ✅ Scraper ejecutado. {len(resultados)} productos guardados en '{CACHE_FILE}'.")
        else:
            print(f"[{datetime.now()}] ✅ No hay productos nuevos para agregar al historial.")
    except Exception as e:
        print(f"[ERROR] Falló la actualización periódica: {e}")


@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "API funcionando 🚀"})


@app.route("/precios")
def precios():
    datos = cargar_cache()
    return jsonify(datos)


def ejecutar_periodicamente():
    while True:
        asyncio.run(main_scraping())
        asyncio.sleep(3600)  # cada 1 hora


if __name__ == "__main__":
    threading.Thread(target=lambda: asyncio.run(main_scraping()), daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
