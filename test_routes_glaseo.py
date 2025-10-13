import sys
import types
import pytest
from fastapi.testclient import TestClient

# Insert dummy modules for external dependencies that may not be installed in the test environment
sys.modules.setdefault('gspread', types.SimpleNamespace())
sys.modules.setdefault('oauth2client.service_account', types.SimpleNamespace())
sys.modules.setdefault('google', types.SimpleNamespace())
sys.modules.setdefault('google.oauth2', types.SimpleNamespace())
sa = types.SimpleNamespace()
sa.Credentials = object
sys.modules.setdefault('google.oauth2.service_account', sa)

from app.main import app

# Test que simula un POST desde Twilio con múltiples productos y sin glaseo

def test_multi_products_without_glaseo_prompts_for_glaseo(monkeypatch):
    client = TestClient(app)

    # Mensaje de usuario (el del reporte) sin glaseo
    body = """
Precios para esto por favor ..

HOSO 50-60 block 10x4

HLSO 16-20 block 10x4

HLSO 26-30 block 10x4

HLSO 36-40 block 10x4

HLSO 51-60 block 10x4

PYD TAIL OFF 61-70 IQF 5X2

16-20 EZPEEL IQF 10X2

26-30 EZPEEL IQF 10X2

DDP LA or Houston
"""

    # Mock de openai_service para forzar detección de múltiples productos
    class DummyOpenAI:
        @staticmethod
        def _basic_intent_analysis(text):
            return {
                'intent': 'proforma',
                'product': 'P&D BLOQUE',
                'size': '50/60',
                'glaseo_factor': None,
                'glaseo_percentage': None,
                'confidence': 0.9,
            }

        @staticmethod
        def detect_multiple_products(text):
            # Devolver una lista de productos detectados
            return [
                {'product': 'HOSO', 'size': '50/60'},
                {'product': 'HLSO', 'size': '16/20'}
            ]

        @staticmethod
        def is_available():
            return False

    # Mock simple para pricing_service que no hace real cálculo
    class DummyPricing:
        def get_shrimp_price(self, query):
            # Si se llama con glaseo, devolver algo
            if query.get('glaseo_factor'):
                return {'producto': query['product'], 'talla': query['size'], 'factor_glaseo': query['glaseo_factor']}
            return None

    # Forzar get_services para devolver servicios dummy
    def dummy_get_services():
        return (DummyPricing(), None, None, None, DummyOpenAI())

    monkeypatch.setattr('app.routes.get_services', lambda: dummy_get_services())

    payload = {
        'Body': body,
        'From': 'whatsapp:+593968058769',
        'To': 'whatsapp:+1234567890',
        'MessageSid': 'SMTEST12345',
        'NumMedia': '0',
        'MediaUrl0': '',
        'MediaContentType0': '',
    }

    response = client.post('/webhook/whatsapp', data=payload)

    assert response.status_code == 200
    text = response.text

    # Debe pedir glaseo porque el análisis identifica múltiples productos sin glaseo
    assert '¿Qué glaseo necesitas' in text or '¿Qué porcentaje de glaseo' in text or '¿Qué glaseo necesitas para todos los productos' in text
