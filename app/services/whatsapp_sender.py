from twilio.rest import Client
import os
import logging
from typing import Optional

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
                logger.info(f"✅ Cliente de Twilio inicializado - Cuenta: {account.friendly_name}")
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
            
            # Método 1: Intentar con URL pública si está disponible
            base_url = os.getenv('BASE_URL')
            if base_url and not base_url.startswith('http://localhost'):
                filename = os.path.basename(pdf_path)
                pdf_url = f"{base_url}/webhook/download-pdf/{filename}"
                
                try:
                    message = self.client.messages.create(
                        from_=self.whatsapp_number,
                        to=to_number,
                        body=message_text,
                        media_url=[pdf_url]
                    )
                    logger.info(f"✅ PDF enviado exitosamente via URL a {to_number}, SID: {message.sid}")
                    return True
                except Exception as url_error:
                    logger.warning(f"⚠️ Error enviando via URL: {url_error}")
            
            # Método 2: Subir archivo directamente (requiere servidor público)
            try:
                # Para desarrollo local, necesitamos una URL pública temporal
                # Usaremos el endpoint de descarga local como fallback
                filename = os.path.basename(pdf_path)
                local_url = f"http://localhost:8000/webhook/download-pdf/{filename}"
                
                message = self.client.messages.create(
                    from_=self.whatsapp_number,
                    to=to_number,
                    body=message_text,
                    media_url=[local_url]
                )
                
                logger.info(f"✅ PDF enviado exitosamente a {to_number}, SID: {message.sid}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error enviando PDF por WhatsApp: {str(e)}")
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
            
            logger.info(f"✅ Mensaje enviado exitosamente a {to_number}, SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje por WhatsApp: {str(e)}")
            return False