# Manual Técnico - BGR Shrimp Bot v2.0

## Tabla de Contenidos

1. [Arquitectura del Sistema](#arquitectura-del-sistema)
2. [Componentes Principales](#componentes-principales)
3. [Estructura del Código](#estructura-del-código)
4. [Patrones de Diseño](#patrones-de-diseño)
5. [Configuración](#configuración)
6. [Base de Datos y Almacenamiento](#base-de-datos-y-almacenamiento)
7. [Integraciones Externas](#integraciones-externas)
8. [Seguridad](#seguridad)
9. [Logging y Monitoreo](#logging-y-monitoreo)
10. [Deployment](#deployment)

---

## Arquitectura del Sistema

### Visión General

BGR Shrimp Bot es una aplicación web basada en FastAPI que procesa webhooks de Twilio para WhatsApp Business. La arquitectura sigue principios de diseño modular con separación de responsabilidades.

### Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTE                              │
│                    (WhatsApp User)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    TWILIO API                               │
│              (WhatsApp Business API)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼ Webhook (HTTPS)
┌─────────────────────────────────────────────────────────────┐
│                   BGR SHRIMP BOT                            │
│                    (FastAPI App)                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              CAPA DE PRESENTACIÓN                    │  │
│  │  - Webhook Handler                                   │  │
│  │  - Request Validation                                │  │
│  │  - Response Formatting                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              CAPA DE NEGOCIO                         │  │
│  │  - Pricing Service                                   │  │
│  │  - OpenAI Service                                    │  │
│  │  - PDF Generator                                     │  │
│  │  - Session Manager                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              CAPA DE DATOS                           │  │
│  │  - Google Sheets Service                             │  │
│  │  - Excel Service                                     │  │
│  │  - File Storage                                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Google     │ │   OpenAI     │ │   Twilio     │
│   Sheets     │ │     API      │ │     API      │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Stack Tecnológico

**Backend Framework:**
- Python 3.11+
- FastAPI 0.104+
- Uvicorn (ASGI server)
- Pydantic (Data validation)

**Servicios Externos:**
- Twilio WhatsApp Business API
- Google Sheets API v4
- OpenAI GPT-4 API

**Librerías Principales:**
- `gspread` - Google Sheets integration
- `openpyxl` - Excel file processing
- `reportlab` - PDF generation
- `twilio` - Twilio SDK
- `openai` - OpenAI SDK

**Infraestructura:**
- Render.com (Hosting)
- HTTPS/TLS (Security)
- JSON file storage (Sessions)


---

## Componentes Principales

### 1. Main Application (`app/main.py`)

**Responsabilidad:** Punto de entrada de la aplicación, configuración de middlewares y lifecycle management.

**Características:**
- Configuración de FastAPI con lifespan context
- Middlewares de CORS y TrustedHost
- Request logging con IDs únicos
- Exception handlers globales
- Health check y metrics endpoints

**Endpoints del Sistema:**
```python
GET  /              # Root endpoint con info del sistema
GET  /health        # Health check con status de componentes
GET  /metrics       # Métricas básicas (solo en debug)
```

### 2. Routes (`app/routes.py`)

**Responsabilidad:** Manejo de webhooks de Twilio y lógica de procesamiento de mensajes.

**Endpoints Principales:**
```python
POST /webhook/whatsapp           # Webhook principal de Twilio
POST /webhook/reload-data        # Recarga datos de Google Sheets
GET  /webhook/data-status        # Estado de fuentes de datos
GET  /webhook/test-twilio        # Test de conectividad Twilio
GET  /webhook/download-pdf/{fn}  # Descarga de PDFs generados
```

**Flujo de Procesamiento:**
1. Validación de webhook Twilio
2. Rate limiting por usuario
3. Sanitización de entrada
4. Detección de duplicados
5. Procesamiento de audio (si aplica)
6. Análisis de intención con IA
7. Ejecución de lógica de negocio
8. Generación de respuesta

### 3. Pricing Service (`app/services/pricing.py`)

**Responsabilidad:** Lógica central de cálculo de precios y cotizaciones.

**Métodos Principales:**
```python
get_shrimp_price(query: dict) -> dict
    # Calcula precio basado en producto, talla, glaseo, flete
    
validate_product(product: str) -> bool
    # Valida que el producto existe
    
validate_size(size: str) -> bool
    # Valida que la talla existe
    
calculate_fob_price(product, size) -> float
    # Calcula precio FOB base
    
calculate_cfr_price(fob, glaseo_factor) -> float
    # Calcula precio CFR con glaseo
    
calculate_ddp_price(cfr, flete) -> float
    # Calcula precio DDP con flete
```

**Productos Soportados:**
- HOSO, HLSO, P&D IQF, P&D BLOQUE
- EZ PEEL, PuD-EUROPA, PuD-EEUU, COOKED

**Tallas Soportadas:**
- U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40
- 40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90

### 4. OpenAI Service (`app/services/openai_service.py`)

**Responsabilidad:** Integración con OpenAI para análisis de intención y transcripción.

**Métodos Principales:**
```python
analyze_user_intent(message: str, session: dict) -> dict
    # Analiza intención del usuario con GPT-4
    
_basic_intent_analysis(message: str) -> dict
    # Análisis rápido sin IA (fallback)
    
transcribe_audio(audio_path: str) -> str
    # Transcribe audio con Whisper API
    
detect_multiple_products(message: str) -> list
    # Detecta múltiples productos en un mensaje
```

**Intenciones Detectadas:**
- `greeting` - Saludo
- `price_query` - Consulta de precio
- `proforma` - Solicitud de proforma
- `modify_flete` - Modificar flete
- `menu_request` - Solicitud de menú
- `help` - Ayuda

### 5. PDF Generator (`app/services/pdf_generator.py`)

**Responsabilidad:** Generación de proformas en PDF con formato profesional.

**Métodos Principales:**
```python
generate_quote_pdf(price_info: dict, phone: str, language: str) -> str
    # Genera PDF de cotización individual
    
generate_consolidated_quote_pdf(products: list, phone: str, 
                                language: str, glaseo: int) -> str
    # Genera PDF consolidado con múltiples productos
```

**Características:**
- Soporte multiidioma (ES/EN)
- Logo de BGR Export
- Información detallada de producto
- Cálculos de FOB, CFR, DDP
- Términos y condiciones
- Información de contacto

### 6. Session Manager (`app/services/session.py`)

**Responsabilidad:** Gestión de sesiones de usuario y estado conversacional.

**Métodos Principales:**
```python
get_session(user_id: str) -> dict
    # Obtiene sesión del usuario
    
set_session_state(user_id: str, state: str, data: dict)
    # Establece estado de sesión
    
get_last_quote(user_id: str) -> dict
    # Obtiene última cotización
    
set_last_quote(user_id: str, quote: dict)
    # Guarda última cotización
    
clear_session(user_id: str)
    # Limpia sesión del usuario
```

**Estados de Sesión:**
- `idle` - Sin operación activa
- `waiting_for_glaseo` - Esperando porcentaje de glaseo
- `waiting_for_flete` - Esperando valor de flete
- `waiting_for_multi_glaseo` - Glaseo para múltiples productos
- `waiting_for_multi_flete` - Flete para múltiples productos
- `waiting_for_multi_language` - Idioma para cotización consolidada

### 7. Google Sheets Service (`app/services/google_sheets.py`)

**Responsabilidad:** Integración con Google Sheets para datos en tiempo real.

**Métodos Principales:**
```python
get_price_data() -> dict
    # Obtiene todos los precios de Google Sheets
    
get_product_price(product: str, size: str) -> float
    # Obtiene precio específico
    
get_flete_data() -> dict
    # Obtiene datos de flete por destino
    
reload_data()
    # Recarga datos desde Google Sheets
```

**Estructura de Sheets:**
- Hoja "Precios": Productos, tallas y precios FOB
- Hoja "Flete": Destinos y costos de flete
- Hoja "Inventario": Disponibilidad de productos

### 8. WhatsApp Sender (`app/services/whatsapp_sender.py`)

**Responsabilidad:** Envío de mensajes y documentos por WhatsApp.

**Métodos Principales:**
```python
send_message(to: str, body: str) -> bool
    # Envía mensaje de texto
    
send_pdf_document(to: str, pdf_path: str, caption: str) -> bool
    # Envía documento PDF
    
send_media(to: str, media_url: str, caption: str) -> bool
    # Envía archivo multimedia
```


---

## Estructura del Código

### Organización de Directorios

```
BGR-SHRIMP/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Aplicación FastAPI principal
│   ├── routes.py               # Endpoints y webhooks
│   ├── config.py               # Configuración centralizada
│   ├── dependencies.py         # Inyección de dependencias
│   ├── security.py             # Utilidades de seguridad
│   ├── exceptions.py           # Excepciones personalizadas
│   ├── logging_config.py       # Configuración de logging
│   └── services/
│       ├── __init__.py
│       ├── pricing.py          # Lógica de precios
│       ├── openai_service.py   # Integración OpenAI
│       ├── pdf_generator.py    # Generación de PDFs
│       ├── session.py          # Gestión de sesiones
│       ├── google_sheets.py    # Integración Google Sheets
│       ├── excel.py            # Procesamiento Excel
│       ├── whatsapp_sender.py  # Cliente Twilio
│       ├── audio_handler.py    # Procesamiento de audio
│       ├── interactive.py      # Menús interactivos
│       ├── utils.py            # Utilidades generales
│       └── utils_new.py        # Utilidades adicionales
├── data/
│   ├── CALCULO_DE_PRECIOS-AGUAJE17.xlsx  # Excel de precios
│   ├── directorio de clientes.xls        # Directorio clientes
│   ├── logoBGR.png                       # Logo para PDFs
│   └── sessions.json                     # Sesiones de usuario
├── generated_pdfs/             # PDFs generados
├── logs/                       # Archivos de log
│   ├── app.log                 # Log general
│   ├── errors.log              # Errores
│   ├── security.log            # Eventos de seguridad
│   └── business.log            # Métricas de negocio
├── scripts/                    # Scripts de utilidad
│   ├── master_validation.py    # Validación completa
│   ├── pre_deploy_checklist.py # Checklist pre-despliegue
│   ├── validate_critical_points.py # Validación de puntos críticos
│   └── generate_quality_certificate.py # Certificado de calidad
├── tests/                      # Suite de pruebas
│   ├── test_quality_assurance.py
│   ├── test_flexible_glaseo.py
│   ├── test_consolidated_quote.py
│   ├── test_session_preservation.py
│   └── ...
├── docs/                       # Documentación
│   └── entrega/                # Documentos de entrega
├── .env                        # Variables de entorno (no en git)
├── .env.example                # Ejemplo de variables
├── requirements.txt            # Dependencias Python
├── Procfile                    # Configuración Heroku
├── render.yaml                 # Configuración Render
├── railway.json                # Configuración Railway
└── README.MD                   # Documentación principal
```

### Convenciones de Código

**Estilo:**
- PEP 8 para Python
- Type hints en todas las funciones
- Docstrings para clases y métodos públicos
- Nombres descriptivos en español para variables de negocio

**Ejemplo:**
```python
def calculate_cfr_price(
    fob_price: float,
    glaseo_factor: float,
    producto: str
) -> float:
    """
    Calcula el precio CFR aplicando el factor de glaseo.
    
    Args:
        fob_price: Precio FOB base
        glaseo_factor: Factor de glaseo (0.70-0.90)
        producto: Nombre del producto
        
    Returns:
        Precio CFR calculado
        
    Raises:
        ValueError: Si el glaseo_factor está fuera de rango
    """
    if not 0.70 <= glaseo_factor <= 0.90:
        raise ValueError(f"Glaseo factor inválido: {glaseo_factor}")
        
    cfr_price = fob_price / glaseo_factor
    logger.info(f"CFR calculado para {producto}: ${cfr_price:.2f}")
    
    return round(cfr_price, 2)
```

---

## Patrones de Diseño

### 1. Service Layer Pattern

Separación de lógica de negocio en servicios independientes:

```python
# Cada servicio es una clase con responsabilidad única
class PricingService:
    def __init__(self):
        self.excel_service = ExcelService()
        self.google_sheets_service = GoogleSheetsService()
        
    def get_shrimp_price(self, query: dict) -> dict:
        # Lógica de negocio aislada
        pass
```

### 2. Dependency Injection

Servicios se inicializan de manera lazy y se comparten:

```python
# Global service instances
pricing_service = None
openai_service = None

def get_services():
    global pricing_service, openai_service
    if pricing_service is None:
        pricing_service = PricingService()
        openai_service = OpenAIService()
    return pricing_service, openai_service
```

### 3. Strategy Pattern

Diferentes estrategias para obtener datos (Google Sheets vs Excel):

```python
class PricingService:
    def _get_price_from_source(self, product, size):
        # Intenta Google Sheets primero
        try:
            return self.google_sheets_service.get_price(product, size)
        except Exception:
            # Fallback a Excel local
            return self.excel_service.get_price(product, size)
```

### 4. State Pattern

Gestión de estados conversacionales:

```python
session = {
    'state': 'waiting_for_glaseo',
    'data': {
        'ai_query': {...},
        'timestamp': ...
    }
}

# Diferentes handlers según el estado
if session['state'] == 'waiting_for_glaseo':
    handle_glaseo_response(message)
elif session['state'] == 'waiting_for_flete':
    handle_flete_response(message)
```

### 5. Decorator Pattern

Decoradores para seguridad y rate limiting:

```python
@rate_limit(lambda req, **kwargs: kwargs.get('From', 'unknown'))
async def whatsapp_webhook(request: Request, From: str = Form(...)):
    # Endpoint protegido con rate limiting
    pass
```

### 6. Retry Pattern

Reintentos automáticos para operaciones críticas:

```python
def retry(func, retries=3, delay=0.5, args=(), kwargs={}):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
```

---

## Configuración

### Variables de Entorno

**Archivo `.env`:**

```bash
# Twilio Configuration (REQUERIDO)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Security (REQUERIDO en producción)
SECRET_KEY=<genera-con-secrets.token_urlsafe(32)>
ADMIN_API_TOKEN=<token-seguro-para-admin>
ENVIRONMENT=production  # development/staging/production

# Google Sheets (RECOMENDADO)
GOOGLE_SHEETS_ID=1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account",...}'

# OpenAI (OPCIONAL)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Server Configuration
BASE_URL=https://tu-dominio.com
PORT=8000
DEBUG=false

# Security Settings
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
CORS_ORIGINS=https://tu-frontend.com
RATE_LIMIT_MAX_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60

# Limits
MAX_MESSAGE_LENGTH=1000
MAX_FILE_SIZE=10485760  # 10MB
REQUEST_TIMEOUT=30
PDF_GENERATION_TIMEOUT=60

# Data Sources
EXCEL_PATH=data/CALCULO_DE_PRECIOS-AGUAJE17.xlsx
```

### Configuración por Entorno

**Development:**
```bash
ENVIRONMENT=development
DEBUG=true
PORT=8000
BASE_URL=http://localhost:8000
```

**Staging:**
```bash
ENVIRONMENT=staging
DEBUG=false
PORT=8000
BASE_URL=https://staging.tu-dominio.com
```

**Production:**
```bash
ENVIRONMENT=production
DEBUG=false
PORT=8000
BASE_URL=https://tu-dominio.com
ALLOWED_HOSTS=tu-dominio.com
```

### Clase Settings

La configuración se centraliza en `app/config.py`:

```python
class Settings:
    # Carga automática desde .env
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    def validate(self):
        """Valida configuración crítica en producción"""
        if self.is_production:
            required = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "SECRET_KEY"]
            missing = [var for var in required if not getattr(self, var)]
            if missing:
                raise ValueError(f"Missing: {', '.join(missing)}")

settings = Settings()
```


---

## Base de Datos y Almacenamiento

### Sesiones de Usuario

**Archivo:** `data/sessions.json`

**Estructura:**
```json
{
  "user_id": {
    "state": "idle",
    "data": {},
    "last_quote": {
      "producto": "HLSO",
      "talla": "16/20",
      "precio_fob": 8.50,
      "precio_cfr": 9.20,
      "glaseo_percentage": 20,
      "timestamp": "2025-01-30T10:30:00"
    },
    "language": "es",
    "created_at": "2025-01-30T10:00:00",
    "updated_at": "2025-01-30T10:30:00"
  }
}
```

**Operaciones:**
- Lectura/escritura síncrona con lock
- Persistencia automática en cada cambio
- Limpieza de sesiones antiguas (> 24 horas)

### PDFs Generados

**Directorio:** `generated_pdfs/`

**Nomenclatura:**
```
cotizacion_BGR_{tipo}_{timestamp}_{user_id}.pdf
```

**Ejemplo:**
```
cotizacion_BGR_consolidada_20250130_115546_7425.pdf
```

**Gestión:**
- Limpieza automática de PDFs > 7 días
- Tamaño máximo por PDF: 5MB
- Formato: PDF/A para compatibilidad

### Datos de Precios

**Fuente Primaria:** Google Sheets  
**Fuente Secundaria:** Excel local (`data/CALCULO_DE_PRECIOS-AGUAJE17.xlsx`)

**Estructura de Datos:**
```python
{
    "HLSO": {
        "16/20": {
            "fob": 8.50,
            "disponible": true,
            "origen": "Ecuador"
        },
        "21/25": {
            "fob": 7.80,
            "disponible": true,
            "origen": "Ecuador"
        }
    }
}
```

### Logs

**Directorio:** `logs/`

**Archivos:**
- `app.log` - Log general de aplicación
- `errors.log` - Errores y excepciones
- `security.log` - Eventos de seguridad
- `business.log` - Métricas de negocio

**Rotación:**
- Rotación diaria automática
- Retención: 30 días
- Formato: JSON estructurado

---

## Integraciones Externas

### 1. Twilio WhatsApp Business API

**Documentación:** https://www.twilio.com/docs/whatsapp

**Configuración:**
```python
from twilio.rest import Client

client = Client(
    settings.TWILIO_ACCOUNT_SID,
    settings.TWILIO_AUTH_TOKEN
)
```

**Webhook Validation:**
```python
from twilio.request_validator import RequestValidator

validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
signature = request.headers.get('X-Twilio-Signature', '')
url = str(request.url)
params = await request.form()

is_valid = validator.validate(url, params, signature)
```

**Envío de Mensajes:**
```python
message = client.messages.create(
    from_=settings.TWILIO_WHATSAPP_NUMBER,
    body="Mensaje de texto",
    to="whatsapp:+593968058769"
)
```

**Envío de Documentos:**
```python
message = client.messages.create(
    from_=settings.TWILIO_WHATSAPP_NUMBER,
    body="Proforma adjunta",
    media_url=[pdf_url],
    to="whatsapp:+593968058769"
)
```

### 2. Google Sheets API

**Documentación:** https://developers.google.com/sheets/api

**Autenticación:**
```python
import gspread
from google.oauth2.service_account import Credentials

creds_dict = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS)
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)

client = gspread.authorize(creds)
sheet = client.open_by_key(settings.GOOGLE_SHEETS_ID)
```

**Lectura de Datos:**
```python
# Obtener hoja específica
worksheet = sheet.worksheet("Precios")

# Leer todos los valores
data = worksheet.get_all_records()

# Leer rango específico
values = worksheet.get('A1:D10')
```

**Manejo de Errores:**
```python
try:
    data = worksheet.get_all_records()
except gspread.exceptions.APIError as e:
    logger.error(f"Google Sheets API error: {e}")
    # Fallback a Excel local
    data = excel_service.get_data()
```

### 3. OpenAI API

**Documentación:** https://platform.openai.com/docs

**Configuración:**
```python
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)
```

**Análisis de Intención:**
```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ],
    temperature=0.3,
    max_tokens=500
)

analysis = json.loads(response.choices[0].message.content)
```

**Transcripción de Audio:**
```python
with open(audio_path, "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="es"
    )

text = transcript.text
```

**Fallback sin OpenAI:**
```python
def _basic_intent_analysis(message: str) -> dict:
    """Análisis básico sin IA para cuando OpenAI no está disponible"""
    message_lower = message.lower()
    
    # Detección de intención por palabras clave
    if any(word in message_lower for word in ['hola', 'buenos', 'hi', 'hello']):
        return {'intent': 'greeting', 'confidence': 0.9}
    
    if any(word in message_lower for word in ['precio', 'price', 'cotiza']):
        return {'intent': 'price_query', 'confidence': 0.8}
    
    # Extracción de entidades con regex
    product_match = re.search(r'\b(HLSO|HOSO|P&D IQF)\b', message, re.I)
    size_match = re.search(r'\b(\d+/\d+|U\d+)\b', message)
    
    return {
        'intent': 'price_query',
        'product': product_match.group(1) if product_match else None,
        'size': size_match.group(1) if size_match else None,
        'confidence': 0.7
    }
```

---

## Seguridad

### Validación de Webhooks

**Twilio Signature Validation:**
```python
def validate_twilio_webhook(request: Request) -> bool:
    """Valida que el request viene de Twilio"""
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    
    signature = request.headers.get('X-Twilio-Signature', '')
    url = str(request.url)
    params = dict(request.form())
    
    return validator.validate(url, params, signature)
```

**Uso en Endpoint:**
```python
@webhook_router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    if not validate_twilio_webhook(request):
        raise HTTPException(status_code=403, detail="Invalid signature")
    # Procesar webhook
```

### Rate Limiting

**Implementación:**
```python
from collections import defaultdict
import time

request_counts = defaultdict(list)

def rate_limit(get_key_func):
    def decorator(func):
        async def wrapper(request: Request, **kwargs):
            key = get_key_func(request, **kwargs)
            now = time.time()
            
            # Limpiar requests antiguos
            request_counts[key] = [
                t for t in request_counts[key]
                if now - t < settings.RATE_LIMIT_WINDOW_SECONDS
            ]
            
            # Verificar límite
            if len(request_counts[key]) >= settings.RATE_LIMIT_MAX_REQUESTS:
                raise HTTPException(status_code=429, detail="Too many requests")
            
            request_counts[key].append(now)
            return await func(request, **kwargs)
        return wrapper
    return decorator
```

**Uso:**
```python
@rate_limit(lambda req, **kwargs: kwargs.get('From', 'unknown'))
async def whatsapp_webhook(request: Request, From: str = Form(...)):
    # Limitado a 30 requests por minuto por usuario
    pass
```

### Sanitización de Entrada

**Función de Sanitización:**
```python
import re

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Limpia y valida entrada de usuario"""
    if not text:
        return ""
    
    # Limitar longitud
    text = text[:max_length]
    
    # Remover caracteres peligrosos
    text = re.sub(r'[<>\"\'`]', '', text)
    
    # Normalizar espacios
    text = ' '.join(text.split())
    
    return text.strip()
```

### Autenticación Bearer

**Para Endpoints Administrativos:**
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifica token de administrador"""
    if credentials.credentials != settings.ADMIN_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials
```

**Uso:**
```python
@webhook_router.post("/reload-data")
async def reload_data(token: str = Depends(verify_admin_token)):
    # Solo accesible con token válido
    pass
```

### Headers de Seguridad

**Middleware:**
```python
def add_security_headers(response: Response) -> Response:
    """Agrega headers de seguridad"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

### Manejo Seguro de Archivos

**Archivos Temporales:**
```python
import tempfile
import os

class SecureTempFile:
    """Context manager para archivos temporales seguros"""
    def __init__(self, suffix=""):
        self.suffix = suffix
        self.path = None
        
    def __enter__(self):
        fd, self.path = tempfile.mkstemp(suffix=self.suffix)
        os.close(fd)
        return self.path
        
    def __exit__(self, *args):
        if self.path and os.path.exists(self.path):
            os.remove(self.path)
```

**Uso:**
```python
with SecureTempFile(suffix=".ogg") as temp_path:
    # Descargar audio
    download_audio(url, temp_path)
    # Procesar
    transcription = transcribe_audio(temp_path)
    # Archivo se elimina automáticamente
```


---

## Logging y Monitoreo

### Sistema de Logging

**Configuración (`app/logging_config.py`):**

```python
import logging
import logging.handlers
import json
from datetime import datetime

def setup_logging():
    """Configura sistema de logging estructurado"""
    
    # Formato JSON para logs
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            # Agregar extra fields
            if hasattr(record, 'request_id'):
                log_data['request_id'] = record.request_id
            if hasattr(record, 'user_id'):
                log_data['user_id'] = record.user_id
                
            return json.dumps(log_data)
    
    # Handler para archivo general
    app_handler = logging.handlers.RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=30
    )
    app_handler.setFormatter(JSONFormatter())
    
    # Handler para errores
    error_handler = logging.handlers.RotatingFileHandler(
        'logs/errors.log',
        maxBytes=10485760,
        backupCount=30
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)
```

### Niveles de Log

**DEBUG:** Información detallada para debugging
```python
logger.debug(f"Procesando consulta: {query}")
```

**INFO:** Eventos normales del sistema
```python
logger.info(f"Cotización generada para usuario {user_id}")
```

**WARNING:** Situaciones inusuales pero manejables
```python
logger.warning(f"Google Sheets no disponible, usando Excel local")
```

**ERROR:** Errores que afectan funcionalidad
```python
logger.error(f"Error generando PDF: {str(e)}")
```

**CRITICAL:** Errores críticos del sistema
```python
logger.critical(f"No se puede conectar a Twilio: {str(e)}")
```

### Logging Estructurado

**Con Contexto:**
```python
logger.info(
    "Request procesado exitosamente",
    extra={
        'request_id': request_id,
        'user_id': user_id,
        'process_time': process_time,
        'status_code': 200
    }
)
```

**Filtrado de Datos Sensibles:**
```python
def sanitize_log_data(data: dict) -> dict:
    """Remueve datos sensibles de logs"""
    sensitive_keys = ['password', 'token', 'api_key', 'secret']
    
    sanitized = data.copy()
    for key in sensitive_keys:
        if key in sanitized:
            sanitized[key] = '***REDACTED***'
    
    return sanitized
```

### Métricas de Negocio

**Log de Eventos de Negocio:**
```python
business_logger = logging.getLogger('business')

# Cotización generada
business_logger.info(
    "quote_generated",
    extra={
        'user_id': user_id,
        'product': product,
        'size': size,
        'price_fob': price_fob,
        'price_cfr': price_cfr,
        'glaseo': glaseo_percentage
    }
)

# PDF generado
business_logger.info(
    "pdf_generated",
    extra={
        'user_id': user_id,
        'pdf_type': 'consolidated',
        'products_count': len(products),
        'language': language,
        'generation_time': generation_time
    }
)
```

### Health Checks

**Endpoint de Health:**
```python
@app.get("/health")
async def health_check():
    """Verifica salud del sistema"""
    health_status = {
        "status": "healthy",
        "service": "bgr-whatsapp-bot",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "twilio": check_twilio_connection(),
            "google_sheets": check_google_sheets_connection(),
            "openai": check_openai_connection(),
            "file_system": check_file_system()
        }
    }
    
    # Determinar status general
    if any(not status for status in health_status["components"].values()):
        health_status["status"] = "degraded"
    
    return health_status
```

**Checks de Componentes:**
```python
def check_twilio_connection() -> bool:
    """Verifica conectividad con Twilio"""
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
        return True
    except Exception as e:
        logger.error(f"Twilio health check failed: {e}")
        return False

def check_google_sheets_connection() -> bool:
    """Verifica conectividad con Google Sheets"""
    try:
        sheet = google_sheets_service.get_sheet()
        return sheet is not None
    except Exception as e:
        logger.error(f"Google Sheets health check failed: {e}")
        return False
```

### Monitoreo Externo

**Recomendaciones:**

1. **UptimeRobot** - Monitoreo de uptime
   - URL: https://uptimerobot.com
   - Configurar check cada 5 minutos
   - Alertas por email/SMS

2. **Sentry** - Error tracking
   - URL: https://sentry.io
   - Captura automática de excepciones
   - Stack traces completos

3. **LogDNA/Datadog** - Análisis de logs
   - Agregación de logs
   - Dashboards personalizados
   - Alertas basadas en patrones

**Integración con Sentry:**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration()],
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.1
)
```

---

## Deployment

### Preparación para Despliegue

**Checklist Pre-Despliegue:**

```bash
# 1. Ejecutar tests
pytest tests/ --cov=app

# 2. Validar puntos críticos
python scripts/validate_critical_points.py

# 3. Ejecutar checklist
python scripts/pre_deploy_checklist.py

# 4. Generar certificado de calidad
python scripts/generate_quality_certificate.py
```

### Despliegue en Render.com

**Archivo `render.yaml`:**
```yaml
services:
  - type: web
    name: bgr-shrimp-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python start.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: ENVIRONMENT
        value: production
      - key: DEBUG
        value: false
    # Variables sensibles se configuran en dashboard
```

**Pasos de Despliegue:**

1. **Conectar Repositorio:**
   - Ir a Render Dashboard
   - New → Web Service
   - Conectar repositorio GitHub

2. **Configurar Variables:**
   - Environment → Add Environment Variable
   - Agregar todas las variables de `.env`

3. **Desplegar:**
   - Deploy → Manual Deploy
   - Monitorear logs durante despliegue

4. **Verificar:**
   - Acceder a `/health` endpoint
   - Ejecutar tests de humo
   - Verificar webhook de Twilio

### Despliegue en Railway

**Archivo `railway.json`:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python start.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Despliegue en Heroku

**Archivo `Procfile`:**
```
web: python start.py
```

**Comandos:**
```bash
# Login
heroku login

# Crear app
heroku create bgr-shrimp-bot

# Configurar variables
heroku config:set TWILIO_ACCOUNT_SID=ACxxx...
heroku config:set TWILIO_AUTH_TOKEN=xxx...

# Desplegar
git push heroku main

# Ver logs
heroku logs --tail
```

### Configuración de Webhook Twilio

**URL del Webhook:**
```
https://tu-dominio.com/webhook/whatsapp
```

**Configuración en Twilio Console:**

1. Ir a Twilio Console → Messaging → Settings
2. Configurar Webhook URL
3. Método: POST
4. Guardar cambios

**Verificar Webhook:**
```bash
curl -X POST https://tu-dominio.com/webhook/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp:+593968058769" \
  -d "Body=test" \
  -d "MessageSid=SMxxx"
```

### Rollback

**Procedimiento de Rollback:**

1. **Identificar Versión Anterior:**
   ```bash
   git log --oneline
   ```

2. **Revertir Código:**
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

3. **Despliegue Automático:**
   - Render/Railway detectan push y redesplegan

4. **Verificación:**
   - Ejecutar tests de humo
   - Verificar health check
   - Monitorear logs

**Rollback Manual en Render:**
- Dashboard → Deploys
- Seleccionar deploy anterior
- Click "Redeploy"

### Backup y Restauración

**Backup de Datos:**
```bash
# Backup de sesiones
cp data/sessions.json backups/sessions_$(date +%Y%m%d).json

# Backup de PDFs
tar -czf backups/pdfs_$(date +%Y%m%d).tar.gz generated_pdfs/

# Backup de logs
tar -czf backups/logs_$(date +%Y%m%d).tar.gz logs/
```

**Restauración:**
```bash
# Restaurar sesiones
cp backups/sessions_20250130.json data/sessions.json

# Restaurar PDFs
tar -xzf backups/pdfs_20250130.tar.gz
```

### Monitoreo Post-Despliegue

**Tests de Humo:**
```bash
# Health check
curl https://tu-dominio.com/health

# Test de webhook (con token)
curl -X POST https://tu-dominio.com/webhook/test-twilio \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Métricas a Monitorear:**
- Uptime (objetivo: 99.9%)
- Tiempo de respuesta (objetivo: < 2s)
- Tasa de error (objetivo: < 1%)
- Uso de memoria (objetivo: < 512MB)
- Uso de CPU (objetivo: < 70%)

---

## Mantenimiento

### Tareas de Mantenimiento Regular

**Diarias:**
- Revisar logs de errores
- Verificar health checks
- Monitorear métricas de performance

**Semanales:**
- Limpiar PDFs antiguos (> 7 días)
- Revisar sesiones activas
- Analizar métricas de negocio

**Mensuales:**
- Actualizar dependencias
- Revisar y optimizar logs
- Backup completo del sistema
- Revisión de seguridad

### Actualización de Dependencias

**Verificar Actualizaciones:**
```bash
pip list --outdated
```

**Actualizar Dependencias:**
```bash
pip install --upgrade <package>
pip freeze > requirements.txt
```

**Testing Post-Actualización:**
```bash
pytest tests/
python scripts/validate_critical_points.py
```

### Troubleshooting Común

Ver documento: `04-GUIA_TROUBLESHOOTING.md`

---

## Contacto Técnico

**Desarrollador Principal:**  
Joel Rojas  
Email: rojassebas765@gmail.com  
WhatsApp: +593 968058769

**Soporte Técnico:**  
Email: rojassebas765@gmail.com  
Horario: 24/7 para incidentes críticos

---

**Versión del Manual:** 1.0  
**Última Actualización:** Enero 2025  
**Para:** BGR Export  
**Confidencialidad:** Uso interno
