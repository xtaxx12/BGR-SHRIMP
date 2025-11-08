"""
Tests de integración para rutas de WhatsApp
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestWhatsAppWebhook:
    """Tests de integración para el webhook de WhatsApp"""

    @pytest.fixture
    def whatsapp_payload(self):
        """Payload básico de WhatsApp"""
        return {
            "MessageSid": "SM1234567890",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "Hola",
            "NumMedia": "0",
            "MediaUrl0": "",
            "MediaContentType0": ""
        }

    @patch('app.routes.whatsapp_routes.get_services')
    @patch('app.routes.whatsapp_routes.is_duplicate_message')
    @patch('app.routes.whatsapp_routes.validate_phone_number')
    @patch('app.routes.whatsapp_routes.sanitize_input')
    def test_whatsapp_webhook_basic_message(
        self, mock_sanitize, mock_validate, mock_is_dup, mock_get_services, client, whatsapp_payload
    ):
        """Test envío de mensaje básico por WhatsApp"""
        # Configurar mocks
        mock_validate.return_value = True
        mock_sanitize.return_value = "Hola"
        mock_is_dup.return_value = False

        # Mock de servicios
        mock_pricing = MagicMock()
        mock_interactive = MagicMock()
        mock_pdf = MagicMock()
        mock_whatsapp = MagicMock()
        mock_openai = MagicMock()

        mock_get_services.return_value = (
            mock_pricing, mock_interactive, mock_pdf, mock_whatsapp, mock_openai
        )

        response = client.post("/webhook/whatsapp", data=whatsapp_payload)
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]

    @patch('app.routes.whatsapp_routes.is_duplicate_message')
    def test_whatsapp_webhook_duplicate_message(
        self, mock_is_dup, client, whatsapp_payload
    ):
        """Test mensaje duplicado es rechazado"""
        mock_is_dup.return_value = True

        response = client.post("/webhook/whatsapp", data=whatsapp_payload)
        assert response.status_code == 200
        # Respuesta vacía para duplicados
        assert "<Response" in response.text

    @patch('app.routes.whatsapp_routes.validate_phone_number')
    def test_whatsapp_webhook_invalid_phone(
        self, mock_validate, client, whatsapp_payload
    ):
        """Test número de teléfono inválido"""
        mock_validate.return_value = False

        response = client.post("/webhook/whatsapp", data=whatsapp_payload)
        assert response.status_code == 400

    def test_whatsapp_verification_endpoint(self, client):
        """Test endpoint de verificación GET /whatsapp"""
        response = client.get("/webhook/whatsapp")
        assert response.status_code == 200
        assert response.text == "Webhook de WhatsApp activo"


class TestWhatsAppAudioMessages:
    """Tests para mensajes de audio"""

    @pytest.fixture
    def audio_payload(self):
        """Payload con mensaje de audio"""
        return {
            "MessageSid": "SM_AUDIO_123",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/test-audio.ogg",
            "MediaContentType0": "audio/ogg"
        }

    @patch('app.routes.whatsapp_routes.get_services')
    @patch('app.routes.whatsapp_routes.AudioHandler')
    @patch('app.routes.whatsapp_routes.is_duplicate_message')
    @patch('app.routes.whatsapp_routes.validate_phone_number')
    @patch('app.routes.whatsapp_routes.SecureTempFile')
    def test_audio_message_transcription_success(
        self, mock_temp_file, mock_validate, mock_is_dup,
        mock_audio_handler, mock_get_services, client, audio_payload
    ):
        """Test transcripción exitosa de mensaje de audio"""
        # Configurar mocks
        mock_validate.return_value = True
        mock_is_dup.return_value = False

        # Mock de SecureTempFile
        mock_temp_file.return_value.__enter__.return_value = "/tmp/audio.ogg"

        # Mock de AudioHandler
        mock_handler = MagicMock()
        mock_handler.download_audio_from_twilio.return_value = "/tmp/audio.ogg"
        mock_audio_handler.return_value = mock_handler

        # Mock de OpenAI service
        mock_openai = MagicMock()
        mock_openai.transcribe_audio.return_value = "precio de camarón"

        mock_get_services.return_value = (
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), mock_openai
        )

        response = client.post("/webhook/whatsapp", data=audio_payload)
        assert response.status_code == 200
        assert "Audio recibido" in response.text or "application/xml" in response.headers["content-type"]


class TestWhatsAppSessionStates:
    """Tests para diferentes estados de sesión"""

    @pytest.fixture
    def session_payload(self):
        """Payload para tests de sesión"""
        return {
            "MessageSid": "SM_SESSION_123",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "20",
            "NumMedia": "0",
            "MediaUrl0": "",
            "MediaContentType0": ""
        }

    @patch('app.routes.whatsapp_routes.get_services')
    @patch('app.routes.whatsapp_routes.session_manager')
    @patch('app.routes.whatsapp_routes.is_duplicate_message')
    @patch('app.routes.whatsapp_routes.validate_phone_number')
    @patch('app.routes.whatsapp_routes.sanitize_input')
    def test_waiting_for_glaseo_state(
        self, mock_sanitize, mock_validate, mock_is_dup,
        mock_session_mgr, mock_get_services, client, session_payload
    ):
        """Test estado waiting_for_glaseo"""
        # Configurar mocks
        mock_validate.return_value = True
        mock_sanitize.return_value = "20"
        mock_is_dup.return_value = False

        # Simular sesión en estado waiting_for_glaseo
        mock_session_mgr.get_session.return_value = {
            'state': 'waiting_for_glaseo',
            'data': {
                'ai_query': {
                    'product': 'HLSO',
                    'size': '16/20',
                    'quantity': 1000
                }
            },
            'conversation_history': [],
            'last_activity': 0
        }

        # Mock de pricing service
        mock_pricing = MagicMock()
        mock_pricing.get_shrimp_price.return_value = {
            'producto': 'HLSO',
            'talla': '16/20',
            'precio': 8.50
        }

        mock_get_services.return_value = (
            mock_pricing, MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )

        response = client.post("/webhook/whatsapp", data=session_payload)
        assert response.status_code == 200
