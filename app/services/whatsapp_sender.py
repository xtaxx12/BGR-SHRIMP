import logging
import os

from twilio.rest import Client

logger = logging.getLogger(__name__)

class WhatsAppSender:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')

        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                # Probar conexión
                account = self.client.api.accounts(self.account_sid).fetch()
                logger.debug(f"✅ Cliente de Twilio inicializado - Cuenta: {account.friendly_name}")
            except Exception as e:
                self.client = None
                logger.error(f"❌ Error inicializando Twilio: {str(e)}")
        else:
            self.client = None
            logger.warning("⚠️ Credenciales de Twilio no configuradas")

    def send_pdf_document(self, to_number: str, pdf_path: str, message_text: str = None) -> bool:
        """
        Envía un PDF como documento por WhatsApp
        """
        try:
            if not self.client:
                logger.error("❌ Cliente de Twilio no disponible")
                return False

            if not os.path.exists(pdf_path):
                logger.error(f"❌ Archivo PDF no encontrado: {pdf_path}")
                return False

            # Mensaje por defecto si no se proporciona
            if not message_text:
                message_text = "📄 Aquí tienes tu cotización en PDF"

            # Obtener URL base
            base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
            
            # Validar que no sea localhost en producción
            if 'localhost' in base_url or '127.0.0.1' in base_url:
                logger.warning(f"⚠️ BASE_URL apunta a localhost: {base_url}")
                logger.warning("⚠️ Twilio no podrá acceder al PDF. Usando URL de producción por defecto.")
                base_url = 'https://bgr-shrimp.onrender.com'

            # Construir URL pública del PDF
            filename = os.path.basename(pdf_path)
            pdf_url = f"{base_url}/webhook/download-pdf/{filename}"

            logger.info(f"📤 Intentando enviar PDF a {to_number}")
            logger.info(f"📎 URL del PDF: {pdf_url}")

            try:
                message = self.client.messages.create(
                    from_=self.whatsapp_number,
                    to=to_number,
                    body=message_text,
                    media_url=[pdf_url]
                )
                logger.info(f"✅ PDF enviado exitosamente a {to_number}, SID: {message.sid}")
                return True
            except Exception as send_error:
                logger.error(f"❌ Error enviando PDF por WhatsApp: {str(send_error)}")
                logger.error(f"   - From: {self.whatsapp_number}")
                logger.error(f"   - To: {to_number}")
                logger.error(f"   - Media URL: {pdf_url}")
                return False

        except Exception as e:
            logger.error(f"❌ Error general enviando PDF por WhatsApp: {str(e)}")
            return False

    def send_message(self, to_number: str, message_text: str) -> bool:
        """
        Envía un mensaje de texto simple por WhatsApp
        """
        try:
            if not self.client:
                logger.error("❌ Cliente de Twilio no disponible")
                return False

            message = self.client.messages.create(
                from_=self.whatsapp_number,
                to=to_number,
                body=message_text
            )

            logger.debug(f"✅ Mensaje enviado exitosamente a {to_number}, SID: {message.sid}")
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando mensaje por WhatsApp: {str(e)}")
            return False
