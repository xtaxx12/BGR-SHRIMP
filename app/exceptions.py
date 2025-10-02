from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

class BusinessException(Exception):
    """Excepción base para errores de negocio"""
    def __init__(self, message: str, code: str = "BUSINESS_ERROR", details: Dict[str, Any] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(BusinessException):
    """Error de validación de datos"""
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        if field:
            self.details["field"] = field

class PricingError(BusinessException):
    """Error en cálculo de precios"""
    def __init__(self, message: str, product: str = None, size: str = None):
        details = {}
        if product:
            details["product"] = product
        if size:
            details["size"] = size
        super().__init__(message, "PRICING_ERROR", details)

class ExternalServiceError(BusinessException):
    """Error en servicio externo (Twilio, OpenAI, etc)"""
    def __init__(self, service: str, message: str, original_error: Exception = None):
        details = {"service": service}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)

class RateLimitExceeded(BusinessException):
    """Error de límite de tasa excedido"""
    def __init__(self, identifier: str, limit: int, window: int):
        message = f"Too many requests. Limit: {limit} requests per {window} seconds"
        details = {
            "identifier": identifier,
            "limit": limit,
            "window_seconds": window
        }
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)

class SessionError(BusinessException):
    """Error relacionado con sesión de usuario"""
    def __init__(self, message: str, user_id: str = None):
        details = {}
        if user_id:
            details["user_id"] = user_id
        super().__init__(message, "SESSION_ERROR", details)

class PDFGenerationError(BusinessException):
    """Error al generar PDF"""
    def __init__(self, message: str, quote_id: str = None):
        details = {}
        if quote_id:
            details["quote_id"] = quote_id
        super().__init__(message, "PDF_GENERATION_ERROR", details)

class DataNotFoundError(BusinessException):
    """Error cuando no se encuentran datos solicitados"""
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        details = {"resource": resource}
        if identifier:
            details["identifier"] = identifier
            message += f": {identifier}"
        super().__init__(message, "NOT_FOUND", details)

class ConfigurationError(Exception):
    """Error de configuración del sistema"""
    def __init__(self, message: str, missing_vars: list = None):
        self.message = message
        self.missing_vars = missing_vars or []
        super().__init__(self.message)

# Manejadores de excepciones globales

async def business_exception_handler(request: Request, exc: BusinessException):
    """Manejador para excepciones de negocio"""
    logger.warning(
        f"Business exception: {exc.code}",
        extra={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    """Manejador específico para errores de validación"""
    logger.warning(
        f"Validation error: {exc.message}",
        extra={
            "field": exc.details.get("field"),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": exc.message,
                "field": exc.details.get("field"),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Manejador para excepciones no esperadas"""
    # Generar ID único para el error
    import uuid
    error_id = str(uuid.uuid4())
    
    # Log completo del error
    logger.error(
        f"Unhandled exception: {error_id}",
        extra={
            "error_id": error_id,
            "type": type(exc).__name__,
            "message": str(exc),
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )
    
    # Respuesta genérica al cliente (no revelar detalles internos)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred. Please try again later.",
                "error_id": error_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

# Decorador para manejo de errores en funciones

from functools import wraps
from typing import Callable

def handle_errors(default_message: str = "An error occurred"):
    """Decorador para manejo automático de errores"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BusinessException:
                # Re-lanzar excepciones de negocio para que sean manejadas globalmente
                raise
            except Exception as e:
                # Log del error
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    extra={
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    }
                )
                # Lanzar excepción genérica
                raise BusinessException(
                    message=default_message,
                    code="FUNCTION_ERROR",
                    details={"function": func.__name__}
                )
        
        return wrapper
    return decorator

# Utilidades para manejo de errores

def safe_parse_json(data: str) -> Optional[Dict[str, Any]]:
    """Parse JSON de forma segura"""
    try:
        import json
        return json.loads(data)
    except Exception as e:
        logger.debug(f"Failed to parse JSON: {e}")
        return None

def safe_get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Obtener atributo de forma segura"""
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default