# 🚀 Guía de Despliegue en Render

## Pasos para desplegar en Render:

### 1. Preparar el repositorio
```bash
# Asegúrate de que todos los archivos estén committeados
git add .
git commit -m "Preparar para despliegue en Render"
git push origin main
```

### 2. Crear servicio en Render
1. Ve a [render.com](https://render.com) y crea una cuenta
2. Conecta tu repositorio de GitHub
3. Crea un nuevo **Web Service**
4. Selecciona tu repositorio

### 3. Configuración del servicio
- **Name**: `bgr-shrimp-bot`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python start.py`

### 4. Variables de entorno
Configura estas variables en el dashboard de Render:

**Obligatorias:**
- `TWILIO_ACCOUNT_SID`: Tu Account SID de Twilio
- `TWILIO_AUTH_TOKEN`: Tu Auth Token de Twilio
- `TWILIO_WHATSAPP_NUMBER`: `whatsapp:+14155238886`

**Opcionales:**
- `OPENAI_API_KEY`: Para funcionalidad de IA (opcional)
- `DEBUG`: `false` (para producción)
- `ENVIRONMENT`: `production`

### 5. Configurar Webhook en Twilio
Una vez desplegado, tu URL será algo como:
```
https://bgr-shrimp-bot.onrender.com
```

Configura el webhook en Twilio:
- **URL**: `https://tu-app.onrender.com/webhook/whatsapp`
- **Method**: `POST`

### 6. Probar el despliegue
1. Envía un mensaje al sandbox de WhatsApp
2. Verifica los logs en Render
3. Confirma que el bot responde correctamente

## 📋 Checklist de despliegue

- [ ] Repositorio actualizado en GitHub
- [ ] Variables de entorno configuradas en Render
- [ ] Servicio desplegado exitosamente
- [ ] Webhook configurado en Twilio
- [ ] Bot probado y funcionando

## 🔧 Troubleshooting

### Error: "Module not found"
- Verifica que `requirements.txt` esté actualizado
- Asegúrate de que el build command sea correcto

### Error: "Port already in use"
- Render asigna automáticamente el puerto via variable `PORT`
- No hardcodees el puerto en tu código

### Error: "Excel file not found"
- Verifica que el archivo Excel esté en el repositorio
- Confirma la ruta en la variable `EXCEL_PATH`

### Webhook no funciona
- Verifica que la URL del webhook sea correcta
- Confirma que el método sea POST
- Revisa los logs de Render para errores

## 💡 Consejos

1. **Logs**: Usa los logs de Render para debuggear
2. **Health Check**: Usa `/health` para verificar que el servicio esté funcionando
3. **Actualizaciones**: Los cambios en GitHub se despliegan automáticamente
4. **Costos**: Render tiene un plan gratuito con limitaciones, considera el plan pagado para producción

## 📞 URLs importantes

- **Dashboard**: https://dashboard.render.com
- **Docs**: https://render.com/docs
- **Twilio Console**: https://console.twilio.com