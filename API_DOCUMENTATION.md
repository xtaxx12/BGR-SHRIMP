# 📚 BGR Export WhatsApp Bot - Documentación de API

## 🌐 Acceso a la Documentación Interactiva

La API incluye documentación interactiva generada automáticamente con Swagger/OpenAPI:

- **Swagger UI**: `http://localhost:8000/docs` (solo en modo DEBUG)
- **ReDoc**: `http://localhost:8000/redoc` (solo en modo DEBUG)
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🚀 Inicio Rápido

### Requisitos Previos

```bash
# Python 3.11+
python --version

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### Ejecutar el Servidor

```bash
# Modo desarrollo
python start.py

# O con uvicorn directamente
uvicorn app.main:app --reload --port 8000
```

## 📋 Endpoints Principales

### 1. Sistema

#### GET `/`
Información básica de la API

**Respuesta:**
```json
{
  "message": "BGR Export WhatsApp Bot",
  "version": "2.0.0",
  "description": "Sistema de consulta de precios de camarón vía WhatsApp",
  "docs": "/docs",
  "health": "/health"
}
```

#### GET `/health`
Health check básico

**Respuesta:**
```json
{
  "status": "healthy",
  "service": "bgr-whatsapp-bot",
  "version": "2.0.0",
  "environment": "production",
  "components": {
    "twilio_configured": true,
    "google_sheets_configured": true,
    "openai_configured": true
  }
}
```

#### GET `/health/detailed`
Health check detallado con verificación de componentes

**Respuesta:**
```json
{
  "status": "healthy",
  "timestamp": 1700000000.0,
  "checks": {
    "twilio": {
      "status": "ok",
      "configured": true
    },
    "google_sheets": {
      "status": "ok",
      "configured": true,
      "data_loaded": true
    },
    "openai": {
      "status": "ok",
      "configured": true
    },
    "sentry": {
      "status": "ok",
      "configured": true
    }
  }
}
```

#### GET `/metrics`
Métricas Prometheus (requiere `ENABLE_METRICS=true`)

**Respuesta:** Formato texto plano compatible con Prometheus

### 2. WhatsApp

#### POST `/webhook/whatsapp`
Webhook para recibir mensajes de WhatsApp vía Twilio

**Headers:**
- `X-Twilio-Signature`: Firma de validación de Twilio (requerido en producción)

**Form Data:**
- `Body` (string): Contenido del mensaje
- `From` (string): Número del remitente (formato: `whatsapp:+593999999999`)
- `To` (string): Número del destinatario
- `MessageSid` (string): ID único del mensaje
- `NumMedia` (int): Número de archivos multimedia
- `MediaUrl0` (string, opcional): URL del primer archivo multimedia
- `MediaContentType0` (string, opcional): Tipo de contenido del multimedia

**Ejemplo de Request:**
```bash
curl -X POST "http://localhost:8000/webhook/whatsapp" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "Body=Precio HLSO 16/20" \
  -d "From=whatsapp:+593999999999" \
  -d "To=whatsapp:+14155238886" \
  -d "MessageSid=SM1234567890abcdef" \
  -d "NumMedia=0"
```

**Respuesta:** XML de TwiML para responder al usuario

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>✅ Proforma generada y enviada en Español 🇪🇸</Message>
</Response>
```

### 3. Administración

#### POST `/webhook/reload-data`
Recarga los datos de precios desde Google Sheets

**Headers:**
- `Authorization: Bearer <ADMIN_TOKEN>` (requerido)

**Respuesta:**
```json
{
  "message": "Datos recargados exitosamente",
  "success": true,
  "products_loaded": 8,
  "timestamp": 1700000000.0
}
```

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/webhook/reload-data" \
  -H "Authorization: Bearer tu_token_admin"
```

#### GET `/webhook/data-status`
Obtiene el estado actual de los datos

**Headers:**
- `Authorization: Bearer <ADMIN_TOKEN>` (requerido)

**Respuesta:**
```json
{
  "status": "ok",
  "google_sheets_connected": true,
  "products_loaded": 8,
  "total_sizes": 45,
  "last_update": "2025-11-19T14:30:00",
  "products": {
    "HLSO": ["16/20", "21/25", "26/30", "31/35", "36/40", "41/50", "51/60", "61/70", "71/90"],
    "HOSO": ["20/30", "30/40", "40/50", "50/60", "60/70", "70/80"],
    "P&D IQF": ["16/20", "21/25", "26/30"],
    "COOKED": ["16/20", "21/25", "26/30"]
  }
}
```

### 4. PDFs

#### GET `/webhook/download-pdf/{filename}`
Descarga un PDF generado

**Parámetros:**
- `filename` (string): Nombre del archivo PDF

**Respuesta:** Archivo PDF

**Ejemplo:**
```bash
curl -O "http://localhost:8000/webhook/download-pdf/cotizacion_BGR_20251119_144246_87.pdf"
```

## 🔐 Autenticación

### Endpoints Públicos
- `/` - Root
- `/health` - Health check básico
- `/health/detailed` - Health check detallado
- `/metrics` - Métricas (si está habilitado)
- `/webhook/whatsapp` - Webhook de WhatsApp (validado con firma Twilio)
- `/webhook/download-pdf/{filename}` - Descarga de PDFs

### Endpoints Protegidos
Requieren header `Authorization: Bearer <ADMIN_TOKEN>`

- `/webhook/reload-data` - Recarga de datos
- `/webhook/data-status` - Estado de datos

**Configuración del token:**
```bash
# En .env
ADMIN_TOKEN=tu_token_secreto_aqui
```

## 📊 Modelos de Datos

### Productos Disponibles

```python
HLSO              # Head Less Shell On - Sin cabeza, con cáscara
HOSO              # Head On Shell On - Camarón entero con cabeza
P&D IQF           # Pelado y desvenado individual
P&D BLOQUE        # Pelado y desvenado en bloque
EZ PEEL           # Fácil pelado
PuD-EUROPA        # Calidad premium para Europa
PuD-EEUU          # Calidad para Estados Unidos
COOKED            # Cocido listo para consumo
PRE-COCIDO        # Pre-cocido
COCIDO SIN TRATAR # Cocido sin tratamiento
```

### Tallas Disponibles

```
U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40, 
40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90
```

### Estructura de Precio

```json
{
  "producto": "HLSO",
  "talla": "16/20",
  "precio_base_kg": 11.45,
  "precio_fob_kg": 11.70,
  "precio_final_kg": 11.95,
  "factor_glaseo": 0.80,
  "glaseo_percentage": 20,
  "flete": 0.25,
  "destination": "Houston",
  "usar_libras": false,
  "cliente_nombre": "Cliente Ejemplo"
}
```

### Estructura de Error

```json
{
  "error": true,
  "error_message": "La talla 20/30 no está disponible para HLSO. Tallas disponibles: 16/20, 21/25, 26/30",
  "product": "HLSO",
  "size": "20/30",
  "available_sizes": ["16/20", "21/25", "26/30", "31/35", "36/40", "41/50", "51/60", "61/70", "71/90"]
}
```

## 🎯 Ejemplos de Uso

### Ejemplo 1: Consulta Simple

**Mensaje del usuario:**
```
Precio HLSO 16/20
```

**Flujo:**
1. Sistema detecta producto (HLSO) y talla (16/20)
2. Pregunta por glaseo si no se especificó
3. Usuario responde con porcentaje de glaseo
4. Sistema genera y envía PDF automáticamente

### Ejemplo 2: Consulta CFR

**Mensaje del usuario:**
```
Precio cfr de HLSO 16/20 con 0.25 de flete
```

**Flujo:**
1. Sistema detecta producto, talla y flete
2. Pregunta por glaseo si no se especificó
3. Calcula precio CFR (FOB + Flete)
4. Genera y envía PDF

### Ejemplo 3: Cotización Consolidada

**Mensaje del usuario:**
```
Necesito precios de HLSO 16/20, 21/25 y 26/30 con glaseo 20%
```

**Flujo:**
1. Sistema detecta múltiples tallas
2. Calcula precios para todas las tallas
3. Pregunta por idioma del PDF
4. Genera PDF consolidado con todas las tallas

### Ejemplo 4: Error de Talla No Disponible

**Mensaje del usuario:**
```
Precio cfr de cola 20/30 con 0.25 de flete
```

**Respuesta del sistema:**
```
❌ La talla 20/30 no está disponible para HLSO. 
Tallas disponibles: 16/20, 21/25, 26/30, 31/35, 36/40, 41/50, 51/60, 61/70, 71/90
```

## 🔧 Configuración

### Variables de Entorno

```bash
# Servidor
PORT=8000
ENVIRONMENT=production  # development, staging, production
DEBUG=false

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_WHATSAPP_NUMBER=+14155238886

# Google Sheets (Precios)
GOOGLE_SHEETS_ID=xxxxx
GOOGLE_SHEETS_CREDENTIALS={"type":"service_account",...}

# OpenAI (Análisis IA)
OPENAI_API_KEY=sk-xxxxx

# Administración
ADMIN_TOKEN=tu_token_secreto

# Sentry (Monitoreo)
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx

# Métricas
ENABLE_METRICS=true

# CORS
CORS_ORIGINS=["*"]
ALLOWED_HOSTS=["*"]
```

## 📈 Monitoreo

### Métricas Disponibles

El sistema expone métricas en formato Prometheus en `/metrics`:

- **api_request_duration_seconds**: Duración de requests
- **api_request_total**: Total de requests
- **api_request_errors_total**: Total de errores

### Health Checks

- **Básico** (`/health`): Verifica configuración de componentes
- **Detallado** (`/health/detailed`): Verifica conectividad y datos

### Logging

Todos los requests se registran con:
- Request ID único
- Método y path
- IP del cliente
- Tiempo de procesamiento
- Status code

## 🐛 Troubleshooting

### Error: "Twilio signature validation failed"

**Solución:** Verificar que `TWILIO_AUTH_TOKEN` esté configurado correctamente

### Error: "Google Sheets not configured"

**Solución:** Verificar `GOOGLE_SHEETS_ID` y `GOOGLE_SHEETS_CREDENTIALS`

### Error: "OpenAI API key not configured"

**Solución:** Configurar `OPENAI_API_KEY` en variables de entorno

### Error: "Rate limit exceeded"

**Solución:** El sistema limita a 10 requests/minuto por número de WhatsApp. Esperar 1 minuto.

## 📞 Soporte

Para soporte técnico o consultas:
- Email: info@bgrexport.com
- Web: https://bgrexport.com

## 📄 Licencia

Proprietary - BGR Export © 2025
