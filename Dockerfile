# Imagen base de Python
FROM python:3.10-slim

# Evita que Python guarde .pyc y buffer
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instalar dependencias del sistema (incluye git y playwright deps)
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    unzip \
    xvfb \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    libxdamage1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero (mejora cache)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores de Playwright
RUN playwright install --with-deps chromium

# Copiar el resto del código
COPY . .

# Exponer puerto para Render
EXPOSE 10000

# Comando por defecto
CMD ["python", "main.py"]
