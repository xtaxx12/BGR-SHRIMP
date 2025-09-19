import os
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
    
    # Configuración del Excel
    EXCEL_PATH = os.getenv("EXCEL_PATH", "data/CALCULO_DE _PRECIOS-AGUAJE17.xlsx")
    
    # Configuración opcional de OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Configuración de producción
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

settings = Settings()