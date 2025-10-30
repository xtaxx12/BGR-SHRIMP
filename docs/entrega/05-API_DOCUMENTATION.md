# Documentación de API - BGR Shrimp Bot

## Tabla de Contenidos

1. [Información General](#información-general)
2. [Autenticación](#autenticación)
3. [Endpoints Públicos](#endpoints-públicos)
4. [Endpoints Administrativos](#endpoints-administrativos)
5. [Webhooks](#webhooks)
6. [Modelos de Datos](#modelos-de-datos)
7. [Códigos de Respuesta](#códigos-de-respuesta)
8. [Ejemplos de Uso](#ejemplos-de-uso)

---

## Información General

### Base URL

**Producción:**
```
https://bgr-shrimp.onrender.com
```

**Staging:**
```
https://bgr-shrimp-staging.onrender.com
```

**Local:**
```
http://localhost:8000
```

### Formato de Datos

- **Request:** `application/x-www-form-urlencoded` o `application/json`
- **Response:** `application/json` o `application/xml` (para Twilio)
- **Encoding:** UTF-8

### Versionado

**Versión Actual:** v2.0.0

La API no usa versionado en la URL. Los cambios breaking se comunican con anticipación.

### Rate Limiting

- **Límite:** 30 requests por minuto por usuario
- **Header de respuesta:** `X-RateLimit-Remaining`
- **Código de error:** 429 Too Many Requests

---

## Autenticación

### Webhooks de Twilio

Los webhooks de Twilio se validan mediante firma criptográfica.

**Header Requerido:**
```
X-Twilio-Signature: <signature>
```

**Validación:**
```python
from twilio.request_validator import RequestValidator

validator = RequestValidator(TWILIO_AUTH_TOKEN)
is_valid = validator.validate(url, params, signature)
```

### Endpoints Administrativos

Los endpoints administrativos requieren autenticación Bearer.

**Header Requerido:**
```
Authorization: Bearer <ADMIN_API_TOKEN>
```

**Ejemplo:**
```bash
curl -H "Authorization: Bearer abc123xyz" \
  https://bgr-shrimp.onrender.com/webhook/reload-data
```

---

## Endpoints Públicos

### GET /

Información básica del servicio.

**Request:**
```bash
GET /
```

**Response:**
```json
{
  "message": "BGR Export WhatsApp Bot",
  "version": "2.0.0",
  "description": "Sistema de consulta de precios de camarón vía WhatsApp"
}
```

**Códigos de Respuesta:**
- `200 OK` - Éxito

---

### GET /health

Health check del sistema y sus componentes.

**Request:**
```bash
GET /health
```

**Response:**
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

**Estados Posibles:**
- `healthy` - Todos los componentes funcionando
- `degraded` - Algunos componentes con problemas

**Códigos de Respuesta:**
- `200 OK` - Sistema saludable
- `503 Service Unavailable` - Sistema degradado

**Ejemplo:**
```bash
curl https://bgr-shrimp.onrender.com/health
```

---

### GET /webhook/download-pdf/{filename}

Descarga un PDF generado.

**Request:**
```bash
GET /webhook/download-pdf/{filename}
```

**Parámetros:**
- `filename` (path) - Nombre del archivo PDF

**Response:**
- Archivo PDF binario

**Headers de Respuesta:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="cotizacion.pdf"
```

**Códigos de Respuesta:**
- `200 OK` - PDF encontrado
- `404 Not Found` - PDF no existe

**Ejemplo:**
```bash
curl -O https://bgr-shrimp.onrender.com/webhook/download-pdf/cotizacion_BGR_20250130_115546_7425.pdf
```

---

## Endpoints Administrativos

### POST /webhook/whatsapp

Webhook principal para mensajes de WhatsApp desde Twilio.

**Autenticación:** Twilio Signature

**Request:**
```bash
POST /webhook/whatsapp
Content-Type: application/x-www-form-urlencoded
X-Twilio-Signature: <signature>

From=whatsapp:+593968058769
To=whatsapp:+14155238886
Body=HLSO 16/20
MessageSid=SM1234567890abcdef
NumMedia=0
```

**Parámetros:**
- `From` (required) - Número de WhatsApp del usuario
- `To` (required) - Número de WhatsApp del bot
- `Body` (optional) - Texto del mensaje
- `MessageSid` (required) - ID único del mensaje
- `NumMedia` (optional) - Cantidad de archivos multimedia
- `MediaUrl0` (optional) - URL del primer archivo multimedia
- `MediaContentType0` (optional) - Tipo MIME del archivo

**Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>
    🦐 HLSO 16/20
    
    💰 Precios disponibles:
    • FOB: $8.50/kg
    • CFR (con glaseo 20%): $9.20/kg
    
    ¿Deseas generar una proforma? Escribe "confirmar"
  </Message>
</Response>
```

**Códigos de Respuesta:**
- `200 OK` - Mensaje procesado
- `400 Bad Request` - Parámetros inválidos
- `403 Forbidden` - Firma inválida
- `429 Too Many Requests` - Rate limit excedido
- `500 Internal Server Error` - Error del servidor

---

### POST /webhook/reload-data

Recarga datos desde Google Sheets.

**Autenticación:** Bearer Token

**Request:**
```bash
POST /webhook/reload-data
Authorization: Bearer <ADMIN_API_TOKEN>
```

**Response:**
```json
{
  "status": "success",
  "message": "Datos recargados exitosamente",
  "timestamp": "2025-01-30T10:30:00Z",
  "products_loaded": 128,
  "flete_destinations": 25
}
```

**Códigos de Respuesta:**
- `200 OK` - Datos recargados
- `401 Unauthorized` - Token inválido
- `500 Internal Server Error` - Error recargando datos

**Ejemplo:**
```bash
curl -X POST https://bgr-shrimp.onrender.com/webhook/reload-data \
  -H "Authorization: Bearer abc123xyz"
```

---

### GET /webhook/data-status

Obtiene el estado de las fuentes de datos.

**Autenticación:** Bearer Token

**Request:**
```bash
GET /webhook/data-status
Authorization: Bearer <ADMIN_API_TOKEN>
```

**Response:**
```json
{
  "google_sheets": {
    "status": "connected",
    "last_update": "2025-01-30T10:00:00Z",
    "products_count": 128,
    "error": null
  },
  "excel_local": {
    "status": "available",
    "file_path": "data/CALCULO_DE_PRECIOS-AGUAJE17.xlsx",
    "last_modified": "2025-01-25T15:30:00Z",
    "products_count": 128
  },
  "current_source": "google_sheets"
}
```

**Códigos de Respuesta:**
- `200 OK` - Estado obtenido
- `401 Unauthorized` - Token inválido

**Ejemplo:**
```bash
curl https://bgr-shrimp.onrender.com/webhook/data-status \
  -H "Authorization: Bearer abc123xyz"
```

---

### GET /webhook/test-twilio

Prueba la conectividad con Twilio.

**Autenticación:** Bearer Token

**Request:**
```bash
GET /webhook/test-twilio
Authorization: Bearer <ADMIN_API_TOKEN>
```

**Response:**
```json
{
  "status": "success",
  "message": "Conexión con Twilio exitosa",
  "account_sid": "AC***************",
  "whatsapp_number": "whatsapp:+14155238886",
  "balance": "$25.50"
}
```

**Códigos de Respuesta:**
- `200 OK` - Conexión exitosa
- `401 Unauthorized` - Token inválido
- `500 Internal Server Error` - Error de conexión

**Ejemplo:**
```bash
curl https://bgr-shrimp.onrender.com/webhook/test-twilio \
  -H "Authorization: Bearer abc123xyz"
```

---

### GET /metrics

Métricas básicas del sistema (solo en modo debug).

**Autenticación:** Ninguna (solo disponible en debug)

**Request:**
```bash
GET /metrics
```

**Response:**
```json
{
  "uptime_seconds": 86400,
  "environment": "development",
  "debug_mode": true,
  "requests_total": 1523,
  "requests_success": 1498,
  "requests_error": 25,
  "average_response_time": 1.8,
  "active_sessions": 45
}
```

**Códigos de Respuesta:**
- `200 OK` - Métricas obtenidas
- `404 Not Found` - No disponible en producción

---

## Webhooks

### Configuración de Webhook en Twilio

**URL del Webhook:**
```
https://bgr-shrimp.onrender.com/webhook/whatsapp
```

**Método:** POST

**Configuración en Twilio Console:**
1. Ir a Twilio Console
2. Messaging → Settings → WhatsApp Sandbox Settings
3. WHEN A MESSAGE COMES IN: `https://bgr-shrimp.onrender.com/webhook/whatsapp`
4. HTTP Method: POST
5. Guardar

### Eventos Soportados

El webhook procesa los siguientes tipos de mensajes:

1. **Mensajes de Texto**
   - Body contiene el texto del mensaje
   - Se analiza con IA o regex

2. **Mensajes de Audio**
   - MediaUrl0 contiene URL del audio
   - Se transcribe con Whisper API
   - Se procesa como texto

3. **Mensajes con Imágenes**
   - Actualmente no soportado
   - Se responde pidiendo mensaje de texto

### Validación de Webhook

Twilio firma cada request con HMAC-SHA1:

```python
import hmac
import hashlib
from urllib.parse import urlencode

def validate_twilio_signature(url, params, signature, auth_token):
    # Concatenar URL y parámetros
    data = url + urlencode(sorted(params.items()))
    
    # Calcular HMAC-SHA1
    expected = hmac.new(
        auth_token.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    # Codificar en base64
    expected_signature = base64.b64encode(expected).decode('utf-8')
    
    return hmac.compare_digest(expected_signature, signature)
```

---


## Modelos de Datos

### Session

Representa una sesión de usuario.

```json
{
  "state": "idle",
  "data": {},
  "last_quote": {
    "producto": "HLSO",
    "talla": "16/20",
    "precio_fob": 8.50,
    "precio_cfr": 9.20,
    "precio_ddp": 10.50,
    "factor_glaseo": 0.80,
    "glaseo_percentage": 20,
    "flete": 0.25,
    "destination": "China",
    "cliente_nombre": "Juan Pérez",
    "usar_libras": false,
    "timestamp": "2025-01-30T10:30:00Z"
  },
  "language": "es",
  "created_at": "2025-01-30T10:00:00Z",
  "updated_at": "2025-01-30T10:30:00Z"
}
```

**Campos:**
- `state` (string) - Estado actual de la sesión
  - `idle` - Sin operación activa
  - `waiting_for_glaseo` - Esperando porcentaje de glaseo
  - `waiting_for_flete` - Esperando valor de flete
  - `waiting_for_multi_glaseo` - Glaseo para múltiples productos
  - `waiting_for_multi_flete` - Flete para múltiples productos
  - `waiting_for_multi_language` - Idioma para cotización consolidada
- `data` (object) - Datos temporales de la operación actual
- `last_quote` (object) - Última cotización generada
- `language` (string) - Idioma preferido (`es` o `en`)
- `created_at` (datetime) - Fecha de creación
- `updated_at` (datetime) - Última actualización

### PriceInfo

Información de precio de un producto.

```json
{
  "producto": "HLSO",
  "talla": "16/20",
  "precio_fob": 8.50,
  "precio_cfr": 9.20,
  "precio_ddp": 10.50,
  "factor_glaseo": 0.80,
  "glaseo_percentage": 20,
  "flete": 0.25,
  "destination": "China",
  "cliente_nombre": "Juan Pérez",
  "cantidad_libras": 15000,
  "cantidad_kg": 6803.89,
  "usar_libras": false,
  "disponible": true,
  "origen": "Ecuador",
  "timestamp": "2025-01-30T10:30:00Z"
}
```

**Campos:**
- `producto` (string) - Tipo de producto (HLSO, HOSO, etc.)
- `talla` (string) - Talla del camarón (16/20, 21/25, etc.)
- `precio_fob` (float) - Precio FOB en USD/kg
- `precio_cfr` (float) - Precio CFR en USD/kg (con glaseo)
- `precio_ddp` (float) - Precio DDP en USD/kg (con flete)
- `factor_glaseo` (float) - Factor de glaseo (0.70-0.90)
- `glaseo_percentage` (int) - Porcentaje de glaseo (10, 20, 30)
- `flete` (float) - Costo de flete en USD/kg
- `destination` (string) - Destino del envío
- `cliente_nombre` (string) - Nombre del cliente
- `cantidad_libras` (float) - Cantidad en libras
- `cantidad_kg` (float) - Cantidad en kilogramos
- `usar_libras` (boolean) - Si se usa libras en lugar de kg
- `disponible` (boolean) - Si el producto está disponible
- `origen` (string) - País de origen
- `timestamp` (datetime) - Fecha de la cotización

### ConsolidatedQuote

Cotización consolidada con múltiples productos.

```json
{
  "consolidated": true,
  "products_info": [
    {
      "producto": "HLSO",
      "talla": "16/20",
      "precio_fob": 8.50,
      "precio_cfr": 9.20
    },
    {
      "producto": "HLSO",
      "talla": "21/25",
      "precio_fob": 7.80,
      "precio_cfr": 8.45
    }
  ],
  "glaseo_percentage": 20,
  "failed_products": [],
  "flete": 0.25,
  "total_products": 2,
  "timestamp": "2025-01-30T10:30:00Z"
}
```

**Campos:**
- `consolidated` (boolean) - Indica que es cotización consolidada
- `products_info` (array) - Lista de productos con sus precios
- `glaseo_percentage` (int) - Porcentaje de glaseo aplicado
- `failed_products` (array) - Productos que no se pudieron cotizar
- `flete` (float) - Flete aplicado (si es DDP)
- `total_products` (int) - Cantidad total de productos
- `timestamp` (datetime) - Fecha de la cotización

### AIAnalysis

Resultado del análisis de intención con IA.

```json
{
  "intent": "price_query",
  "confidence": 0.95,
  "product": "HLSO",
  "size": "16/20",
  "glaseo_percentage": 20,
  "glaseo_factor": 0.80,
  "destination": "China",
  "flete_custom": 0.25,
  "flete_solicitado": true,
  "is_ddp": true,
  "cliente_nombre": "Juan Pérez",
  "cantidad": 15000,
  "usar_libras": false,
  "language": "es"
}
```

**Campos:**
- `intent` (string) - Intención detectada
  - `greeting` - Saludo
  - `price_query` - Consulta de precio
  - `proforma` - Solicitud de proforma
  - `modify_flete` - Modificar flete
  - `menu_request` - Solicitud de menú
  - `help` - Ayuda
- `confidence` (float) - Confianza del análisis (0.0-1.0)
- `product` (string) - Producto detectado
- `size` (string) - Talla detectada
- `glaseo_percentage` (int) - Porcentaje de glaseo
- `glaseo_factor` (float) - Factor de glaseo calculado
- `destination` (string) - Destino detectado
- `flete_custom` (float) - Flete personalizado
- `flete_solicitado` (boolean) - Si se solicitó flete
- `is_ddp` (boolean) - Si es precio DDP
- `cliente_nombre` (string) - Nombre del cliente
- `cantidad` (float) - Cantidad solicitada
- `usar_libras` (boolean) - Si usa libras
- `language` (string) - Idioma detectado

### HealthStatus

Estado de salud del sistema.

```json
{
  "status": "healthy",
  "service": "bgr-whatsapp-bot",
  "version": "2.0.0",
  "environment": "production",
  "timestamp": "2025-01-30T10:30:00Z",
  "components": {
    "twilio_configured": true,
    "google_sheets_configured": true,
    "openai_configured": true,
    "file_system": true
  },
  "metrics": {
    "uptime_seconds": 86400,
    "requests_total": 1523,
    "active_sessions": 45
  }
}
```

**Campos:**
- `status` (string) - Estado general (`healthy`, `degraded`, `unhealthy`)
- `service` (string) - Nombre del servicio
- `version` (string) - Versión del servicio
- `environment` (string) - Entorno (`production`, `staging`, `development`)
- `timestamp` (datetime) - Fecha del check
- `components` (object) - Estado de componentes individuales
- `metrics` (object) - Métricas del sistema

---

## Códigos de Respuesta

### Códigos de Éxito (2xx)

#### 200 OK
Solicitud procesada exitosamente.

**Ejemplo:**
```json
{
  "status": "success",
  "data": {...}
}
```

#### 201 Created
Recurso creado exitosamente (no usado actualmente).

### Códigos de Error del Cliente (4xx)

#### 400 Bad Request
Parámetros inválidos o faltantes.

**Ejemplo:**
```json
{
  "error": "Bad Request",
  "message": "Invalid phone format",
  "details": {
    "field": "From",
    "value": "invalid-phone"
  }
}
```

#### 401 Unauthorized
Token de autenticación inválido o faltante.

**Ejemplo:**
```json
{
  "error": "Unauthorized",
  "message": "Invalid token"
}
```

#### 403 Forbidden
Firma de Twilio inválida o acceso denegado.

**Ejemplo:**
```json
{
  "error": "Forbidden",
  "message": "Invalid Twilio signature"
}
```

#### 404 Not Found
Recurso no encontrado.

**Ejemplo:**
```json
{
  "error": "Not Found",
  "message": "PDF not found",
  "details": {
    "filename": "cotizacion_BGR_20250130_115546_7425.pdf"
  }
}
```

#### 429 Too Many Requests
Rate limit excedido.

**Ejemplo:**
```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded",
  "details": {
    "limit": 30,
    "window_seconds": 60,
    "retry_after": 45
  }
}
```

### Códigos de Error del Servidor (5xx)

#### 500 Internal Server Error
Error no manejado en el servidor.

**Ejemplo:**
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred",
  "request_id": "abc123-def456-ghi789"
}
```

#### 503 Service Unavailable
Servicio temporalmente no disponible.

**Ejemplo:**
```json
{
  "error": "Service Unavailable",
  "message": "System is degraded",
  "details": {
    "components": {
      "google_sheets": false
    }
  }
}
```

---

## Ejemplos de Uso

### Ejemplo 1: Consulta Simple de Precio

**Escenario:** Usuario consulta precio de HLSO 16/20

**Request (desde Twilio):**
```http
POST /webhook/whatsapp HTTP/1.1
Host: bgr-shrimp.onrender.com
Content-Type: application/x-www-form-urlencoded
X-Twilio-Signature: abc123...

From=whatsapp:+593968058769&To=whatsapp:+14155238886&Body=HLSO 16/20&MessageSid=SM123
```

**Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>
    🦐 HLSO 16/20
    
    💰 Precios disponibles:
    • FOB: $8.50/kg
    • CFR (con glaseo 20%): $9.20/kg
    • DDP: Requiere destino y flete
    
    📦 Inventario: Disponible
    🏭 Origen: Ecuador
    
    ¿Deseas generar una proforma? Escribe "confirmar"
  </Message>
</Response>
```

---

### Ejemplo 2: Generar Proforma

**Escenario:** Usuario confirma generación de proforma

**Request 1 - Consulta:**
```
Body=HLSO 16/20 glaseo 20%
```

**Response 1:**
```xml
<Response>
  <Message>
    🦐 HLSO 16/20
    💰 CFR: $9.20/kg (glaseo 20%)
    
    ¿Deseas generar una proforma? Escribe "confirmar"
  </Message>
</Response>
```

**Request 2 - Confirmación:**
```
Body=confirmar
```

**Response 2:**
```xml
<Response>
  <Message>
    🌐 ¿En qué idioma deseas la proforma?
    
    1️⃣ Español 🇪🇸
    2️⃣ English 🇺🇸
    
    Responde con el número o escribe el idioma
  </Message>
</Response>
```

**Request 3 - Idioma:**
```
Body=español
```

**Response 3:**
```xml
<Response>
  <Message>
    ✅ Proforma generada y enviada en Español 🇪🇸
  </Message>
  <Message>
    <Media>https://bgr-shrimp.onrender.com/webhook/download-pdf/cotizacion_BGR_20250130_115546_7425.pdf</Media>
    <Body>Cotización BGR Export - HLSO 16/20</Body>
  </Message>
</Response>
```

---

### Ejemplo 3: Cotización DDP con Flete

**Escenario:** Usuario solicita precio DDP a China

**Request 1:**
```
Body=HLSO 16/20 DDP China
```

**Response 1:**
```xml
<Response>
  <Message>
    🚢 Para calcular el precio DDP a China necesito el valor del flete:
    
    💡 Ejemplos:
    • "flete 0.25"
    • "0.30 de flete"
    
    ¿Cuál es el valor del flete por kilo? 💰
  </Message>
</Response>
```

**Request 2:**
```
Body=flete 0.25
```

**Response 2:**
```xml
<Response>
  <Message>
    🦐 HLSO 16/20 - DDP China
    
    💰 Precios:
    • FOB: $8.50/kg
    • CFR: $9.20/kg (glaseo 20%)
    • DDP: $10.50/kg (flete $0.25)
    
    ✅ Proforma generada con flete $0.25 a China 🚢
  </Message>
  <Message>
    <Media>https://bgr-shrimp.onrender.com/webhook/download-pdf/cotizacion_BGR_20250130_115546_7425.pdf</Media>
  </Message>
</Response>
```

---

### Ejemplo 4: Recargar Datos (Admin)

**Escenario:** Administrador recarga datos de Google Sheets

**Request:**
```bash
curl -X POST https://bgr-shrimp.onrender.com/webhook/reload-data \
  -H "Authorization: Bearer abc123xyz" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "status": "success",
  "message": "Datos recargados exitosamente",
  "timestamp": "2025-01-30T10:30:00Z",
  "products_loaded": 128,
  "flete_destinations": 25,
  "source": "google_sheets"
}
```

---

### Ejemplo 5: Health Check

**Escenario:** Monitoreo verifica salud del sistema

**Request:**
```bash
curl https://bgr-shrimp.onrender.com/health
```

**Response (Sistema Saludable):**
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

**Response (Sistema Degradado):**
```json
{
  "status": "degraded",
  "service": "bgr-whatsapp-bot",
  "version": "2.0.0",
  "environment": "production",
  "message": "Google Sheets not available",
  "components": {
    "twilio_configured": true,
    "google_sheets_configured": false,
    "openai_configured": true
  }
}
```

---

### Ejemplo 6: Descargar PDF

**Escenario:** Cliente descarga PDF de cotización

**Request:**
```bash
curl -O https://bgr-shrimp.onrender.com/webhook/download-pdf/cotizacion_BGR_20250130_115546_7425.pdf
```

**Response:**
```
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="cotizacion_BGR_20250130_115546_7425.pdf"
Content-Length: 245678

[Binary PDF data]
```

---

### Ejemplo 7: Cotización Consolidada

**Escenario:** Usuario solicita múltiples productos

**Request:**
```
Body=Necesito precios de:
HLSO 16/20
HLSO 21/25
P&D IQF 26/30
Glaseo 20%
```

**Response:**
```xml
<Response>
  <Message>
    📋 Detecté 3 productos para cotizar:
       1. HLSO 16/20
       2. HLSO 21/25
       3. P&D IQF 26/30
    
    ❄️ Glaseo: 20%
    
    ✅ Precios calculados para 3/3 productos
    
    🌐 Selecciona el idioma para la cotización consolidada:
    1️⃣ Español 🇪🇸
    2️⃣ English 🇺🇸
  </Message>
</Response>
```

---

## Límites y Restricciones

### Rate Limiting

- **Límite por usuario:** 30 requests/minuto
- **Ventana de tiempo:** 60 segundos
- **Acción al exceder:** HTTP 429, esperar 60 segundos

### Tamaños Máximos

- **Mensaje de texto:** 1000 caracteres
- **Archivo de audio:** 10MB
- **PDF generado:** 5MB
- **Sesión:** 24 horas de inactividad

### Timeouts

- **Request timeout:** 30 segundos
- **PDF generation timeout:** 60 segundos
- **External API timeout:** 10 segundos

---

## Webhooks de Notificación

Actualmente el sistema no envía webhooks de notificación a sistemas externos. Todas las respuestas se envían directamente a través de Twilio WhatsApp.

**Futuras Implementaciones:**
- Webhook de cotización generada
- Webhook de error crítico
- Webhook de métricas diarias

---

## Versionado y Cambios

### Política de Versionado

- **Major version (v2.0.0):** Cambios breaking en API
- **Minor version (v2.1.0):** Nuevas funcionalidades compatibles
- **Patch version (v2.0.1):** Bug fixes y mejoras menores

### Changelog

**v2.0.0 (Enero 2025)**
- Arquitectura completamente rediseñada
- Seguridad mejorada con validación de webhooks
- Rate limiting implementado
- Soporte para múltiples productos
- Generación de PDFs consolidados
- Transcripción de audio con Whisper
- Análisis de intención con GPT-4

**v1.0.0 (Diciembre 2024)**
- Versión inicial
- Consulta de precios básica
- Generación de PDFs simples

---

## Soporte y Contacto

**Documentación Adicional:**
- Manual de Usuario: `02-MANUAL_USUARIO.md`
- Manual Técnico: `03-MANUAL_TECNICO.md`
- Guía de Troubleshooting: `04-GUIA_TROUBLESHOOTING.md`

**Soporte Técnico:**
- Email: rojassebas765@gmail.com
- WhatsApp: +593 968058769
- Horario: 24/7 para incidentes críticos

**Reportar Bugs:**
- Email con detalles del problema
- Incluir request_id si está disponible
- Adjuntar logs relevantes

---

**Versión de la API:** v2.0.0  
**Última Actualización:** Enero 2025  
**Para:** BGR Export  
**Confidencialidad:** Uso interno
