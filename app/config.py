import os
import secrets

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings:
    # Configuración de Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    # Configuración del servidor
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

    # Configuración del Excel
    EXCEL_PATH = os.getenv("EXCEL_PATH", "data/CALCULO_DE _PRECIOS-AGUAJE17.xlsx")

    # Configuración de Google Sheets
    GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

    # Configuración opcional de OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Configuración de producción
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    # Configuración de seguridad
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
    ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    # Rate limiting
    RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "30"))
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # Timeouts
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    PDF_GENERATION_TIMEOUT = int(os.getenv("PDF_GENERATION_TIMEOUT", "60"))

    # Límites de entrada
    MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "1000"))
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    def validate(self):
        """Validar configuración crítica"""
        if self.is_production:
            required = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "SECRET_KEY"]
            missing = [var for var in required if not getattr(self, var)]
            if missing:
                raise ValueError(f"Missing required configuration: {', '.join(missing)}")

settings = Settings()

# Validar configuración en producción
if settings.is_production:
    try:
        settings.validate()
    except ValueError as e:
        import logging
        logging.error(f"Configuration error: {e}")
        # En producción, fallar rápido si falta configuración crítica
        raise
