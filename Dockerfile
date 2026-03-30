# ===========================================
# Panel de Personas CGR - Docker Image
# Optimizado para Azure Container Apps
# ===========================================
FROM python:3.11-slim

# Metadatos
LABEL maintainer="CDIA CGR <cdia@contraloria.cl>"
LABEL version="2.0"
LABEL description="Panel de Personas - Sistema Integrado de Información"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8081

WORKDIR /app

# Instalar dependencias del sistema en una sola capa
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Actualizar pip
RUN pip install --upgrade pip setuptools wheel

# Copiar solo pyproject.toml primero (para cache de dependencias)
COPY pyproject.toml ./

# Instalar dependencias del proyecto
RUN pip install . \
    && rm -rf ~/.cache/pip

# Copiar el código de la aplicación
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY main.py ./

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8081/ || exit 1

# Comando de inicio
CMD ["python", "main.py", "api", "--host", "0.0.0.0", "--port", "8081"]
