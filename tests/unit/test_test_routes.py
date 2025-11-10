"""
Tests para rutas de prueba y debugging
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestTestRoutes:
    """Tests para endpoints de prueba"""

    @pytest.fixture
    def admin_headers(self):
        """Headers de autenticación de admin"""
        return {"Authorization": "Bearer test_admin_token"}

    def test_test_webhook_returns_xml(self, client):
        """POST /test retorna XML válido"""
        response = client.post("/webhook/test")
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "Mensaje de prueba desde ShrimpBot" in response.text
        assert "<?xml" in response.text or "<Response>" in response.text

    def test_simple_webhook_returns_success(self, client):
        """POST /simple retorna mensaje de éxito"""
        payload = {
            "Body": "Test message",
            "From": "whatsapp:+593981234567",
            "To": "whatsapp:+14155238886",
            "MessageSid": "SM123456"
        }
        response = client.post("/webhook/simple", data=payload)
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "Mensaje recibido correctamente" in response.text

    def test_test_response_returns_xml(self, client):
        """POST /test-response retorna XML válido"""
        response = client.post("/webhook/test-response")
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "Mensaje de prueba desde BGR Export Bot" in response.text

    def test_test_twilio_without_auth(self, client):
        """GET /test-twilio sin autenticación debe fallar"""
        response = client.get("/webhook/test-twilio")
        assert response.status_code == 403

    @patch('app.routes.test_routes.Client')
    def test_test_twilio_with_valid_credentials(self, mock_client, client, admin_headers):
        """GET /test-twilio con credenciales válidas"""
        # Mock de cliente Twilio
        mock_account = MagicMock()
        mock_account.friendly_name = "Test Account"
        mock_account.status = "active"

        mock_client_instance = MagicMock()
        mock_client_instance.api.accounts.return_value.fetch.return_value = mock_account
        mock_client.return_value = mock_client_instance

        response = client.get("/webhook/test-twilio", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["account_name"] == "Test Account"
        assert data["account_status"] == "active"

    def test_test_pdf_send_without_auth(self, client):
        """POST /test-pdf-send sin autenticación debe fallar"""
        response = client.post("/webhook/test-pdf-send", data={"phone_number": "+593981234567"})
        assert response.status_code == 403

    @patch('app.routes.test_routes.get_services')
    def test_test_pdf_send_with_valid_phone(self, mock_get_services, client, admin_headers):
        """POST /test-pdf-send con número válido genera y envía PDF"""
        # Mock de servicios
        mock_pdf_generator = MagicMock()
        mock_pdf_generator.generate_quote_pdf.return_value = "/tmp/test_quote.pdf"

        mock_whatsapp_sender = MagicMock()
        mock_whatsapp_sender.send_pdf_document.return_value = True

        mock_get_services.return_value = (
            MagicMock(),  # pricing_service
            MagicMock(),  # interactive_service
            mock_pdf_generator,
            mock_whatsapp_sender,
            MagicMock()   # openai_service
        )

        response = client.post(
            "/webhook/test-pdf-send",
            data={"phone_number": "+593981234567"},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["pdf_generated"] is True
        assert data["pdf_sent_whatsapp"] is True

    def test_test_pdf_send_with_invalid_phone(self, client, admin_headers):
        """POST /test-pdf-send con número inválido debe fallar"""
        response = client.post(
            "/webhook/test-pdf-send",
            data={"phone_number": "invalid"},
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "Invalid phone number format" in response.json()["detail"]