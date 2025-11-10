import time
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Cargar variables de entorno ANTES de importar servicios
load_dotenv()

import logging

from app.config import settings
from app.exceptions import (
    BusinessException,
    ValidationError,
    business_exception_handler,
    general_exception_handler,
    validation_exception_handler,
)
from app.logging_config import setup_logging
from app.routes.whatsapp_routes import whatsapp_router
from app.routes.admin_routes import admin_router
from app.routes.test_routes import test_router
from app.routes.pdf_routes import pdf_router

# Configurar logging mejorado
setup_logging()
logger = logging.getLogger(__name__)

# Contexto de ciclo de vida de la aplicación
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting BGR Export WhatsApp Bot")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Validar configuración en producción
    if settings.is_production:
        try:
            settings.validate()
            logger.info("Configuration validated successfully")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            raise

    yield

    # Shutdown
    logger.info("Shutting down BGR Export WhatsApp Bot")

app = FastAPI(
    title="BGR Export WhatsApp Bot",
    description="Bot de WhatsApp para consulta de precios de camarón",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Desactivar docs en producción
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# Configurar middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de hosts confiables en producción
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Generar request ID
    import uuid
    request_id = str(uuid.uuid4())

    # Agregar request ID a los logs
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown"
        }
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log de respuesta exitosa
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": round(process_time, 3)
            }
        )

        # Agregar headers de seguridad y métricas
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "Request failed",
            extra={
                "request_id": request_id,
                "error": str(e),
                "process_time": round(process_time, 3)
            }
        )
        raise

# Registrar manejadores de excepciones
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Incluir rutas
app.include_router(whatsapp_router, prefix="/webhook", tags=["whatsapp"])
app.include_router(admin_router, prefix="/webhook", tags=["admin"])
app.include_router(test_router, prefix="/webhook", tags=["test"])
app.include_router(pdf_router, prefix="/webhook", tags=["pdf"])

# Endpoints de sistema
@app.get("/", tags=["system"])
async def root():
    return {
        "message": "BGR Export WhatsApp Bot",
        "version": "2.0.0",
        "description": "Sistema de consulta de precios de camarón vía WhatsApp"
    }

@app.get("/health", tags=["system"])
async def health_check():
    """Endpoint para verificar salud del servicio"""
    # Verificar componentes críticos
    health_status = {
        "status": "healthy",
        "service": "bgr-whatsapp-bot",
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
        "components": {
            "twilio_configured": bool(settings.TWILIO_ACCOUNT_SID),
            "google_sheets_configured": bool(settings.GOOGLE_SHEETS_ID),
            "openai_configured": bool(settings.OPENAI_API_KEY)
        }
    }

    # Verificar si hay problemas
    if not health_status["components"]["twilio_configured"]:
        health_status["status"] = "degraded"
        health_status["message"] = "Twilio not configured"

    return health_status

@app.get("/metrics", tags=["system"])
async def metrics():
    """Endpoint básico de métricas"""
    if not settings.DEBUG:
        raise HTTPException(status_code=404)

    # TODO: Implementar métricas reales con Prometheus o similar
    return {
        "uptime_seconds": time.time(),
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG
    }

if __name__ == "__main__":
    # Configuración para desarrollo local
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
