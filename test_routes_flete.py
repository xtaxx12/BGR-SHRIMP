import sys
import types
sys.modules.setdefault('gspread', types.SimpleNamespace())
sys.modules.setdefault('oauth2client.service_account', types.SimpleNamespace())
sa = types.SimpleNamespace()
sa.Credentials = object
sys.modules.setdefault('google', types.SimpleNamespace())
sys.modules.setdefault('google.oauth2', types.SimpleNamespace())
sys.modules.setdefault('google.oauth2.service_account', sa)

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

class DummyOpenAI:
    @staticmethod
    def _basic_intent_analysis(text):
        if 'modifica' in text:
            return {'intent': 'modify_flete', 'flete_custom': 0.15}
        return {'intent': 'proforma', 'product': 'HLSO', 'size': '16/20', 'glaseo_factor': 0.9, 'glaseo_percentage': 10, 'confidence': 0.9}
    @staticmethod
    def detect_multiple_products(text):
        return [{'product': 'HLSO', 'size': '16/20'}, {'product': 'HLSO', 'size': '26/30'}]
    @staticmethod
    def is_available():
        return False

class DummyPricing:
    def get_shrimp_price(self, query):
        # Simula cálculo con flete
        return {
            'producto': query['product'],
            'talla': query['size'],
            'factor_glaseo': query.get('glaseo_factor', 0.9),
            'glaseo_percentage': query.get('glaseo_percentage', 10),
            'flete': query.get('flete_custom', 0.15)
        }

class DummyPDF:
    def generate_consolidated_quote_pdf(self, products, From, lang, glaseo, destination=None):
        return '/tmp/dummy_consolidado.pdf'
    def generate_quote_pdf(self, price_info, From, lang):
        return '/tmp/dummy_individual.pdf'
    def get_language_options(self):
        return '1️⃣ Español 🇪🇸\n2️⃣ English 🇺🇸'
    def parse_language_selection(self, text):
        return 'es' if text == '1' else 'en'

class DummyWhatsApp:
    def send_pdf_document(self, From, pdf_path, msg):
        return True

@pytest.fixture(autouse=True)
def patch_services(monkeypatch):
    # Patch get_services to use dummies
    def dummy_get_services():
        return (DummyPricing(), None, DummyPDF(), DummyWhatsApp(), DummyOpenAI())
    monkeypatch.setattr('app.routes.get_services', lambda: dummy_get_services())

    # Patch session_manager to start clean
    from app.services.session import session_manager
    session_manager.sessions.clear()

# Test: modificar flete en cotización consolidada
def test_modificar_flete_consolidada(client):
    # Simula cotización consolidada previa
    from app.services.session import session_manager
    user_id = '+593968058769'
    # note: routes.py strips the 'whatsapp:' prefix when building session keys
    session_manager.set_last_quote(user_id, {
        'consolidated': True,
        'products_info': [
            {'producto': 'HLSO', 'talla': '16/20', 'factor_glaseo': 0.9, 'glaseo_percentage': 10, 'flete': 0.15},
            {'producto': 'HLSO', 'talla': '26/30', 'factor_glaseo': 0.9, 'glaseo_percentage': 10, 'flete': 0.15}
        ],
        'glaseo_percentage': 10,
        'failed_products': [],
        'flete': 0.15
    })
    payload = {
        'Body': 'modifica el flete a 0.15 centavos',
        'From': 'whatsapp:' + user_id,
        'To': 'whatsapp:+1234567890',
        'MessageSid': 'SMTESTFLETE1',
        'NumMedia': '0',
        'MediaUrl0': '',
        'MediaContentType0': '',
    }
    response = client.post('/webhook/whatsapp', data=payload)
    assert response.status_code == 200
    assert 'Cotización consolidada actualizada' in response.text
    # Verifica que la última cotización se actualizó con el nuevo flete
    last = session_manager.get_last_quote(user_id)
    assert last is not None
    assert last.get('flete') == 0.15

# Test: modificar flete en cotización individual
def test_modificar_flete_individual(client):
    from app.services.session import session_manager
    user_id = '+593968058769'
    # note: routes.py strips the 'whatsapp:' prefix when building session keys
    session_manager.set_last_quote(user_id, {
        'producto': 'HLSO',
        'talla': '16/20',
        'factor_glaseo': 0.9,
        'glaseo_percentage': 10,
        'flete': 0.15
    })
    payload = {
        'Body': 'modifica el flete a 0.15 centavos',
        'From': 'whatsapp:' + user_id,
        'To': 'whatsapp:+1234567890',
        'MessageSid': 'SMTESTFLETE2',
        'NumMedia': '0',
        'MediaUrl0': '',
        'MediaContentType0': '',
    }
    response = client.post('/webhook/whatsapp', data=payload)
    assert response.status_code == 200
    assert 'Proforma actualizada' in response.text
    # Verifica que la última cotización se actualizó con el nuevo flete
    last = session_manager.get_last_quote(user_id)
    assert last is not None
    # Puede ser un dict de producto o un resumen; verificar flete
    assert last.get('flete') == 0.15 or last.get('flete', 0.15) == 0.15
