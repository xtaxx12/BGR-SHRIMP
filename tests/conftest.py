"""
Configuración compartida de pytest y fixtures globales
"""
import os
import sys
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

# Agregar el directorio raíz al path para imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configurar variables de entorno para testing
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "test_sid")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_token")
os.environ.setdefault("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing_only")
os.environ.setdefault("ADMIN_API_TOKEN", "test_admin_token")


@pytest.fixture(scope="session")
def test_env_vars():
    """Variables de entorno para testing"""
    return {
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        "TWILIO_ACCOUNT_SID": "test_sid",
        "TWILIO_AUTH_TOKEN": "test_token",
    }


@pytest.fixture
def mock_google_sheets_service():
    """Mock del servicio de Google Sheets"""
    mock = MagicMock()

    # Mock data típica
    mock.get_price_data.return_value = {
        'precio_kg': 8.55,
        'talla': '16/20',
        'producto': 'HLSO',
        'stock': 5000
    }

    mock.get_costo_fijo_value.return_value = 1.50
    mock.get_flete_value.return_value = 0.35
    mock.is_available.return_value = True

    return mock


@pytest.fixture
def mock_excel_service():
    """Mock del servicio de Excel local"""
    mock = MagicMock()

    mock.get_price_data.return_value = {
        'precio_kg': 8.55,
        'talla': '16/20',
        'producto': 'HLSO',
    }

    return mock


@pytest.fixture
def mock_session_manager():
    """Mock del gestor de sesiones"""
    mock = MagicMock()

    def get_session(user_id: str) -> Dict[str, Any]:
        return {
            'state': 'idle',
            'data': {},
            'conversation_history': [],
            'last_activity': 0
        }

    mock.get_session.side_effect = get_session
    mock.update_session.return_value = None
    mock.clear_session.return_value = None

    return mock


@pytest.fixture
def mock_whatsapp_sender():
    """Mock del servicio de envío de WhatsApp"""
    mock = MagicMock()
    mock.send_message.return_value = {"sid": "test_message_sid"}
    mock.send_media.return_value = {"sid": "test_media_sid"}
    return mock


@pytest.fixture
def mock_pdf_generator():
    """Mock del generador de PDFs"""
    mock = MagicMock()
    mock.generate_quote_pdf.return_value = "/tmp/test_quote.pdf"
    return mock


@pytest.fixture
def sample_pricing_data() -> Dict[str, Any]:
    """Datos de ejemplo para tests de pricing"""
    return {
        'base_price_kg': 8.55,
        'size': '16/20',
        'product': 'HLSO',
        'user_params': {
            'glaseo_factor': 0.8,
            'glaseo_percentage': 20,
            'flete_custom': None,
            'flete_solicitado': True,
            'usar_libras': False,
            'destination': None
        }
    }


@pytest.fixture
def sample_webhook_payload() -> Dict[str, str]:
    """Payload de ejemplo de webhook de Twilio"""
    return {
        "MessageSid": "SM1234567890abcdef",
        "AccountSid": "AC1234567890abcdef",
        "From": "whatsapp:+593981234567",
        "To": "whatsapp:+14155238886",
        "Body": "Precio HLSO 16/20",
        "NumMedia": "0",
    }


@pytest.fixture
def sample_audio_webhook_payload() -> Dict[str, str]:
    """Payload de webhook con audio"""
    return {
        "MessageSid": "SM1234567890abcdef",
        "AccountSid": "AC1234567890abcdef",
        "From": "whatsapp:+593981234567",
        "To": "whatsapp:+14155238886",
        "Body": "",
        "NumMedia": "1",
        "MediaContentType0": "audio/ogg",
        "MediaUrl0": "https://api.twilio.com/test-audio.ogg",
    }


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Cliente de test para FastAPI"""
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons entre tests"""
    # Limpiar caché de ServiceContainer si existe
    from app.dependencies import get_service_container
    get_service_container.cache_clear()

    yield

    # Cleanup después del test
    get_service_container.cache_clear()


@pytest.fixture
def mock_openai_service():
    """Mock del servicio de OpenAI"""
    mock = MagicMock()
    mock.detect_products_and_intent.return_value = {
        'products': [{'producto': 'HLSO', 'talla': '16/20'}],
        'intent': 'consulta_precio',
        'requires_glaseo': True,
        'requires_flete': False
    }
    mock.transcribe_audio.return_value = "Precio HLSO 16/20"
    return mock
