#!/usr/bin/env python3
"""
Archivo de inicio para Render
"""
import uvicorn
import os
from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Desactivar reload en producción
        log_level="info"
    )