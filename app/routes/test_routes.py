"""
Endpoints de prueba para debugging y testing.
"""
import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from app.config import settings
from app.security import security, validate_phone_number, verify_admin_token
from app.utils.service_utils import get_services

logger = logging.getLogger(__name__)

test_router = APIRouter()


@test_router.post("/test")
async def test_webhook():
    """
    Endpoint de prueba para verificar respuestas XML
    """
    response = MessagingResponse()
    response.message("Mensaje de prueba desde ShrimpBot")
    response_xml = str(response)
    logger.info(f"Respuesta de prueba XML: {response_xml}")
    return PlainTextResponse(response_xml, media_type="application/xml")


@test_router.post("/simple")
async def simple_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    MessageSid: str = Form(...)
):
    """
    Webhook simplificado para debugging
    """
    logger.info(f"SIMPLE: Mensaje de {From}: {Body}")

    response = MessagingResponse()
    response.message("✅ Mensaje recibido correctamente!")

    response_xml = str(response)
    logger.info(f"SIMPLE: Enviando XML: {response_xml}")

    return PlainTextResponse(response_xml, media_type="application/xml")


@test_router.post("/test-response")
async def test_response():
    """
    Endpoint para probar respuestas TwiML
    """
    response = MessagingResponse()
    response.message("🦐 Mensaje de prueba desde BGR Export Bot")

    response_xml = str(response)
    logger.info(f"TEST: XML generado: {response_xml}")

    return PlainTextResponse(response_xml, media_type="application/xml")


@test_router.get("/test-twilio")
async def test_twilio(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Endpoint para probar las credenciales de Twilio
    """
    # Verificar token de administrador
    if not verify_admin_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER

        if not all([account_sid, auth_token, whatsapp_number]):
            return {
                "status": "error",
                "message": "Credenciales de Twilio no configuradas",
                "config": {
                    "account_sid": bool(account_sid),
                    "auth_token": bool(auth_token),
                    "whatsapp_number": bool(whatsapp_number)
                }
            }

        client = Client(account_sid, auth_token)

        # Probar conexión obteniendo información de la cuenta
        account = client.api.accounts(account_sid).fetch()

        return {
            "status": "success",
            "message": "Credenciales de Twilio válidas",
            "account_name": account.friendly_name,
            "account_status": account.status,
            "whatsapp_number": whatsapp_number
        }

    except Exception as e:
        logger.error(f"Error probando Twilio: {str(e)}")
        return {"status": "error", "message": str(e)}


@test_router.post("/test-pdf-send")
async def test_pdf_send(
    phone_number: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Endpoint para probar el envío de PDFs
    """
    # Verificar token de administrador
    if not verify_admin_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Validar número de teléfono
    if not phone_number.startswith("whatsapp:"):
        phone_number = f"whatsapp:{phone_number}"

    if not validate_phone_number(phone_number):
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    try:
        # Crear una cotización de prueba
        test_quote = {
            'size': '16/20',
            'product': 'HLSO',
            'quantity': 15000,
            'destination': 'China',
            'fob_price': 5.50,
            'glaseo_price': 6.05,
            'final_price': 6.85,
            'freight_cost': 0.80,
            'total_value': 102750.00
        }

        # Inicializar servicios si no están inicializados
        pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service = get_services()

        # Generar PDF de prueba
        pdf_path = pdf_generator.generate_quote_pdf(test_quote, f"whatsapp:{phone_number}")

        if pdf_path:
            # Intentar enviar por WhatsApp
            pdf_sent = whatsapp_sender.send_pdf_document(
                f"whatsapp:{phone_number}",
                pdf_path,
                "📄 PDF de prueba - BGR Export"
            )

            filename = pdf_path.split('/')[-1] if '/' in pdf_path else pdf_path.split('\\')[-1]
            download_url = f"https://e28980114917.ngrok-free.app/webhook/download-pdf/{filename}"

            return {
                "status": "success" if pdf_sent else "partial",
                "message": "PDF enviado por WhatsApp" if pdf_sent else "PDF generado, pero no enviado por WhatsApp",
                "pdf_generated": True,
                "pdf_sent_whatsapp": pdf_sent,
                "download_url": download_url
            }
        else:
            return {
                "status": "error",
                "message": "Error generando PDF de prueba"
            }

    except Exception as e:
        logger.error(f"Error en test de PDF: {str(e)}")
        return {"status": "error", "message": str(e)}
