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
from app.monitoring import init_sentry, get_metrics, api_request_duration
from app.routes.whatsapp_routes import whatsapp_router
from app.routes.admin_routes import admin_router
from app.routes.test_routes import test_router
from app.routes.pdf_routes import pdf_router

# Configurar logging mejorado
setup_logging()
logger = logging.getLogger(__name__)

# Inicializar Sentry
init_sentry()

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

        # Registrar métrica de duración
        if settings.ENABLE_METRICS:
            api_request_duration.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).observe(process_time)

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
        
        # Registrar métrica de error
        if settings.ENABLE_METRICS:
            api_request_duration.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).observe(process_time)
        
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

@app.get("/health/detailed", tags=["system"])
async def detailed_health_check():
    """Health check detallado con verificación de componentes"""
    from app.services.google_sheets import get_google_sheets_service
    
    checks = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Check Twilio
    checks["checks"]["twilio"] = {
        "status": "ok" if settings.TWILIO_ACCOUNT_SID else "not_configured",
        "configured": bool(settings.TWILIO_ACCOUNT_SID)
    }
    
    # Check Google Sheets
    try:
        gs_service = get_google_sheets_service()
        has_data = gs_service.prices_data is not None and len(gs_service.prices_data) > 0
        checks["checks"]["google_sheets"] = {
            "status": "ok" if has_data else "no_data",
            "configured": bool(settings.GOOGLE_SHEETS_ID),
            "data_loaded": has_data
        }
    except Exception as e:
        checks["checks"]["google_sheets"] = {
            "status": "error",
            "error": str(e)
        }
        checks["status"] = "degraded"
    
    # Check OpenAI
    checks["checks"]["openai"] = {
        "status": "ok" if settings.OPENAI_API_KEY else "not_configured",
        "configured": bool(settings.OPENAI_API_KEY)
    }
    
    # Check Sentry
    checks["checks"]["sentry"] = {
        "status": "ok" if settings.SENTRY_DSN else "not_configured",
        "configured": bool(settings.SENTRY_DSN)
    }
    
    return checks


@app.get("/metrics", tags=["system"])
async def metrics_endpoint():
    """Endpoint de métricas Prometheus"""
    if not settings.ENABLE_METRICS:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(get_metrics(), media_type="text/plain")

if __name__ == "__main__":
    # Configuración para desarrollo local
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
