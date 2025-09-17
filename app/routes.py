from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from app.services.pricing import PricingService
from app.services.utils import parse_user_message, format_price_response
import logging

logger = logging.getLogger(__name__)

webhook_router = APIRouter()
pricing_service = PricingService()

@webhook_router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    MessageSid: str = Form(...)
):
    """
    Endpoint para recibir mensajes de WhatsApp desde Twilio
    """
    try:
        logger.info(f"Mensaje recibido de {From}: {Body}")
        
        # Crear respuesta de Twilio
        response = MessagingResponse()
        
        # Procesar mensaje del usuario
        user_input = parse_user_message(Body)
        
        if not user_input:
            response.message("¡Hola! 👋 Soy el bot de BGR Export.\n\n"
                           "Puedes consultarme precios de camarón enviando:\n"
                           "• Talla (ej: 16/20, 21/25)\n"
                           "• Producto y talla (ej: HLSO 16/20)\n"
                           "• Consulta completa (ej: Precio HLSO 16/20 para 15,000 lb destino China)")
        else:
            # Obtener precio del camarón
            price_info = pricing_service.get_shrimp_price(user_input)
            
            if price_info:
                formatted_response = format_price_response(price_info)
                response.message(formatted_response)
            else:
                response.message("❌ No encontré información para esa talla.\n\n"
                               "Tallas disponibles: 8/12, 13/15, 16/20, 21/25, 26/30, 31/35, 36/40, 41/50, 51/60, 61/70")
        
        return PlainTextResponse(str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}")
        response = MessagingResponse()
        response.message("❌ Ocurrió un error procesando tu consulta. Intenta nuevamente.")
        return PlainTextResponse(str(response), media_type="application/xml")

@webhook_router.get("/whatsapp")
async def whatsapp_webhook_verification(request: Request):
    """
    Verificación del webhook de Twilio
    """
    return {"status": "webhook_ready"}