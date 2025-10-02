import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
import json
from typing import Any, Dict
from app.config import settings

class StructuredFormatter(logging.Formatter):
    """Custom formatter que genera logs estructurados en JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Agregar información extra si existe
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
            
        # Agregar información de excepción si existe
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        # Agregar campos extra
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
                
        return json.dumps(log_data)

class SensitiveDataFilter(logging.Filter):
    """Filtro para remover información sensible de los logs"""
    
    SENSITIVE_PATTERNS = [
        'password', 'token', 'api_key', 'auth_token', 'secret',
        'credit_card', 'ssn', 'account_sid', 'TWILIO_AUTH_TOKEN'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Filtrar mensaje principal
        message = record.getMessage()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.lower() in message.lower():
                # Reemplazar valores sensibles con asteriscos
                record.msg = self._mask_sensitive_data(record.msg, pattern)
                
        return True
    
    def _mask_sensitive_data(self, text: str, pattern: str) -> str:
        import re
        # Buscar patrones como "token=valor" o "token: valor"
        regex = rf"{pattern}[=:\s]+['\"]*([^'\"\s,}}]+)"
        return re.sub(regex, f"{pattern}=***REDACTED***", text, flags=re.IGNORECASE)

def setup_logging():
    """Configurar sistema de logging para la aplicación"""
    
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Nivel de log basado en entorno
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Limpiar handlers existentes
    root_logger.handlers = []
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if settings.is_production:
        # En producción usar formato JSON estructurado
        console_handler.setFormatter(StructuredFormatter())
    else:
        # En desarrollo usar formato legible
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
    
    # Agregar filtro de datos sensibles
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)
    
    root_logger.addHandler(console_handler)
    
    # Handler para archivo (rotación diaria)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "app.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(StructuredFormatter())
    file_handler.addFilter(sensitive_filter)
    
    root_logger.addHandler(file_handler)
    
    # Handler para errores (archivo separado)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    error_handler.addFilter(sensitive_filter)
    
    root_logger.addHandler(error_handler)
    
    # Configurar loggers específicos
    
    # Reducir verbosidad de bibliotecas externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("twilio").setLevel(logging.WARNING)
    
    # Logger para auditoría de seguridad
    security_logger = logging.getLogger("security")
    security_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "security.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    security_handler.setFormatter(StructuredFormatter())
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)
    
    # Logger para métricas de negocio
    business_logger = logging.getLogger("business")
    business_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "business.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=30,
        encoding="utf-8"
    )
    business_handler.setFormatter(StructuredFormatter())
    business_logger.addHandler(business_handler)
    business_logger.setLevel(logging.INFO)

class LoggerAdapter(logging.LoggerAdapter):
    """Adapter para agregar contexto a los logs"""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        # Agregar contexto extra a todos los logs
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
            
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs

def get_logger(name: str, **context) -> LoggerAdapter:
    """Obtener logger con contexto adicional"""
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context)

# Funciones de utilidad para logging

def log_api_request(logger: logging.Logger, request, response_time: float = None):
    """Log de peticiones API"""
    extra = {
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else "unknown",
        "response_time_ms": round(response_time * 1000, 2) if response_time else None
    }
    logger.info("API request", extra=extra)

def log_business_event(event_type: str, user_id: str, details: Dict[str, Any]):
    """Log de eventos de negocio (cotizaciones, PDFs generados, etc)"""
    logger = logging.getLogger("business")
    extra = {
        "event_type": event_type,
        "user_id": user_id,
        **details
    }
    logger.info(f"Business event: {event_type}", extra=extra)

def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log de eventos de seguridad"""
    logger = logging.getLogger("security")
    extra = {
        "event_type": event_type,
        **details
    }
    logger.warning(f"Security event: {event_type}", extra=extra)