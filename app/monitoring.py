"""
Módulo de monitoreo con Sentry y Prometheus
"""
import logging
import time
from functools import wraps
from typing import Callable

import sentry_sdk
from prometheus_client import Counter, Histogram, generate_latest
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# SENTRY CONFIGURATION
# ============================================================================

def init_sentry():
    """Inicializa Sentry para error tracking y performance monitoring"""
    if not settings.SENTRY_DSN:
        logger.warning("⚠️ Sentry DSN no configurado - Monitoreo de errores deshabilitado")
        return
    
    try:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Captura logs de nivel INFO y superior
            event_level=logging.ERROR  # Envía eventos a Sentry para ERROR y superior
        )
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                sentry_logging,
            ],
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            
            # Configuración adicional
            send_default_pii=False,  # No enviar información personal por defecto
            attach_stacktrace=True,
            max_breadcrumbs=50,
            
            # Filtrar eventos sensibles
            before_send=filter_sensitive_data,
        )
        
        logger.info(f"✅ Sentry inicializado - Environment: {settings.ENVIRONMENT}")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando Sentry: {e}")


def filter_sensitive_data(event, hint):
    """Filtra datos sensibles antes de enviar a Sentry"""
    # Filtrar tokens y credenciales de los datos
    if 'request' in event:
        if 'headers' in event['request']:
            # Ocultar headers sensibles
            sensitive_headers = ['authorization', 'x-api-key', 'cookie']
            for header in sensitive_headers:
                if header in event['request']['headers']:
                    event['request']['headers'][header] = '[FILTERED]'
        
        if 'data' in event['request']:
            # Ocultar campos sensibles en el body
            sensitive_fields = ['password', 'token', 'api_key', 'secret']
            for field in sensitive_fields:
                if field in event['request']['data']:
                    event['request']['data'][field] = '[FILTERED]'
    
    return event


# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Métricas de negocio
quotations_generated = Counter(
    'bgr_quotations_generated_total',
    'Total de cotizaciones generadas',
    ['product', 'status']
)

quotations_by_type = Counter(
    'bgr_quotations_by_type_total',
    'Cotizaciones por tipo (FOB/CFR)',
    ['type', 'product']
)

pdf_generated = Counter(
    'bgr_pdf_generated_total',
    'Total de PDFs generados',
    ['type', 'status']
)

whatsapp_messages = Counter(
    'bgr_whatsapp_messages_total',
    'Total de mensajes de WhatsApp procesados',
    ['direction', 'status']
)

# Métricas de performance
quotation_generation_time = Histogram(
    'bgr_quotation_generation_seconds',
    'Tiempo de generación de cotización',
    ['product']
)

pdf_generation_time = Histogram(
    'bgr_pdf_generation_seconds',
    'Tiempo de generación de PDF',
    ['type']
)

api_request_duration = Histogram(
    'bgr_api_request_duration_seconds',
    'Duración de requests HTTP',
    ['method', 'endpoint', 'status']
)

# Métricas de errores
errors_total = Counter(
    'bgr_errors_total',
    'Total de errores',
    ['type', 'severity']
)

validation_errors = Counter(
    'bgr_validation_errors_total',
    'Errores de validación',
    ['field', 'error_type']
)

# Métricas de sistema
active_sessions = Counter(
    'bgr_active_sessions_total',
    'Sesiones activas de usuarios'
)


# ============================================================================
# DECORADORES PARA MÉTRICAS
# ============================================================================

def track_quotation_time(product: str = "unknown"):
    """Decorator para medir tiempo de generación de cotización"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                quotation_generation_time.labels(product=product).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                quotation_generation_time.labels(product=product).observe(duration)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                quotation_generation_time.labels(product=product).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                quotation_generation_time.labels(product=product).observe(duration)
                raise
        
        # Detectar si la función es async o sync
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def track_pdf_generation(pdf_type: str = "single"):
    """Decorator para medir tiempo de generación de PDF"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                pdf_generation_time.labels(type=pdf_type).observe(duration)
                pdf_generated.labels(type=pdf_type, status='success').inc()
                return result
            except Exception as e:
                duration = time.time() - start_time
                pdf_generation_time.labels(type=pdf_type).observe(duration)
                pdf_generated.labels(type=pdf_type, status='error').inc()
                raise
        return wrapper
    return decorator


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def record_quotation(product: str, status: str = 'success', quotation_type: str = 'FOB'):
    """Registra una cotización generada"""
    if settings.ENABLE_METRICS:
        quotations_generated.labels(product=product, status=status).inc()
        quotations_by_type.labels(type=quotation_type, product=product).inc()


def record_whatsapp_message(direction: str = 'inbound', status: str = 'success'):
    """Registra un mensaje de WhatsApp procesado"""
    if settings.ENABLE_METRICS:
        whatsapp_messages.labels(direction=direction, status=status).inc()


def record_error(error_type: str, severity: str = 'error'):
    """Registra un error"""
    if settings.ENABLE_METRICS:
        errors_total.labels(type=error_type, severity=severity).inc()


def record_validation_error(field: str, error_type: str):
    """Registra un error de validación"""
    if settings.ENABLE_METRICS:
        validation_errors.labels(field=field, error_type=error_type).inc()


def get_metrics():
    """Retorna las métricas en formato Prometheus"""
    return generate_latest()


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================

class track_time:
    """Context manager para medir tiempo de ejecución"""
    def __init__(self, metric: Histogram, **labels):
        self.metric = metric
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.metric.labels(**self.labels).observe(duration)
        return False  # No suprimir excepciones
