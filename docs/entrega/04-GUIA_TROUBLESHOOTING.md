# Guía de Troubleshooting - BGR Shrimp Bot

## Tabla de Contenidos

1. [Problemas Comunes](#problemas-comunes)
2. [Diagnóstico Paso a Paso](#diagnóstico-paso-a-paso)
3. [Códigos de Error](#códigos-de-error)
4. [Problemas de Integración](#problemas-de-integración)
5. [Problemas de Performance](#problemas-de-performance)
6. [Procedimientos de Emergencia](#procedimientos-de-emergencia)

---

## Problemas Comunes

### 1. Bot No Responde a Mensajes

**Síntomas:**
- Usuario envía mensaje pero no recibe respuesta
- Webhook no se ejecuta
- No hay logs de la solicitud

**Causas Posibles:**
1. Servicio caído
2. Webhook de Twilio mal configurado
3. Problema de conectividad
4. Rate limiting activado

**Diagnóstico:**

```bash
# 1. Verificar que el servicio está corriendo
curl https://tu-dominio.com/health

# 2. Verificar logs
tail -f logs/app.log

# 3. Verificar configuración de Twilio
# Ir a Twilio Console → Messaging → Settings
# Verificar que Webhook URL es correcta
```

**Soluciones:**

**A. Si el servicio está caído:**
```bash
# En Render/Railway, verificar dashboard
# Revisar logs de deployment
# Hacer redeploy si es necesario
```

**B. Si webhook está mal configurado:**
1. Ir a Twilio Console
2. Messaging → Settings → Webhook Configuration
3. Verificar URL: `https://tu-dominio.com/webhook/whatsapp`
4. Método: POST
5. Guardar cambios

**C. Si hay rate limiting:**
```bash
# Verificar logs
grep "429" logs/app.log

# Esperar 60 segundos o ajustar límites en .env
RATE_LIMIT_MAX_REQUESTS=50
RATE_LIMIT_WINDOW_SECONDS=60
```

---

### 2. Error al Generar PDF

**Síntomas:**
- Mensaje: "❌ Error generando la proforma"
- PDF no se crea
- Error en logs

**Causas Posibles:**
1. Datos incompletos
2. Problema con ReportLab
3. Falta logo o recursos
4. Permisos de escritura

**Diagnóstico:**

```bash
# 1. Verificar logs de error
grep "PDF" logs/errors.log

# 2. Verificar que existe el logo
ls -la data/logoBGR.png

# 3. Verificar permisos del directorio
ls -la generated_pdfs/

# 4. Intentar generar PDF manualmente
python -c "from app.services.pdf_generator import PDFGenerator; \
           gen = PDFGenerator(); \
           print(gen.generate_quote_pdf({...}, 'test', 'es'))"
```

**Soluciones:**

**A. Si falta el logo:**
```bash
# Verificar que existe
ls data/logoBGR.png

# Si no existe, restaurar desde backup
cp backups/logoBGR.png data/
```

**B. Si hay problema de permisos:**
```bash
# Dar permisos de escritura
chmod 755 generated_pdfs/

# Verificar espacio en disco
df -h
```

**C. Si faltan datos:**
```python
# Verificar que price_info tiene todos los campos requeridos
required_fields = ['producto', 'talla', 'precio_fob', 'precio_cfr']
for field in required_fields:
    if field not in price_info:
        logger.error(f"Missing field: {field}")
```

---

### 3. Precios No Encontrados

**Síntomas:**
- Mensaje: "❌ No se encontró precio para..."
- Producto válido pero sin precio
- Error en cálculo

**Causas Posibles:**
1. Producto/talla no existe en datos
2. Google Sheets no disponible
3. Excel local desactualizado
4. Error en nombre de producto

**Diagnóstico:**

```bash
# 1. Verificar conectividad con Google Sheets
curl -X GET https://tu-dominio.com/webhook/data-status \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. Verificar logs
grep "precio" logs/app.log

# 3. Verificar Excel local
python -c "from app.services.excel import ExcelService; \
           svc = ExcelService(); \
           print(svc.get_all_products())"
```

**Soluciones:**

**A. Si Google Sheets no está disponible:**
```bash
# Recargar datos
curl -X POST https://tu-dominio.com/webhook/reload-data \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Verificar credenciales
echo $GOOGLE_SHEETS_CREDENTIALS | jq .

# Verificar ID de sheet
echo $GOOGLE_SHEETS_ID
```

**B. Si producto no existe:**
```bash
# Listar productos disponibles
python -c "from app.services.pricing import PricingService; \
           svc = PricingService(); \
           print(svc.get_available_products())"

# Agregar producto a Google Sheets o Excel
```

**C. Si hay error en nombre:**
```python
# Verificar normalización de nombres
# HLSO vs Hlso vs hlso
# Todos deberían funcionar por normalización
```

---

### 4. Mensajes de Audio No Se Transcriben

**Síntomas:**
- Audio enviado pero no transcrito
- Mensaje: "❌ No pude procesar el audio"
- Error en logs

**Causas Posibles:**
1. OpenAI API no disponible
2. API key inválida
3. Formato de audio no soportado
4. Archivo muy grande

**Diagnóstico:**

```bash
# 1. Verificar API key de OpenAI
echo $OPENAI_API_KEY

# 2. Verificar logs
grep "audio" logs/app.log

# 3. Test de OpenAI
python -c "from openai import OpenAI; \
           client = OpenAI(); \
           print(client.models.list())"
```

**Soluciones:**

**A. Si OpenAI no está disponible:**
```bash
# Verificar status de OpenAI
curl https://status.openai.com/api/v2/status.json

# Usar fallback (análisis básico sin IA)
# El sistema automáticamente usa fallback
```

**B. Si API key es inválida:**
```bash
# Regenerar API key en OpenAI dashboard
# Actualizar variable de entorno
heroku config:set OPENAI_API_KEY=sk-new-key...
```

**C. Si formato no soportado:**
```python
# Verificar que Twilio envía formato OGG
# El sistema convierte automáticamente
# Si falla, pedir al usuario que envíe texto
```

---

### 5. Sesiones Se Pierden

**Síntomas:**
- Usuario pierde contexto entre mensajes
- Última cotización no se encuentra
- Estado de sesión se resetea

**Causas Posibles:**
1. Archivo sessions.json corrupto
2. Problema de escritura
3. Sesión expirada (> 24 horas)
4. Reinicio del servicio

**Diagnóstico:**

```bash
# 1. Verificar archivo de sesiones
cat data/sessions.json | jq .

# 2. Verificar permisos
ls -la data/sessions.json

# 3. Verificar logs
grep "session" logs/app.log
```

**Soluciones:**

**A. Si archivo está corrupto:**
```bash
# Restaurar desde backup
cp backups/sessions_latest.json data/sessions.json

# O crear nuevo archivo vacío
echo '{}' > data/sessions.json
```

**B. Si hay problema de permisos:**
```bash
# Dar permisos de escritura
chmod 644 data/sessions.json
```

**C. Si sesiones expiran muy rápido:**
```python
# Ajustar tiempo de expiración en session.py
SESSION_TIMEOUT = 86400  # 24 horas en segundos
```

---

### 6. Rate Limiting Excesivo

**Síntomas:**
- Mensaje: "Too many requests"
- Usuario bloqueado temporalmente
- Error 429 en logs

**Causas Posibles:**
1. Usuario enviando muchos mensajes
2. Límite muy bajo
3. Ataque de spam
4. Mensajes duplicados

**Diagnóstico:**

```bash
# 1. Verificar logs de rate limiting
grep "429" logs/app.log

# 2. Verificar configuración
echo $RATE_LIMIT_MAX_REQUESTS
echo $RATE_LIMIT_WINDOW_SECONDS

# 3. Identificar usuario problemático
grep "Too many requests" logs/app.log | grep -o "whatsapp:[+0-9]*"
```

**Soluciones:**

**A. Si límite es muy bajo:**
```bash
# Ajustar límites en .env
RATE_LIMIT_MAX_REQUESTS=50  # Aumentar de 30 a 50
RATE_LIMIT_WINDOW_SECONDS=60

# Redeploy para aplicar cambios
```

**B. Si es spam:**
```python
# Agregar usuario a blacklist
# En security.py, agregar:
BLACKLISTED_NUMBERS = [
    "whatsapp:+1234567890"
]

def is_blacklisted(phone: str) -> bool:
    return phone in BLACKLISTED_NUMBERS
```

**C. Si son duplicados:**
```bash
# Verificar deduplicación
grep "duplicado" logs/app.log

# El sistema ya maneja duplicados automáticamente
# Si persiste, verificar MessageSid en logs
```

---


## Diagnóstico Paso a Paso

### Procedimiento General de Diagnóstico

Cuando enfrentes un problema, sigue estos pasos en orden:

#### Paso 1: Verificar Estado del Sistema

```bash
# Health check
curl https://tu-dominio.com/health

# Respuesta esperada:
{
  "status": "healthy",
  "service": "bgr-whatsapp-bot",
  "version": "2.0.0",
  "components": {
    "twilio_configured": true,
    "google_sheets_configured": true,
    "openai_configured": true
  }
}
```

**Si status es "degraded":**
- Identificar qué componente está fallando
- Ir a sección específica de ese componente

#### Paso 2: Revisar Logs Recientes

```bash
# Últimos 50 logs
tail -n 50 logs/app.log

# Filtrar errores
grep "ERROR" logs/errors.log | tail -n 20

# Buscar request específico
grep "request_id:abc123" logs/app.log
```

**Qué buscar:**
- Stack traces de excepciones
- Mensajes de error específicos
- Request IDs para rastrear flujo completo
- Tiempos de respuesta anormales

#### Paso 3: Reproducir el Problema

```bash
# Test manual del webhook
curl -X POST https://tu-dominio.com/webhook/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Twilio-Signature: <signature>" \
  -d "From=whatsapp:+593968058769" \
  -d "Body=HLSO 16/20" \
  -d "MessageSid=SM123456"
```

**Observar:**
- Código de respuesta HTTP
- Tiempo de respuesta
- Contenido de respuesta
- Logs generados

#### Paso 4: Aislar el Componente

```python
# Test individual de componentes
python -c "
from app.services.pricing import PricingService
svc = PricingService()
result = svc.get_shrimp_price({'product': 'HLSO', 'size': '16/20'})
print(result)
"
```

**Componentes a testear:**
- PricingService
- GoogleSheetsService
- PDFGenerator
- OpenAIService
- WhatsAppSender

#### Paso 5: Verificar Configuración

```bash
# Verificar variables de entorno críticas
env | grep TWILIO
env | grep GOOGLE_SHEETS
env | grep OPENAI

# Verificar archivos de configuración
cat .env | grep -v "^#" | grep -v "^$"
```

**Variables críticas:**
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- GOOGLE_SHEETS_ID
- GOOGLE_SHEETS_CREDENTIALS
- SECRET_KEY

#### Paso 6: Aplicar Solución

Basado en el diagnóstico, aplicar la solución apropiada de la sección "Problemas Comunes".

#### Paso 7: Verificar Solución

```bash
# Re-ejecutar test
curl https://tu-dominio.com/health

# Verificar logs
tail -f logs/app.log

# Test funcional completo
# Enviar mensaje de WhatsApp real
```

---

## Códigos de Error

### Errores HTTP

#### 400 Bad Request

**Mensaje:** "Invalid phone format" o "Invalid input"

**Causa:** Entrada de usuario inválida

**Solución:**
```python
# Verificar validación de teléfono
def validate_phone_number(phone: str) -> bool:
    pattern = r'^whatsapp:\+\d{10,15}$'
    return bool(re.match(pattern, phone))
```

#### 401 Unauthorized

**Mensaje:** "Invalid token"

**Causa:** Token de administrador inválido

**Solución:**
```bash
# Verificar token
echo $ADMIN_API_TOKEN

# Usar token correcto en request
curl -H "Authorization: Bearer $ADMIN_API_TOKEN" ...
```

#### 403 Forbidden

**Mensaje:** "Invalid signature"

**Causa:** Webhook de Twilio no validado correctamente

**Solución:**
```python
# Verificar TWILIO_AUTH_TOKEN
# Verificar que URL en Twilio Console es correcta
# Verificar que request viene de Twilio
```

#### 429 Too Many Requests

**Mensaje:** "Too many requests"

**Causa:** Rate limiting activado

**Solución:**
```bash
# Esperar 60 segundos
# O ajustar límites
RATE_LIMIT_MAX_REQUESTS=50
```

#### 500 Internal Server Error

**Mensaje:** Varía según el error

**Causa:** Error no manejado en el servidor

**Solución:**
```bash
# Revisar logs de error
tail -n 100 logs/errors.log

# Identificar stack trace
# Corregir bug o reportar
```

### Errores de Negocio

#### PRICE_NOT_FOUND

**Mensaje:** "No se encontró precio para [producto] [talla]"

**Causa:** Producto o talla no existe en datos

**Solución:**
1. Verificar que producto/talla son válidos
2. Recargar datos de Google Sheets
3. Verificar Excel local
4. Agregar producto si es nuevo

#### INVALID_GLASEO

**Mensaje:** "Porcentaje de glaseo inválido"

**Causa:** Glaseo fuera de rango (10%, 20%, 30%)

**Solución:**
```python
# Validar glaseo
def validate_glaseo(percentage: int) -> bool:
    return percentage in [10, 20, 30]
```

#### FLETE_NOT_SPECIFIED

**Mensaje:** "Necesito el valor del flete"

**Causa:** DDP solicitado sin especificar flete

**Solución:**
- Usuario debe proporcionar valor de flete
- O verificar si existe en Google Sheets para ese destino

#### PDF_GENERATION_FAILED

**Mensaje:** "Error generando la proforma"

**Causa:** Fallo en generación de PDF

**Solución:**
1. Verificar que existe logo
2. Verificar permisos de escritura
3. Verificar espacio en disco
4. Revisar logs para error específico

#### SESSION_EXPIRED

**Mensaje:** "Sesión expirada"

**Causa:** Sesión > 24 horas

**Solución:**
- Usuario debe iniciar nueva consulta
- Sesión se limpia automáticamente

### Errores de Integración

#### TWILIO_API_ERROR

**Mensaje:** "Error enviando mensaje"

**Causa:** Fallo en API de Twilio

**Solución:**
```bash
# Verificar status de Twilio
curl https://status.twilio.com/api/v2/status.json

# Verificar credenciales
# Verificar balance de cuenta
```

#### GOOGLE_SHEETS_ERROR

**Mensaje:** "Error accediendo a Google Sheets"

**Causa:** Fallo en API de Google Sheets

**Solución:**
```bash
# Verificar credenciales
echo $GOOGLE_SHEETS_CREDENTIALS | jq .

# Verificar permisos de service account
# Verificar que sheet existe y es accesible
```

#### OPENAI_API_ERROR

**Mensaje:** "Error en análisis de IA"

**Causa:** Fallo en API de OpenAI

**Solución:**
```bash
# Sistema usa fallback automáticamente
# Verificar API key si persiste
echo $OPENAI_API_KEY

# Verificar status de OpenAI
curl https://status.openai.com/api/v2/status.json
```

---

## Problemas de Integración

### Twilio WhatsApp

#### Problema: Webhook No Se Ejecuta

**Diagnóstico:**
```bash
# 1. Verificar configuración en Twilio Console
# Messaging → Settings → Webhook Configuration

# 2. Verificar que URL es accesible públicamente
curl https://tu-dominio.com/webhook/whatsapp

# 3. Verificar logs de Twilio
# Console → Monitor → Logs → Errors
```

**Solución:**
1. Verificar URL en Twilio Console
2. Asegurar que es HTTPS (no HTTP)
3. Verificar que servicio está corriendo
4. Verificar firewall/security groups

#### Problema: Mensajes No Se Envían

**Diagnóstico:**
```bash
# Test de envío
python -c "
from app.services.whatsapp_sender import WhatsAppSender
sender = WhatsAppSender()
result = sender.send_message('whatsapp:+593968058769', 'Test')
print(result)
"
```

**Solución:**
1. Verificar credenciales de Twilio
2. Verificar balance de cuenta
3. Verificar que número está aprobado
4. Revisar logs de Twilio Console

#### Problema: PDFs No Se Envían

**Diagnóstico:**
```bash
# Verificar que PDF existe
ls -la generated_pdfs/

# Verificar que URL es accesible
curl https://tu-dominio.com/webhook/download-pdf/filename.pdf
```

**Solución:**
1. Verificar que PDF se generó correctamente
2. Verificar que URL es pública
3. Verificar tamaño de PDF (< 5MB)
4. Usar media_url en lugar de attachment

### Google Sheets

#### Problema: No Se Pueden Leer Datos

**Diagnóstico:**
```bash
# Test de conexión
python -c "
from app.services.google_sheets import GoogleSheetsService
svc = GoogleSheetsService()
data = svc.get_price_data()
print(len(data))
"
```

**Solución:**
1. Verificar GOOGLE_SHEETS_CREDENTIALS
2. Verificar GOOGLE_SHEETS_ID
3. Verificar permisos de service account
4. Compartir sheet con service account email

#### Problema: Datos Desactualizados

**Diagnóstico:**
```bash
# Verificar última actualización
curl -X GET https://tu-dominio.com/webhook/data-status \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Solución:**
```bash
# Forzar recarga
curl -X POST https://tu-dominio.com/webhook/reload-data \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### OpenAI

#### Problema: Transcripción Falla

**Diagnóstico:**
```bash
# Verificar API key
python -c "
from openai import OpenAI
client = OpenAI()
print(client.models.list())
"
```

**Solución:**
1. Verificar OPENAI_API_KEY
2. Verificar balance de cuenta OpenAI
3. Sistema usa fallback automáticamente
4. Pedir al usuario que envíe texto

#### Problema: Análisis de Intención Incorrecto

**Diagnóstico:**
```bash
# Revisar logs de análisis
grep "análisis" logs/app.log
```

**Solución:**
1. Sistema usa fallback si confianza < 0.7
2. Mejorar prompt de sistema
3. Ajustar temperatura del modelo
4. Usar análisis básico sin IA

---

## Problemas de Performance

### Respuestas Lentas

**Síntomas:**
- Tiempo de respuesta > 5 segundos
- Timeouts frecuentes
- Usuarios reportan lentitud

**Diagnóstico:**
```bash
# Verificar tiempos de respuesta en logs
grep "process_time" logs/app.log | tail -n 20

# Verificar uso de recursos
top
htop
```

**Soluciones:**

**A. Si Google Sheets es lento:**
```python
# Implementar cache
from functools import lru_cache
import time

@lru_cache(maxsize=100)
def get_cached_price(product, size):
    return google_sheets_service.get_price(product, size)

# Cache expira cada 5 minutos
```

**B. Si OpenAI es lento:**
```python
# Reducir max_tokens
response = client.chat.completions.create(
    model="gpt-4",
    max_tokens=300,  # Reducir de 500
    temperature=0.3
)
```

**C. Si generación de PDF es lenta:**
```python
# Optimizar imágenes
# Reducir calidad de logo si es muy grande
# Usar formato más eficiente
```

### Alto Uso de Memoria

**Síntomas:**
- Memoria > 512MB
- OOM (Out of Memory) errors
- Servicio se reinicia

**Diagnóstico:**
```bash
# Verificar uso de memoria
free -h
ps aux | grep python

# Verificar logs
grep "memory" logs/app.log
```

**Soluciones:**

**A. Limpiar sesiones antiguas:**
```python
def cleanup_old_sessions():
    """Limpia sesiones > 24 horas"""
    current_time = time.time()
    for user_id, session in list(sessions.items()):
        if current_time - session['updated_at'] > 86400:
            del sessions[user_id]
```

**B. Limpiar PDFs antiguos:**
```bash
# Cron job para limpiar PDFs > 7 días
find generated_pdfs/ -name "*.pdf" -mtime +7 -delete
```

**C. Limitar cache:**
```python
# Reducir tamaño de cache
@lru_cache(maxsize=50)  # Reducir de 100
```

### Alto Uso de CPU

**Síntomas:**
- CPU > 80%
- Respuestas lentas
- Servicio no responde

**Diagnóstico:**
```bash
# Verificar procesos
top -o %CPU

# Verificar workers de Uvicorn
ps aux | grep uvicorn
```

**Soluciones:**

**A. Ajustar workers:**
```python
# En start.py
uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=settings.PORT,
    workers=2  # Ajustar según CPU disponible
)
```

**B. Optimizar regex:**
```python
# Compilar regex una vez
PRODUCT_PATTERN = re.compile(r'\b(HLSO|HOSO|P&D IQF)\b', re.I)

def extract_product(text):
    return PRODUCT_PATTERN.search(text)
```

---

## Procedimientos de Emergencia

### Servicio Completamente Caído

**Prioridad:** P1 - Crítico

**Pasos Inmediatos:**

1. **Verificar Status:**
   ```bash
   curl https://tu-dominio.com/health
   ```

2. **Revisar Dashboard:**
   - Ir a Render/Railway dashboard
   - Verificar status del servicio
   - Revisar logs de deployment

3. **Intentar Restart:**
   ```bash
   # En Render: Manual Deploy → Restart
   # En Railway: Settings → Restart
   ```

4. **Si persiste, Rollback:**
   ```bash
   # Identificar último deploy exitoso
   # Hacer rollback a esa versión
   ```

5. **Notificar:**
   - Informar a stakeholders
   - Actualizar status page
   - Documentar incidente

### Pérdida de Datos

**Prioridad:** P1 - Crítico

**Pasos Inmediatos:**

1. **Detener Servicio:**
   ```bash
   # Prevenir más pérdida de datos
   # Pausar servicio en dashboard
   ```

2. **Identificar Alcance:**
   ```bash
   # ¿Qué datos se perdieron?
   # Sesiones, PDFs, logs?
   ```

3. **Restaurar desde Backup:**
   ```bash
   # Sesiones
   cp backups/sessions_latest.json data/sessions.json
   
   # PDFs
   tar -xzf backups/pdfs_latest.tar.gz
   ```

4. **Verificar Integridad:**
   ```bash
   # Verificar que archivos son válidos
   cat data/sessions.json | jq .
   ```

5. **Reiniciar Servicio:**
   ```bash
   # Restart en dashboard
   # Verificar health check
   ```

### Brecha de Seguridad

**Prioridad:** P1 - Crítico

**Pasos Inmediatos:**

1. **Aislar Sistema:**
   ```bash
   # Pausar servicio inmediatamente
   # Prevenir más acceso no autorizado
   ```

2. **Cambiar Credenciales:**
   ```bash
   # Regenerar todos los tokens
   # TWILIO_AUTH_TOKEN
   # ADMIN_API_TOKEN
   # SECRET_KEY
   # OPENAI_API_KEY
   ```

3. **Revisar Logs:**
   ```bash
   # Identificar accesos sospechosos
   grep "401\|403" logs/security.log
   
   # Identificar IPs sospechosas
   grep "suspicious" logs/security.log
   ```

4. **Aplicar Parches:**
   ```bash
   # Actualizar dependencias
   pip install --upgrade -r requirements.txt
   
   # Aplicar fixes de seguridad
   ```

5. **Auditoría Completa:**
   - Revisar todos los accesos
   - Verificar integridad de datos
   - Documentar incidente
   - Notificar a afectados si necesario

### Integración Externa Caída

**Prioridad:** P2 - Alto

**Twilio Caído:**
```bash
# 1. Verificar status
curl https://status.twilio.com/api/v2/status.json

# 2. Notificar a usuarios
# 3. Esperar restauración
# 4. No hay fallback para Twilio
```

**Google Sheets Caído:**
```bash
# 1. Sistema usa Excel automáticamente
# 2. Verificar que Excel está actualizado
# 3. Monitorear restauración de Google Sheets
# 4. Recargar datos cuando vuelva
```

**OpenAI Caído:**
```bash
# 1. Sistema usa análisis básico automáticamente
# 2. Funcionalidad reducida pero operativa
# 3. Monitorear restauración
# 4. Transcripción de audio no disponible
```

---

## Contacto de Emergencia

**Para Incidentes Críticos (P1):**

**Desarrollador Principal:**  
Sebastián Rojas  
WhatsApp: +593 968058769  
Email: rojassebas765@gmail.com  
Disponibilidad: 24/7

**Escalamiento:**
1. Contactar por WhatsApp (respuesta < 30 min)
2. Si no responde, email (respuesta < 1 hora)
3. Si persiste, contactar a BGR Export directamente

**Información a Proporcionar:**
1. Descripción del problema
2. Hora de inicio
3. Impacto (usuarios afectados)
4. Logs relevantes
5. Pasos ya intentados

---

**Versión:** 1.0  
**Última Actualización:** Enero 2025  
**Para:** BGR Export  
**Confidencialidad:** Uso interno
