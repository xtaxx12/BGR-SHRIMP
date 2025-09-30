import requests
import os
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AudioHandler:
    def __init__(self):
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    def download_audio_from_twilio(self, media_url: str) -> Optional[str]:
        """
        Descarga un archivo de audio desde Twilio y lo guarda temporalmente
        """
        try:
            logger.info(f"🎤 Descargando audio desde: {media_url}")
            
            # Hacer petición autenticada a Twilio
            response = requests.get(
                media_url,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=30
            )
            
            if response.status_code == 200:
                # Crear archivo temporal
                with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
                    temp_file.write(response.content)
                    temp_path = temp_file.name
                
                logger.debug(f"✅ Audio descargado en: {temp_path}")
                return temp_path
            else:
                logger.error(f"❌ Error descargando audio: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error en descarga de audio: {str(e)}")
            return None
    
    def cleanup_temp_file(self, file_path: str):
        """
        Elimina el archivo temporal
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"🗑️ Archivo temporal eliminado: {file_path}")
        except Exception as e:
            logger.error(f"❌ Error eliminando archivo temporal: {str(e)}")
    
    def convert_ogg_to_mp3(self, ogg_path: str) -> Optional[str]:
        """
        Convierte archivo OGG a MP3 (Whisper prefiere MP3)
        """
        try:
            # Para simplificar, vamos a intentar usar el archivo OGG directamente
            # Si hay problemas, podríamos agregar conversión con ffmpeg
            return ogg_path
        except Exception as e:
            logger.error(f"❌ Error convirtiendo audio: {str(e)}")
            return None