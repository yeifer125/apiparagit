# API PIMA – Scraper de Precios Agrícolas yeifer

Esta API en **Python + Flask** realiza scraping del boletín de precios agrícolas de [PIMA](https://www.pima.go.cr/boletin/), procesa PDFs con `pdfplumber` y expone los datos en formato JSON.  

Está preparada para ejecutarse **localmente o mediante Docker**, y registra las IP de los clientes que acceden a la API.

---

## 📦 Características

- Scraper automático usando **Playwright + Chromium**.
- Detecta productos simples y compuestos (`camote`, `camote zanahoria`).
- Almacena los datos en `datos_cache.json` para consultas rápidas.
- API REST con endpoints:
  - `/` – Verifica que la API está funcionando.
  - `/precios` – Devuelve los precios actuales en JSON.
  - `/actualizar` – Fuerza una actualización manual del scraper.
- Actualización periódica cada 30 minutos.
- Registra la **IP real del cliente** usando `X-Forwarded-For`.
- Contenedor Docker listo para entornos sin GUI (`--no-sandbox`).

---

## 🔧 Instalación y Ejecución Local

1. Clonar el repositorio:

```bash
git clone https://github.com/tu_usuario/pima-api.git
cd pima-api


Crear un entorno virtual e instalar dependencias:

python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

pip install --upgrade pip
pip install -r requirements.txt


Instalar Chromium para Playwright:

playwright install chromium


Ejecutar la API:

python main.py


La API se ejecutará en http://127.0.0.1:5000 (o en el puerto definido por PORT).

🐳 Uso con Docker

Construir la imagen:

docker build -t pima-api .


Ejecutar el contenedor:

docker run -d -p 5000:5000 --name pima-api pima-api


La API estará disponible en http://localhost:5000.

📄 Ejemplo de respuesta /precios
[
  {
    "producto": "Camote",
    "unidad": "Mata",
    "mayorista": "Mata",
    "minimo": "1000.0",
    "maximo": "1500.0",
    "moda": "1200.0",
    "promedio": "1230.0",
    "fecha": "22/08/2025"
  },
  {
    "producto": "Camote Zanahoria",
    "unidad": "Mata",
    "mayorista": "Mata",
    "minimo": "1100.0",
    "maximo": "1600.0",
    "moda": "1300.0",
    "promedio": "1350.0",
    "fecha": "22/08/2025"
  }
]

📂 Estructura del proyecto
/app
├─ Dockerfile
├─ main.py
├─ requirements.txt
├─ pdfs/               # PDFs descargados
└─ datos_cache.json    # Datos procesados

🔗 Recursos

Playwright Python

pdfplumber

Flask

📝 Licencia

Uso personal / interno. Modificar según necesidades.
