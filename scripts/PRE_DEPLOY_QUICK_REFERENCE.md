# Checklist de Pre-Despliegue - Guía Rápida

## Ejecución Rápida

```bash
python scripts/pre_deploy_checklist.py
```

## Checklist Manual

Antes de ejecutar el script, verifica manualmente:

### ✅ Variables de Entorno Críticas

```bash
# Verificar que estén configuradas
echo $TWILIO_ACCOUNT_SID
echo $TWILIO_AUTH_TOKEN
echo $SECRET_KEY
echo $ENVIRONMENT
echo $DEBUG
```

### ✅ Archivos Requeridos

- [ ] `data/CALCULO_DE _PRECIOS-AGUAJE17.xlsx` existe
- [ ] `logs/` directorio existe y es escribible
- [ ] `.env` configurado correctamente

### ✅ Servicios Externos

- [ ] Twilio: Cuenta activa y credenciales válidas
- [ ] Google Sheets: (Opcional) Credenciales configuradas
- [ ] OpenAI: (Opcional) API key válida

### ✅ Configuración de Seguridad

- [ ] `DEBUG=false` en producción
- [ ] `ENVIRONMENT=production` en producción
- [ ] `SECRET_KEY` configurada (32+ caracteres)
- [ ] `BASE_URL` usa HTTPS
- [ ] `ALLOWED_HOSTS` no es '*' en producción
- [ ] `CORS_ORIGINS` no es '*' en producción

### ✅ Sistema de Logs

- [ ] Directorio `logs/` existe
- [ ] Permisos de escritura en `logs/`
- [ ] Archivos de log se crean correctamente

## Resultado Esperado

```
✅ SISTEMA LISTO PARA DESPLIEGUE
```

## Si Hay Fallos Críticos

1. **Revisar el reporte**: `pre_deploy_checklist_report.json`
2. **Identificar fallos críticos**: Sección `critical_failures`
3. **Corregir cada fallo** según la documentación
4. **Re-ejecutar el checklist**
5. **Repetir hasta que pase**

## Comandos Útiles

### Generar SECRET_KEY
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Generar ADMIN_API_TOKEN
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Verificar Conectividad Twilio
```bash
curl -X GET "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID.json" \
  -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN"
```

### Verificar Archivo Excel
```bash
python -c "import openpyxl; wb = openpyxl.load_workbook('data/CALCULO_DE _PRECIOS-AGUAJE17.xlsx'); print(f'Hojas: {len(wb.sheetnames)}')"
```

## Tiempos Estimados

- **Ejecución completa**: ~10-15 segundos
- **Con todos los servicios**: ~8-10 segundos
- **Solo verificaciones locales**: ~2-3 segundos

## Contacto

Para soporte, contactar al equipo de desarrollo.
