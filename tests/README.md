# Tests Documentation

Este directorio contiene la suite de tests completa para BGR-SHRIMP Bot.

## Estructura

```
tests/
├── conftest.py          # Fixtures compartidas y configuración pytest
├── unit/                # Tests unitarios (rápidos, aislados)
│   └── test_pricing_service.py
├── integration/         # Tests de integración (más lentos)
│   └── test_webhook.py
├── fixtures/            # Datos de prueba
└── mocks/              # Objetos mock reutilizables
```

## Ejecutar Tests

### Todos los tests
```bash
pytest
```

### Solo tests unitarios
```bash
pytest tests/unit/ -v
```

### Solo tests de integración
```bash
pytest tests/integration/ -v
```

### Tests específicos por marker
```bash
pytest -m unit          # Solo unitarios
pytest -m integration   # Solo integración
pytest -m pricing       # Solo pricing
pytest -m webhook       # Solo webhook
```

### Con coverage
```bash
pytest --cov=app --cov-report=html
```

### Tests en paralelo (más rápido)
```bash
pytest -n auto
```

## Escribir Tests

### Test Unitario Ejemplo

```python
def test_calculate_price():
    """Test calculation logic"""
    service = PricingService()
    result = service.calculate_final_price(
        base_price=8.55,
        fixed_cost=1.50,
        glaseo_factor=0.80,
        freight=0.35
    )
    assert result == 7.49
```

### Test de Integración Ejemplo

```python
def test_webhook_endpoint(test_client):
    """Test webhook receives messages"""
    payload = {
        "From": "whatsapp:+593981234567",
        "Body": "Precio HLSO 16/20",
        "MessageSid": "SM123"
    }
    response = test_client.post("/webhook/whatsapp", data=payload)
    assert response.status_code == 200
```

## Fixtures Disponibles

- `test_client`: Cliente HTTP para testing FastAPI
- `mock_google_sheets_service`: Mock de Google Sheets
- `mock_excel_service`: Mock de Excel local
- `mock_session_manager`: Mock del gestor de sesiones
- `mock_whatsapp_sender`: Mock del cliente WhatsApp
- `mock_pdf_generator`: Mock del generador de PDFs
- `sample_pricing_data`: Datos de ejemplo para tests
- `sample_webhook_payload`: Payload de ejemplo de Twilio

## Markers

- `@pytest.mark.unit`: Test unitario
- `@pytest.mark.integration`: Test de integración
- `@pytest.mark.slow`: Test lento
- `@pytest.mark.security`: Test de seguridad
- `@pytest.mark.pricing`: Test de pricing
- `@pytest.mark.webhook`: Test de webhook

## Coverage

Objetivo: **80% de cobertura** en módulos críticos

Ver reporte:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## CI/CD

Los tests se ejecutan automáticamente en:
- Cada push a `main` o `develop`
- Cada pull request
- GitHub Actions workflow: `.github/workflows/ci.yml`

## Troubleshooting

### Tests fallan por dependencias
```bash
pip install -r requirements-dev.txt
```

### Tests fallan por variables de entorno
Asegúrate de tener un `.env` válido o usar el modo testing.

### Limpiar caché
```bash
pytest --cache-clear
rm -rf .pytest_cache __pycache__
```