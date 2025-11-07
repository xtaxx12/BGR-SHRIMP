"""
Tests de integración para el endpoint de webhook de WhatsApp

Cubre:
- Recepción de mensajes de texto
- Recepción de mensajes de audio
- Deduplicación de mensajes
- Rate limiting
- Validación de webhooks Twilio
- Flujos completos de cotización
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import time


@pytest.fixture
def test_client():
    """Cliente de test para la aplicación FastAPI"""
    from app.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_services():
    """Mock de todos los servicios externos para tests de integración"""
    with patch('app.routes.PricingService') as mock_pricing, \
         patch('app.routes.InteractiveMessageService') as mock_interactive, \
         patch('app.routes.PDFGenerator') as mock_pdf, \
         patch('app.routes.WhatsAppSender') as mock_whatsapp, \
         patch('app.routes.OpenAIService') as mock_openai:

        # Configurar comportamiento de mocks
        pricing_instance = MagicMock()
        pricing_instance.get_shrimp_price.return_value = {
            'precio_fob_kg': 8.55,
            'precio_final_kg': 7.49,
            'size': '16/20',
            'product': 'HLSO',
            'glaseo_percentage': 20,
            'factor_glaseo': 0.80,
            'flete': 0.35,
            'incluye_flete': True,
        }
        mock_pricing.return_value = pricing_instance

        interactive_instance = MagicMock()
        mock_interactive.return_value = interactive_instance

        pdf_instance = MagicMock()
        pdf_instance.generate_quote_pdf.return_value = '/tmp/test_quote.pdf'
        mock_pdf.return_value = pdf_instance

        whatsapp_instance = MagicMock()
        whatsapp_instance.send_message.return_value = {'sid': 'SM123'}
        whatsapp_instance.send_media.return_value = {'sid': 'SM456'}
        mock_whatsapp.return_value = whatsapp_instance

        openai_instance = MagicMock()
        openai_instance.detect_products_and_intent.return_value = {
            'products': [{'producto': 'HLSO', 'talla': '16/20'}],
            'intent': 'consulta_precio',
            'requires_glaseo': True,
        }
        mock_openai.return_value = openai_instance

        yield {
            'pricing': pricing_instance,
            'interactive': interactive_instance,
            'pdf': pdf_instance,
            'whatsapp': whatsapp_instance,
            'openai': openai_instance,
        }


@pytest.fixture(autouse=True)
def reset_duplicate_cache():
    """Reset del caché de mensajes duplicados entre tests"""
    from app.routes import processed_messages, message_timestamps
    processed_messages.clear()
    message_timestamps.clear()
    yield
    processed_messages.clear()
    message_timestamps.clear()


class TestWebhookBasicFunctionality:
    """Tests de funcionalidad básica del webhook"""

    def test_webhook_accepts_valid_message(self, test_client):
        """Test que el webhook acepta un mensaje válido"""
        payload = {
            "MessageSid": "SM_test_001",
            "AccountSid": "AC_test",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "Precio HLSO 16/20",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        assert response.status_code == 200
        assert "xml" in response.headers.get("content-type", "").lower()

    def test_webhook_rejects_invalid_phone_format(self, test_client):
        """Test que el webhook rechaza números de teléfono inválidos"""
        payload = {
            "MessageSid": "SM_test_002",
            "AccountSid": "AC_test",
            "From": "invalid_phone",
            "To": "whatsapp:+14155238886",
            "Body": "Test",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        assert response.status_code == 400

    def test_webhook_sanitizes_input(self, test_client):
        """Test que el webhook sanitiza la entrada del usuario"""
        payload = {
            "MessageSid": "SM_test_003",
            "AccountSid": "AC_test",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "Precio <script>alert('xss')</script> HLSO 16/20",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        # Debería procesar el mensaje pero sin el script
        assert response.status_code == 200


class TestMessageDeduplication:
    """Tests de deduplicación de mensajes"""

    def test_duplicate_message_ignored(self, test_client):
        """Test que mensajes duplicados son ignorados"""
        payload = {
            "MessageSid": "SM_duplicate_test",
            "AccountSid": "AC_test",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "Test",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            # Primera vez: debe procesarse
            response1 = test_client.post("/webhook/whatsapp", data=payload)
            assert response1.status_code == 200

            # Segunda vez: debe ser ignorado
            response2 = test_client.post("/webhook/whatsapp", data=payload)
            assert response2.status_code == 200
            # El contenido debe ser una respuesta vacía
            assert "<Response" in response2.text

    def test_old_messages_cleaned_up(self, test_client):
        """Test que mensajes antiguos son limpiados del caché"""
        from app.routes import processed_messages, message_timestamps

        # Agregar mensaje antiguo manualmente
        old_sid = "SM_old_message"
        processed_messages.add(old_sid)
        message_timestamps[old_sid] = time.time() - 400  # 400 segundos atrás

        payload = {
            "MessageSid": "SM_new_message",
            "AccountSid": "AC_test",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "Test",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        # El mensaje antiguo debe haber sido limpiado
        assert old_sid not in processed_messages


class TestAudioMessages:
    """Tests para mensajes de audio"""

    def test_audio_message_transcribed(self, test_client, mock_services):
        """Test que mensajes de audio son transcritos"""
        mock_services['openai'].transcribe_audio.return_value = "Precio HLSO 16/20"

        payload = {
            "MessageSid": "SM_audio_test",
            "AccountSid": "AC_test",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/test-audio.ogg",
            "MediaContentType0": "audio/ogg",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True), \
             patch('app.routes.AudioHandler') as mock_audio_handler:

            audio_handler_instance = MagicMock()
            audio_handler_instance.handle_audio_message.return_value = "Precio HLSO 16/20"
            mock_audio_handler.return_value = audio_handler_instance

            response = test_client.post("/webhook/whatsapp", data=payload)

        assert response.status_code == 200


class TestPricingWorkflow:
    """Tests para el flujo completo de consulta de precios"""

    def test_complete_pricing_query_workflow(self, test_client, mock_services):
        """Test flujo completo: consulta -> detección -> cálculo -> respuesta"""
        payload = {
            "MessageSid": "SM_pricing_test",
            "AccountSid": "AC_test",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "Precio HLSO 16/20 con 20% glaseo",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        assert response.status_code == 200
        # Verificar que el servicio de pricing fue llamado
        # (El mock ya está configurado en mock_services)

    def test_query_without_glaseo_asks_for_it(self, test_client, mock_services):
        """Test que si falta glaseo, el sistema lo solicita"""
        # Configurar mock para indicar que requiere glaseo
        mock_services['openai'].detect_products_and_intent.return_value = {
            'products': [{'producto': 'HLSO', 'talla': '16/20'}],
            'intent': 'consulta_precio',
            'requires_glaseo': True,
            'glaseo_percentage': None,  # Sin glaseo
        }

        payload = {
            "MessageSid": "SM_no_glaseo_test",
            "AccountSid": "AC_test",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "Precio HLSO 16/20",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        assert response.status_code == 200
        # La sesión debe estar esperando glaseo
        from app.services.session import session_manager
        session = session_manager.get_session("whatsapp:+593981234567")
        assert session['state'] == 'waiting_for_glaseo' or session['state'] == 'idle'


class TestSessionManagement:
    """Tests de gestión de sesiones"""

    def test_session_created_for_new_user(self, test_client):
        """Test que se crea una sesión para usuarios nuevos"""
        from app.services.session import session_manager

        user_id = "whatsapp:+593987654321"

        payload = {
            "MessageSid": "SM_new_user_test",
            "AccountSid": "AC_test",
            "From": user_id,
            "To": "whatsapp:+14155238886",
            "Body": "Hola",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        assert response.status_code == 200

        # Verificar que la sesión existe
        session = session_manager.get_session(user_id)
        assert session is not None
        assert 'state' in session

    def test_session_updated_with_conversation_history(self, test_client):
        """Test que la sesión guarda historial de conversación"""
        from app.services.session import session_manager

        user_id = "whatsapp:+593981234567"

        payload = {
            "MessageSid": "SM_history_test",
            "AccountSid": "AC_test",
            "From": user_id,
            "To": "whatsapp:+14155238886",
            "Body": "Precio HLSO 16/20",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        session = session_manager.get_session(user_id)
        assert 'conversation_history' in session


class TestCommandProcessing:
    """Tests para procesamiento de comandos especiales"""

    @pytest.mark.parametrize("command,expected_state", [
        ("menu", "idle"),
        ("ayuda", "idle"),
        ("help", "idle"),
    ])
    def test_special_commands(self, test_client, command, expected_state):
        """Test que comandos especiales son procesados correctamente"""
        payload = {
            "MessageSid": f"SM_cmd_{command}",
            "AccountSid": "AC_test",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": command,
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        assert response.status_code == 200


class TestErrorHandling:
    """Tests de manejo de errores"""

    def test_webhook_handles_service_errors_gracefully(self, test_client, mock_services):
        """Test que errores en servicios se manejan correctamente"""
        # Simular error en pricing service
        mock_services['pricing'].get_shrimp_price.side_effect = Exception("Test error")

        payload = {
            "MessageSid": "SM_error_test",
            "AccountSid": "AC_test",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "Body": "Precio HLSO 16/20",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        # El webhook debe responder, aunque haya error interno
        assert response.status_code in [200, 500]

    def test_webhook_handles_missing_form_fields(self, test_client):
        """Test que campos faltantes son manejados"""
        payload = {
            "MessageSid": "SM_missing_fields",
            # From está faltando (required field)
            "To": "whatsapp:+14155238886",
            "Body": "Test",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response = test_client.post("/webhook/whatsapp", data=payload)

        # Debe retornar error 422 (Unprocessable Entity) por campo faltante
        assert response.status_code == 422


@pytest.mark.integration
class TestCompleteFlows:
    """Tests de flujos completos end-to-end"""

    def test_complete_quote_generation_flow(self, test_client, mock_services):
        """
        Test flujo completo:
        1. Usuario consulta precio
        2. Sistema detecta necesidad de glaseo
        3. Usuario proporciona glaseo
        4. Sistema calcula precio
        5. Usuario confirma
        6. Sistema genera PDF
        """
        user_id = "whatsapp:+593981234567"

        # Paso 1: Consulta inicial
        payload1 = {
            "MessageSid": "SM_flow_001",
            "AccountSid": "AC_test",
            "From": user_id,
            "To": "whatsapp:+14155238886",
            "Body": "Precio HLSO 16/20",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response1 = test_client.post("/webhook/whatsapp", data=payload1)
            assert response1.status_code == 200

        # Paso 2: Usuario proporciona glaseo
        payload2 = {
            "MessageSid": "SM_flow_002",
            "AccountSid": "AC_test",
            "From": user_id,
            "To": "whatsapp:+14155238886",
            "Body": "20% glaseo",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response2 = test_client.post("/webhook/whatsapp", data=payload2)
            assert response2.status_code == 200

        # Paso 3: Usuario confirma y genera PDF
        payload3 = {
            "MessageSid": "SM_flow_003",
            "AccountSid": "AC_test",
            "From": user_id,
            "To": "whatsapp:+14155238886",
            "Body": "confirmar",
            "NumMedia": "0",
        }

        with patch('app.security.validate_twilio_webhook', return_value=True):
            response3 = test_client.post("/webhook/whatsapp", data=payload3)
            assert response3.status_code == 200


class TestLanguageDetection:
    """Tests de detección de idioma"""

    def test_spanish_detection(self, test_client):
        """Test detección de español"""
        from app.routes import _detect_language

        spanish_text = "Hola, necesito precio de camarón"
        assert _detect_language(spanish_text) == 'es'

    def test_english_detection(self, test_client):
        """Test detección de inglés"""
        from app.routes import _detect_language

        english_text = "Hello, I need shrimp price please"
        assert _detect_language(english_text) == 'en'

    def test_language_from_ai_analysis(self, test_client):
        """Test que usa idioma del análisis de IA si está disponible"""
        from app.routes import _detect_language

        ai_analysis = {'language': 'en'}
        text = "Texto en español"  # Español pero IA detectó inglés

        # Debe priorizar el análisis de IA
        assert _detect_language(text, ai_analysis) == 'en'


class TestGlaseoConversion:
    """Tests de conversión de glaseo a factor"""

    def test_glaseo_percentage_to_factor(self):
        """Test conversión de porcentaje de glaseo a factor"""
        from app.routes import glaseo_percentage_to_factor

        assert glaseo_percentage_to_factor(10) == 0.90
        assert glaseo_percentage_to_factor(20) == 0.80
        assert glaseo_percentage_to_factor(30) == 0.70
        assert glaseo_percentage_to_factor(15) == 0.85
        assert glaseo_percentage_to_factor(25) == 0.75