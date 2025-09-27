import asyncio
import os
import json
import threading
import time
import subprocess
from datetime import datetime
from collections import OrderedDict
from flask import Flask, Response, request
from playwright.async_api import async_playwright
import pdfplumber
import shutil
import gc  # 🧠 Garbage collector manual

PDF_FOLDER = os.path.join(os.path.dirname(__file__), "pdfs")
CACHE_FILE = os.path.join(os.path.dirname(__file__), "datos_cache.json")

REPO_URL = os.environ.get("REPO_URL")
REPO_PATH = os.path.join(os.path.dirname(__file__), "iadatos")
BRANCH_NAME = "main"

ultima_ejecucion_scraper = None
ultima_actualizacion_git = None

def actualizar_historial_git(datos):
    global ultima_actualizacion_git
    if not REPO_URL:
        print("[WARN] REPO_URL no configurado, no se guardará historial.")
        return
    if os.path.exists(REPO_PATH) and not os.path.exists(os.path.join(REPO_PATH, ".git")):
        shutil.rmtree(REPO_PATH)

    if not os.path.exists(os.path.join(REPO_PATH, ".git")):
        subprocess.run(["git", "clone", REPO_URL, REPO_PATH], check=True)
    os.chdir(REPO_PATH)

    res = subprocess.run(["git", "branch", "--list", BRANCH_NAME], capture_output=True, text=True)
    subprocess.run(["git", "checkout", BRANCH_NAME if BRANCH_NAME in res.stdout else "-b", BRANCH_NAME], check=True)

    subprocess.run(["git", "config", "user.email", "render@example.com"], check=True)
    subprocess.run(["git", "config", "user.name", "RenderBot"], check=True)

    historial_file = os.path.join(REPO_PATH, "historial.json")
    historial = json.load(open(historial_file, "r", encoding="utf-8")) if os.path.exists(historial_file) else []

    nuevos = [d for d in datos if d not in historial]
    if not nuevos:
        print("✅ No hay productos nuevos para agregar al historial.")
        return

    historial.extend(nuevos)
    with open(historial_file, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

    subprocess.run(["git", "add", "."], check=True)
    if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
        subprocess.run(["git", "commit", "-m", f"Añadidos {len(nuevos)} productos"], check=True)
        try:
            subprocess.run(["git", "pull", "--rebase", "origin", BRANCH_NAME], check=True)
        except subprocess.CalledProcessError:
            print("[WARN] Pull fallido, posiblemente es el primer push.")
        subprocess.run(["git", "push", "origin", BRANCH_NAME], check=True)
        ultima_actualizacion_git = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

async def auto_scroll(page):
    await page.evaluate("""async () => {
        await new Promise(resolve => {
            let totalHeight = 0;
            const distance = 100;
            const timer = setInterval(() => {
                const scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;
                if (totalHeight >= scrollHeight) {
                    clearInterval(timer);
                    resolve();
                }
            }, 100);
        });
    }""")

async def extraer_documentos(page_or_frame):
    return await page_or_frame.eval_on_selector_all(
        "a",
        """
        anchors => anchors
            .filter(a => a.innerText.includes('Documentos adjuntos'))
            .map(a => ({texto: a.innerText.trim(), href: a.href}))
        """
    )

async def descargar_archivo(context, url, nombre):
    os.makedirs(PDF_FOLDER, exist_ok=True)
    ruta_archivo = os.path.join(PDF_FOLDER, nombre)
    if os.path.exists(ruta_archivo):
        return ruta_archivo

    # 🧠 Reintentos con backoff
    for intento in range(3):
        try:
            response = await context.request.get(url, timeout=30000)
            if response.status == 200:
                contenido = await response.body()
                if contenido.startswith(b"%PDF"):
                    with open(ruta_archivo, "wb") as f:
                        f.write(contenido)
                    return ruta_archivo
            print(f"[WARN] Archivo no válido en intento {intento+1}: {url}")
        except Exception as e:
            print(f"[WARN] Error descargando {url} intento {intento+1}: {e}")
        await asyncio.sleep(2 * (intento + 1))
    return None

def extraer_todo_pdf(ruta_pdf):
    resultados = []
    fecha = ""
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            for linea in texto.split("\n"):
                if "fecha de plaza" in linea.lower():
                    fecha = linea.split(":")[-1].strip() or fecha
                cols = linea.split()
                if len(cols) < 5: continue
                try:
                    minimo, maximo, moda, promedio = map(lambda x: float(x.replace(",", "")), cols[-4:])
                    mayorista = cols[-5]
                    prod_nombre = " ".join(cols[:-5])
                except ValueError:
                    continue
                if prod_nombre.strip() and not prod_nombre.lower().startswith("producto"):
                    resultados.append(OrderedDict([
                        ("producto", prod_nombre),
                        ("unidad", mayorista),
                        ("mayorista", mayorista),
                        ("minimo", str(minimo)),
                        ("maximo", str(maximo)),
                        ("moda", str(moda)),
                        ("promedio", str(promedio)),
                        ("fecha", fecha or datetime.now().strftime("%d/%m/%Y"))
                    ]))
    return resultados

def parse_fecha(fecha_str):
    try:
        return datetime.strptime(fecha_str, "%d/%m/%Y")
    except:
        return datetime.min

async def main_scraping():
    global ultima_ejecucion_scraper
    rutas_pdfs = []
    async with async_playwright() as p:
        iphone = p.devices["iPhone 14"]
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(**iphone)
        page = await context.new_page()
        await page.goto("https://www.pima.go.cr/boletin/", wait_until="networkidle")
        await auto_scroll(page)

        documentos = await extraer_documentos(page)
        for frame in page.frames:
            documentos.extend(await extraer_documentos(frame))
        documentos = [dict(t) for t in {tuple(d.items()) for d in documentos}]

        for i, doc in enumerate(documentos, 1):
            nombre = f"{i}_{doc['texto'][:20].replace(' ', '_')}.pdf"
            ruta_pdf = await descargar_archivo(context, doc['href'], nombre)
            if ruta_pdf: rutas_pdfs.append(ruta_pdf)

        await browser.close()

    todos_resultados = []
    for pdf_path in rutas_pdfs:
        try:
            todos_resultados.extend(extraer_todo_pdf(pdf_path))
        except Exception as e:
            print(f"[ERROR] No se pudo procesar {pdf_path}: {e}")
        finally:
            # 🧠 Liberar memoria: eliminar PDF tras procesarlo
            os.remove(pdf_path)

    todos_resultados.sort(key=lambda x: parse_fecha(x["fecha"]), reverse=True)
    ultima_ejecucion_scraper = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(todos_resultados, f, ensure_ascii=False, indent=2)

    actualizar_historial_git(todos_resultados)
    gc.collect()  # 🧠 Forzar limpieza de memoria
    print(f"[{datetime.now()}] ✅ Scraper ejecutado. {len(todos_resultados)} productos guardados.")

def tarea_periodica():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            loop.run_until_complete(main_scraping())
        except Exception as e:
            print(f"[ERROR] Falló la actualización periódica: {e}")
        finally:
            gc.collect()
            time.sleep(30 * 60)

app = Flask(__name__)

@app.route("/precios", methods=["GET"])
def obtener_precios():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    print(f"[LOG] /precios desde IP: {ip}")
    if os.path.exists(CACHE_FILE):
        datos = json.load(open(CACHE_FILE, "r", encoding="utf-8"))
        info = {"ultima_ejecucion_scraper": ultima_ejecucion_scraper, "ultima_actualizacion_git": ultima_actualizacion_git}
        return Response(json.dumps([info] + datos, ensure_ascii=False, indent=2), mimetype="application/json")
    return Response(json.dumps({"error": "No existe el archivo de cache"}, ensure_ascii=False), mimetype="application/json"), 404

@app.route("/")
def index():
    return "API PIMA funcionando. Usa /precios para ver los datos."

@app.route("/actualizar", methods=["GET"])
def actualizar():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_scraping())
        return Response(json.dumps({"status": "ok", "mensaje": "Datos actualizados manualmente"}, ensure_ascii=False), mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"status": "error", "mensaje": str(e)}, ensure_ascii=False), mimetype="application/json"), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=lambda: asyncio.run(main_scraping()), daemon=True).start()
    threading.Thread(target=tarea_periodica, daemon=True).start()
    app.run(host="0.0.0.0", port=port)
