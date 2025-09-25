#!/usr/bin/env python3
"""
Archivo de inicio para Render
"""
import uvicorn
import os
from dotenv import load_dotenv
from app.main import app

# Cargar variables de entorno
load_dotenv()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Desactivar reload en producción
        log_level="info"
    )