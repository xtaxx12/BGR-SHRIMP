"""
Endpoints administrativos para gestión y monitoreo del sistema.
"""
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.security import security, verify_admin_token
from app.utils.service_utils import get_services

logger = logging.getLogger(__name__)

admin_router = APIRouter()


@admin_router.post("/reload-data")
async def reload_data(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Endpoint para recargar datos desde Google Sheets
    """
    # Verificar token de administrador
    if not verify_admin_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Reinicializar servicios con variables de entorno actuales
        from app.utils import service_utils

        # Forzar reinicialización
        service_utils.pricing_service = None
        service_utils.interactive_service = None
        service_utils.pdf_generator = None
        service_utils.whatsapp_sender = None
        service_utils.openai_service = None

        # Inicializar servicios
        pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service = get_services()

        # Contar datos cargados
        total_prices = sum(len(product_data) for product_data in pricing_service.excel_service.prices_data.values())
        products = [p for p in pricing_service.excel_service.prices_data.keys() if pricing_service.excel_service.prices_data[p]]

        return {
            "status": "success",
            "message": "Servicios reinicializados y datos recargados",
            "total_prices": total_prices,
            "products": products,
            "google_sheets_id": os.getenv('GOOGLE_SHEETS_ID', 'No configurado')[:20] + "..."
        }
    except Exception as e:
        logger.error(f"Error recargando datos: {str(e)}")
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@admin_router.get("/data-status")
async def data_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Endpoint para verificar el estado de los datos
    """
    # Verificar token de administrador
    if not verify_admin_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Inicializar servicios si no están inicializados
        pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service = get_services()

        # Verificar datos actuales
        total_prices = sum(len(product_data) for product_data in pricing_service.excel_service.prices_data.values())
        products = [p for p in pricing_service.excel_service.prices_data.keys() if pricing_service.excel_service.prices_data[p]]

        # Verificar configuración de Google Sheets
        sheets_id = os.getenv('GOOGLE_SHEETS_ID')
        sheets_credentials = os.getenv('GOOGLE_SHEETS_CREDENTIALS')

        # Verificar si el servicio de Google Sheets está funcionando
        sheets_service_status = "No inicializado"
        if hasattr(pricing_service.excel_service, 'google_sheets_service'):
            if pricing_service.excel_service.google_sheets_service.sheet:
                sheets_service_status = "Conectado"
            else:
                sheets_service_status = "Error de conexión"

        return {
            "status": "success",
            "data_source": "Google Sheets" if sheets_id and sheets_credentials else "Local Excel",
            "total_prices": total_prices,
            "products": products,
            "google_sheets_configured": bool(sheets_id and sheets_credentials),
            "google_sheets_id": sheets_id[:20] + "..." if sheets_id else None,
            "sheets_service_status": sheets_service_status,
            "env_loaded": bool(sheets_id)
        }
    except Exception as e:
        logger.error(f"Error verificando estado: {str(e)}")
        return {"status": "error", "message": str(e)}