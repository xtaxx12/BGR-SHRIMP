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
from app.models import (
    HealthStatus,
    DetailedHealthStatus,
    RootResponse
)

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
    title="BGR Export WhatsApp Bot API",
    description="""
    ## 🦐 Sistema de Cotización de Camarón vía WhatsApp
    
    API REST para gestionar cotizaciones de productos de camarón premium de BGR Export.
    
    ### Características principales:
    
    * **WhatsApp Integration**: Recibe y procesa mensajes de WhatsApp vía Twilio
    * **Pricing Engine**: Cálculo dinámico de precios FOB y CFR con glaseo
    * **PDF Generation**: Generación automática de proformas en español e inglés
    * **AI-Powered**: Análisis inteligente de mensajes con OpenAI GPT
    * **Session Management**: Gestión de sesiones de usuario con contexto
    * **Multi-Product**: Soporte para cotizaciones consolidadas
    
    ### Productos disponibles:
    
    * HLSO (Head Less Shell On) - Sin cabeza, con cáscara
    * HOSO (Head On Shell On) - Camarón entero con cabeza
    * P&D IQF - Pelado y desvenado individual
    * P&D BLOQUE - Pelado y desvenado en bloque
    * COOKED - Cocido listo para consumo
    * EZ PEEL - Fácil pelado
    * PuD-EUROPA - Calidad premium para Europa
    * PuD-EEUU - Calidad para Estados Unidos
    
    ### Tallas disponibles:
    
    U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40, 40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90
    
    ### Autenticación:
    
    * Endpoints de administración requieren token Bearer
    * Webhooks de WhatsApp validados con firma Twilio
    
    ### Rate Limiting:
    
    * WhatsApp webhook: 10 requests/minuto por número
    * Admin endpoints: Sin límite (requiere autenticación)
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
    contact={
        "name": "BGR Export",
        "url": "https://bgrexport.com",
        "email": "info@bgrexport.com"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://bgrexport.com/license"
    },
    openapi_tags=[
        {
            "name": "whatsapp",
            "description": "Endpoints para integración con WhatsApp vía Twilio. Recibe mensajes, procesa audio y genera cotizaciones."
        },
        {
            "name": "admin",
            "description": "Endpoints administrativos para gestión del sistema. Requieren autenticación con token Bearer."
        },
        {
            "name": "pdf",
            "description": "Endpoints para descarga de PDFs generados. Acceso público a documentos de cotización."
        },
        {
            "name": "test",
            "description": "Endpoints de prueba para desarrollo y testing. Solo disponibles en modo DEBUG."
        },
        {
            "name": "system",
            "description": "Endpoints de sistema para health checks, métricas y estado general de la aplicación."
        }
    ]
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

# 🆕 Rutas de entrenamiento
from app.routes.training_routes import training_router
app.include_router(training_router, prefix="/webhook", tags=["training"])

# Endpoints de sistema
@app.get(
    "/",
    tags=["system"],
    summary="Root endpoint",
    description="Información básica de la API",
    response_description="Información del servicio",
    response_model=RootResponse
)
async def root():
    """
    ## Root Endpoint
    
    Retorna información básica sobre el servicio.
    
    ### Respuesta:
    
    ```json
    {
        "message": "BGR Export WhatsApp Bot",
        "version": "2.0.0",
        "description": "Sistema de consulta de precios de camarón vía WhatsApp"
    }
    ```
    """
    return {
        "message": "BGR Export WhatsApp Bot",
        "version": "2.0.0",
        "description": "Sistema de consulta de precios de camarón vía WhatsApp",
        "docs": "/docs" if settings.DEBUG else "Disabled in production",
        "health": "/health"
    }

@app.get(
    "/health",
    tags=["system"],
    summary="Health check básico",
    description="Verifica el estado general del servicio y sus componentes",
    response_description="Estado de salud del servicio",
    response_model=HealthStatus
)
async def health_check():
    """
    ## Health Check Básico
    
    Verifica el estado general del servicio y la configuración de componentes críticos.
    
    ### Componentes verificados:
    
    * **Twilio**: Configuración de integración con WhatsApp
    * **Google Sheets**: Configuración de fuente de datos de precios
    * **OpenAI**: Configuración de análisis inteligente de mensajes
    
    ### Estados posibles:
    
    * `healthy`: Todos los componentes configurados correctamente
    * `degraded`: Algunos componentes no configurados pero el servicio funciona
    
    ### Ejemplo de respuesta:
    
    ```json
    {
        "status": "healthy",
        "service": "bgr-whatsapp-bot",
        "version": "2.0.0",
        "environment": "production",
        "components": {
            "twilio_configured": true,
            "google_sheets_configured": true,
            "openai_configured": true
        }
    }
    ```
    """
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

@app.get(
    "/health/detailed",
    tags=["system"],
    summary="Health check detallado",
    description="Verifica el estado detallado de todos los componentes del sistema",
    response_description="Estado detallado de cada componente",
    response_model=DetailedHealthStatus
)
async def detailed_health_check():
    """
    ## Health Check Detallado
    
    Realiza verificaciones profundas de todos los componentes del sistema.
    
    ### Verificaciones incluidas:
    
    * **Twilio**: Configuración y conectividad
    * **Google Sheets**: Configuración, conectividad y datos cargados
    * **OpenAI**: Configuración de API key
    * **Sentry**: Configuración de monitoreo de errores
    
    ### Estados por componente:
    
    * `ok`: Componente funcionando correctamente
    * `not_configured`: Componente no configurado
    * `no_data`: Componente configurado pero sin datos
    * `error`: Error en el componente
    
    ### Ejemplo de respuesta:
    
    ```json
    {
        "status": "healthy",
        "timestamp": 1700000000.0,
        "checks": {
            "twilio": {
                "status": "ok",
                "configured": true
            },
            "google_sheets": {
                "status": "ok",
                "configured": true,
                "data_loaded": true
            },
            "openai": {
                "status": "ok",
                "configured": true
            },
            "sentry": {
                "status": "ok",
                "configured": true
            }
        }
    }
    ```
    """
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


@app.get(
    "/metrics",
    tags=["system"],
    summary="Métricas Prometheus",
    description="Expone métricas del sistema en formato Prometheus",
    response_description="Métricas en formato texto plano compatible con Prometheus"
)
async def metrics_endpoint():
    """
    ## Métricas Prometheus
    
    Expone métricas del sistema en formato compatible con Prometheus.
    
    ### Métricas disponibles:
    
    * **api_request_duration_seconds**: Duración de requests HTTP
    * **api_request_total**: Total de requests por endpoint
    * **api_request_errors_total**: Total de errores por endpoint
    
    ### Configuración:
    
    Solo disponible si `ENABLE_METRICS=true` en variables de entorno.
    
    ### Ejemplo de uso con Prometheus:
    
    ```yaml
    scrape_configs:
      - job_name: 'bgr-whatsapp-bot'
        static_configs:
          - targets: ['api.bgrexport.com:80']
        metrics_path: '/metrics'
    ```
    
    ### Ejemplo de respuesta:
    
    ```
    # HELP api_request_duration_seconds Request duration in seconds
    # TYPE api_request_duration_seconds histogram
    api_request_duration_seconds_bucket{endpoint="/webhook/whatsapp",method="POST",status="200",le="0.1"} 45.0
    api_request_duration_seconds_bucket{endpoint="/webhook/whatsapp",method="POST",status="200",le="0.5"} 98.0
    api_request_duration_seconds_count{endpoint="/webhook/whatsapp",method="POST",status="200"} 100.0
    api_request_duration_seconds_sum{endpoint="/webhook/whatsapp",method="POST",status="200"} 12.5
    ```
    """
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
