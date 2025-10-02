from functools import wraps
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
from typing import Dict, Optional, Callable
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from collections import defaultdict
import time
import logging
import secrets
from app.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        
    def is_allowed(self, identifier: str) -> bool:
        now = time.time()
        self.requests[identifier] = [
            timestamp for timestamp in self.requests[identifier]
            if now - timestamp < self.window_seconds
        ]
        
        if len(self.requests[identifier]) >= self.max_requests:
            return False
            
        self.requests[identifier].append(now)
        return True
    
    def cleanup_old_entries(self):
        now = time.time()
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                timestamp for timestamp in self.requests[identifier]
                if now - timestamp < self.window_seconds
            ]
            if not self.requests[identifier]:
                del self.requests[identifier]

class TwilioWebhookValidator:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
    
    def validate_request(self, url: str, params: dict, x_twilio_signature: str) -> bool:
        if not x_twilio_signature:
            return False
            
        # Ordenar parámetros alfabéticamente por clave
        sorted_params = sorted(params.items())
        
        # Construir string para validar
        data = url
        for key, value in sorted_params:
            data += f"{key}{value}"
        
        # Calcular firma esperada
        expected_signature = base64.b64encode(
            hmac.new(
                self.auth_token.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode()
        
        # Comparación segura contra timing attacks
        return hmac.compare_digest(expected_signature, x_twilio_signature)

# Instancias globales
rate_limiter = RateLimiter(max_requests=30, window_seconds=60)
webhook_validator = TwilioWebhookValidator(settings.TWILIO_AUTH_TOKEN or "")

# Decorador para validar webhooks de Twilio
def validate_twilio_webhook(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Solo validar en producción
        if settings.is_production and settings.TWILIO_AUTH_TOKEN:
            # Obtener URL completa
            url = str(request.url)
            
            # Obtener firma de Twilio
            x_twilio_signature = request.headers.get("X-Twilio-Signature", "")
            
            # Obtener parámetros del formulario
            form_data = await request.form()
            params = dict(form_data)
            
            # Validar
            if not webhook_validator.validate_request(url, params, x_twilio_signature):
                logger.warning(f"Invalid Twilio webhook signature from {request.client.host}")
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        return await func(*args, **kwargs)
    
    return wrapper

# Decorador para rate limiting
def rate_limit(identifier_func: Optional[Callable] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Obtener identificador (por defecto IP)
            if identifier_func:
                identifier = identifier_func(request, *args, **kwargs)
            else:
                identifier = request.client.host if request.client else "unknown"
            
            # Verificar rate limit
            if not rate_limiter.is_allowed(identifier):
                logger.warning(f"Rate limit exceeded for {identifier}")
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later."
                )
            
            # Limpiar entradas antiguas periódicamente
            if secrets.randbelow(100) == 0:  # 1% de probabilidad
                rate_limiter.cleanup_old_entries()
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

# Bearer token para endpoints administrativos
security = HTTPBearer()

def verify_admin_token(credentials: HTTPAuthorizationCredentials) -> bool:
    expected_token = os.getenv("ADMIN_API_TOKEN")
    if not expected_token:
        logger.error("ADMIN_API_TOKEN not configured")
        return False
    
    # Comparación segura contra timing attacks
    return secrets.compare_digest(credentials.credentials, expected_token)

# Sanitizador de entrada
def sanitize_input(text: str, max_length: int = 1000) -> str:
    if not text:
        return ""
    
    # Limitar longitud
    text = text[:max_length]
    
    # Remover caracteres de control (excepto saltos de línea y tabs)
    allowed_chars = set(range(32, 127))  # ASCII imprimibles
    allowed_chars.update([9, 10, 13])  # Tab, LF, CR
    
    sanitized = "".join(
        char for char in text 
        if ord(char) in allowed_chars or ord(char) > 127  # Permitir Unicode
    )
    
    return sanitized.strip()

# Validador de número de teléfono
def validate_phone_number(phone: str) -> bool:
    # Formato esperado: whatsapp:+[código país][número]
    if not phone.startswith("whatsapp:+"):
        return False
    
    # Extraer número
    number = phone[10:]  # Remover "whatsapp:+"
    
    # Validar que solo contenga dígitos
    if not number.isdigit():
        return False
    
    # Validar longitud razonable (entre 7 y 15 dígitos)
    if len(number) < 7 or len(number) > 15:
        return False
    
    return True

# Manejador seguro de archivos temporales
import tempfile
import os

class SecureTempFile:
    def __init__(self, suffix: str = ""):
        self.suffix = suffix
        self.file_path = None
        
    def __enter__(self):
        fd, self.file_path = tempfile.mkstemp(suffix=self.suffix)
        os.close(fd)
        return self.file_path
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file_path and os.path.exists(self.file_path):
            try:
                os.unlink(self.file_path)
            except Exception as e:
                logger.error(f"Error removing temp file {self.file_path}: {e}")

# Headers de seguridad
def add_security_headers(response: Response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response