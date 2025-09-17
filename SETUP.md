# 🚀 Guía de Configuración - BGR Export WhatsApp Bot

## 📋 Requisitos Previos

1. **Python 3.11+** instalado
2. **Cuenta de Twilio** con WhatsApp API habilitado
3. **Archivo Excel** con precios (hoja "PRECIOS FOB")

## ⚙️ Configuración Local

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
```bash
# Copiar archivo de ejemplo
copy .env.example .env

# Editar .env con tus credenciales de Twilio
```

### 3. Preparar archivo Excel
- Coloca tu archivo Excel en `data/precios_fob.xlsx`
- Debe tener una hoja llamada "PRECIOS FOB"
- Columnas requeridas: TALLA, PRECIO_BASE, PRODUCTO, COSTO_FIJO, FACTOR_GLASEO, FLETE

### 4. Ejecutar localmente
```bash
python run_local.py
```

## 🌐 Configuración en Railway

### 1. Crear proyecto en Railway
- Conecta tu repositorio GitHub
- Railway detectará automáticamente el proyecto Python

### 2. Configurar variables de entorno en Railway
```
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token  
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### 3. Deploy automático
- Railway desplegará automáticamente cuando hagas push al repositorio

## 📱 Configuración de Twilio WhatsApp

### 1. Configurar Webhook
- URL del webhook: `https://tu-app.railway.app/webhook/whatsapp`
- Método: POST

### 2. Probar el bot
Envía un mensaje a tu número de WhatsApp de Twilio:
```
16/20
```

## 🧪 Pruebas

### Ejecutar tests
```bash
python -m pytest tests/
```

### Ejemplos de mensajes para probar
- `16/20`
- `Precio HLSO 21/25`
- `Precio HLSO 16/20 para 15,000 lb destino China`

## 📊 Estructura del Excel

Tu archivo Excel debe tener esta estructura en la hoja "PRECIOS FOB":

| TALLA | PRECIO_BASE | PRODUCTO | COSTO_FIJO | FACTOR_GLASEO | FLETE |
|-------|-------------|----------|------------|---------------|-------|
| 8/12  | 12.50       | HLSO     | 0.25       | 0.7           | 0.20  |
| 13/15 | 10.80       | HLSO     | 0.25       | 0.7           | 0.20  |
| 16/20 | 8.55        | HLSO     | 0.25       | 0.7           | 0.20  |

## 🔧 Solución de Problemas

### Error: "Archivo Excel no encontrado"
- Verifica que el archivo esté en `data/precios_fob.xlsx`
- El sistema usará datos de ejemplo si no encuentra el archivo

### Error de conexión con Twilio
- Verifica tus credenciales en el archivo `.env`
- Asegúrate de que el webhook esté configurado correctamente

### Bot no responde
- Verifica que el servidor esté corriendo
- Revisa los logs para errores
- Confirma que la URL del webhook sea correcta