"""
Endpoints para descarga de archivos PDF.
"""
import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

pdf_router = APIRouter()


@pdf_router.get("/download-pdf/{filename}")
async def download_pdf(filename: str):
    """
    Endpoint para descargar PDFs generados
    """
    try:
        pdf_path = os.path.join("generated_pdfs", filename)
        logger.info(f"🔍 Buscando PDF en: {pdf_path}")
        logger.info(f"📁 Directorio actual: {os.getcwd()}")

        # Listar archivos en el directorio
        if os.path.exists("generated_pdfs"):
            files = os.listdir("generated_pdfs")
            logger.info(f"📄 Archivos en generated_pdfs: {files}")
        else:
            logger.error("❌ Directorio generated_pdfs no existe")

        if os.path.exists(pdf_path):
            logger.debug(f"✅ PDF encontrado: {pdf_path}")
            return FileResponse(
                path=pdf_path,
                filename=filename,
                media_type='application/pdf',
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        else:
            logger.error(f"❌ PDF no encontrado en: {pdf_path}")
            raise HTTPException(status_code=404, detail="PDF no encontrado")

    except Exception as e:
        logger.error(f"Error descargando PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
