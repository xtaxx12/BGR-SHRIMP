#!/usr/bin/env python3
"""
Script para ejecutar el bot localmente para desarrollo y pruebas
"""
import uvicorn
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print("🚀 Iniciando BGR Export WhatsApp Bot...")
    print(f"📡 Servidor corriendo en: http://localhost:{port}")
    print(f"🔧 Modo debug: {debug}")
    print("📱 Webhook URL para Twilio: http://localhost:{}/webhook/whatsapp".format(port))


    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        log_level="info"
    )