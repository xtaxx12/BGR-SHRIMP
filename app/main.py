from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import uvicorn
from app.routes import webhook_router
from app.config import settings
import logging

# Configurar logging
log_level = logging.DEBUG if settings.DEBUG else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BGR Export WhatsApp Bot",
    description="Bot de WhatsApp para consulta de precios de camarón",
    version="1.0.0"
)

# Incluir rutas
app.include_router(webhook_router, prefix="/webhook")

@app.get("/")
async def root():
    return {"message": "BGR Export WhatsApp Bot - Sistema de consulta de precios de camarón"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bgr-whatsapp-bot"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)