"""
Utilidades para inicialización de servicios.
"""
import logging

from app.services.interactive import InteractiveMessageService
from app.services.openai_service import OpenAIService
from app.services.pdf_generator import PDFGenerator
from app.services.pricing import PricingService
from app.services.whatsapp_sender import WhatsAppSender

logger = logging.getLogger(__name__)

# Servicios se inicializarán de manera lazy
pricing_service = None
interactive_service = None
pdf_generator = None
openai_service = None
whatsapp_sender = None


def get_services():
    """
    Inicializa los servicios de manera lazy
    """
    global pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service

    if pricing_service is None:
        pricing_service = PricingService()
        # Pasar el servicio de Excel al servicio interactivo para compartir datos
        interactive_service = InteractiveMessageService(pricing_service.excel_service)
        pdf_generator = PDFGenerator()
        whatsapp_sender = WhatsAppSender()
        openai_service = OpenAIService()
        logger.debug("✅ Servicios inicializados")

    return pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service
