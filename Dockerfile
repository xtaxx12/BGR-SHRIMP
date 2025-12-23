# =============================================================================
# Dockerfile para BGR-SHRIMP - Build Multistage Optimizado
# =============================================================================
# Mejoras implementadas:
# - Multistage build para reducir tamaño de imagen final
# - Usuario no-root por seguridad (principio de menor privilegio)
# - HEALTHCHECK para monitoreo de contenedor
# - Caching optimizado de capas de Docker
# =============================================================================

# -----------------------------------------------------------------------------
# STAGE 1: Builder - Compilación de dependencias
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Instalar dependencias de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio para wheels
WORKDIR /wheels

# Copiar solo requirements para aprovechar cache de Docker
COPY requirements.txt .

# Compilar dependencias como wheels
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# -----------------------------------------------------------------------------
# STAGE 2: Runtime - Imagen final optimizada
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Metadatos de la imagen
LABEL maintainer="BGR Export <rojassebas765@gmail.com>"
LABEL version="2.0.0"
LABEL description="WhatsApp Bot for BGR Export shrimp price quotations"

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Puerto de la aplicación
    PORT=8000 \
    # Directorio de la app
    APP_HOME=/app

# Instalar curl para healthcheck y limpiar cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Crear usuario no-root para seguridad (principio de menor privilegio)
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Establecer directorio de trabajo
WORKDIR ${APP_HOME}

# Copiar wheels compilados desde builder
COPY --from=builder /wheels /wheels

# Instalar dependencias desde wheels (más rápido, sin compilación)
RUN pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

# Copiar código de la aplicación
COPY --chown=appuser:appgroup . .

# Crear directorios necesarios con permisos correctos
RUN mkdir -p data logs generated_pdfs \
    && chown -R appuser:appgroup ${APP_HOME}

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE ${PORT}

# -----------------------------------------------------------------------------
# HEALTHCHECK - Verificar que la aplicación responde
# -----------------------------------------------------------------------------
# Intervalo: cada 30 segundos
# Timeout: máximo 10 segundos para responder
# Start-period: 40 segundos de gracia al iniciar
# Retries: 3 intentos antes de marcar como unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# -----------------------------------------------------------------------------
# Comando de ejecución
# -----------------------------------------------------------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
