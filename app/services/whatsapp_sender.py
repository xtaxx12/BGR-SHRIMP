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
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("✅ Cliente de Twilio inicializado")
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
            
            # Obtener URL pública del PDF
            # Para desarrollo local, necesitarás usar ngrok o similar
            base_url = os.getenv('BASE_URL', 'http://localhost:8000')
            filename = os.path.basename(pdf_path)
            pdf_url = f"{base_url}/webhook/download-pdf/{filename}"
            
            # Mensaje por defecto si no se proporciona
            if not message_text:
                message_text = "📄 Aquí tienes tu cotización en PDF"
            
            # Enviar mensaje con archivo adjunto
            message = self.client.messages.create(
                from_=self.whatsapp_number,
                to=to_number,
                body=message_text,
                media_url=[pdf_url]
            )
            
            logger.info(f"✅ PDF enviado exitosamente a {to_number}, SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando PDF por WhatsApp: {str(e)}")
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