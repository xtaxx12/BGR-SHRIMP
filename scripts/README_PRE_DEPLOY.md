# Checklist de Pre-Despliegue Automatizado

## Descripción

Script automatizado que valida que el sistema BGR Shrimp Bot esté listo para despliegue a producción. Verifica configuración, conectividad, seguridad y monitoreo.

## Uso

```bash
python scripts/pre_deploy_checklist.py
```

## Secciones de Verificación

### 1. Variables de Entorno

#### Variables Requeridas (Críticas)
- `TWILIO_ACCOUNT_SID` - Account SID de Twilio
- `TWILIO_AUTH_TOKEN` - Token de autenticación de Twilio
- `TWILIO_WHATSAPP_NUMBER` - Número de WhatsApp de Twilio

#### Variables Opcionales
- `GOOGLE_SHEETS_ID` - ID de Google Sheets para datos en tiempo real
- `GOOGLE_SHEETS_CREDENTIALS` - Credenciales JSON de cuenta de servicio
- `OPENAI_API_KEY` - API key de OpenAI para funcionalidades avanzadas

#### Variables de Seguridad (Críticas)
- `SECRET_KEY` - Clave secreta para sesiones (mínimo 32 caracteres)
- `ADMIN_API_TOKEN` - Token para endpoints administrativos
- `ENVIRONMENT` - Debe ser 'production' en producción
- `DEBUG` - Debe ser 'false' en producción

#### Variables de Configuración
- `ALLOWED_HOSTS` - Hosts permitidos (no usar '*' en producción)
- `CORS_ORIGINS` - Orígenes CORS permitidos (no usar '*' en producción)
- `BASE_URL` - URL base del sistema (debe usar HTTPS)
- `RATE_LIMIT_MAX_REQUESTS` - Máximo de requests por ventana
- `RATE_LIMIT_WINDOW_SECONDS` - Ventana de tiempo para rate limiting

### 2. Conectividad con Servicios Externos

#### Twilio (Crítico)
- Verifica credenciales válidas
- Conecta a la API de Twilio
- Valida estado de la cuenta

#### Google Sheets (Opcional)
- Verifica credenciales de cuenta de servicio
- Conecta a Google Sheets API
- Valida acceso a la hoja de cálculo
- Si falla, el sistema usa Excel local como respaldo

#### OpenAI (Opcional)
- Verifica formato de API key
- Conecta a OpenAI API
- Valida acceso a modelos
- Si falla, funcionalidades avanzadas no estarán disponibles

#### Archivo Excel (Crítico)
- Verifica existencia del archivo
- Valida que se puede leer
- Cuenta hojas disponibles

### 3. Configuración de Seguridad

#### HTTPS (Crítico)
- Verifica que BASE_URL use HTTPS
- Permite HTTP solo en localhost/desarrollo

#### Rate Limiting
- Verifica configuración de límites
- Valida ventana de tiempo
- Alerta si los límites son muy altos

#### Tokens (Crítico)
- Verifica SECRET_KEY configurada
- Verifica TWILIO_AUTH_TOKEN configurada
- Alerta si ADMIN_API_TOKEN no está configurada

#### Headers de Seguridad
- Verifica implementación de headers de seguridad
- Valida función add_security_headers

### 4. Logs y Monitoreo

#### Directorio de Logs (Crítico)
- Verifica existencia del directorio logs/
- Valida permisos de escritura
- Crea directorio si no existe

#### Configuración de Logging
- Verifica módulo logging_config
- Lista archivos de log existentes
- Valida configuración de logging

#### Sistema de Monitoreo
- Verifica configuración de Sentry (opcional)
- Verifica habilitación de métricas (opcional)
- Valida disponibilidad de health check

#### Configuración de Backup
- Verifica existencia del directorio data/
- Valida archivo sessions.json
- Reporta tamaño de datos

## Códigos de Salida

- `0` - Sistema listo para despliegue (todas las verificaciones críticas pasaron)
- `1` - Sistema NO listo para despliegue (hay fallos críticos)
- `130` - Proceso interrumpido por el usuario
- `1` - Error inesperado durante ejecución

## Reporte Generado

El script genera un archivo `pre_deploy_checklist_report.json` con:

```json
{
  "timestamp": "2025-10-30T12:00:00.000000",
  "summary": {
    "total_checks": 16,
    "passed": 15,
    "failed": 1,
    "critical_checks": 7,
    "critical_passed": 6,
    "warnings_count": 3,
    "ready_for_deployment": false
  },
  "results": [...],
  "warnings": [...],
  "critical_failures": [...]
}
```

## Interpretación de Resultados

### ✅ Sistema Listo para Despliegue
- Todas las verificaciones críticas pasaron
- Puede haber advertencias no críticas
- Proceder con despliegue

### ⚠️ Sistema Listo con Advertencias
- Todas las verificaciones críticas pasaron
- Hay advertencias que deberían revisarse
- Proceder con precaución

### ❌ Sistema NO Listo para Despliegue
- Una o más verificaciones críticas fallaron
- NO proceder con despliegue
- Corregir fallos críticos primero

## Verificaciones Críticas

Las siguientes verificaciones son **críticas** y deben pasar para desplegar:

1. Variables de entorno requeridas (Twilio)
2. Variables de seguridad (SECRET_KEY, DEBUG)
3. Conectividad con Twilio
4. Acceso a archivo Excel
5. Configuración HTTPS
6. Configuración de tokens
7. Directorio de logs escribible

## Verificaciones No Críticas

Las siguientes verificaciones son **opcionales** pero recomendadas:

1. Variables de entorno opcionales (Google Sheets, OpenAI)
2. Configuración de producción (ALLOWED_HOSTS, CORS)
3. Conectividad con Google Sheets
4. Conectividad con OpenAI
5. Configuración de rate limiting
6. Headers de seguridad
7. Configuración de logging
8. Sistema de monitoreo
9. Configuración de backup

## Solución de Problemas Comunes

### Error: "Variables de seguridad - SECRET_KEY no configurada"

**Solución:**
```bash
# Generar SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Agregar a .env
SECRET_KEY=tu_secret_key_generada_aqui
```

### Error: "DEBUG=true en producción es un riesgo de seguridad"

**Solución:**
```bash
# En .env
DEBUG=false
```

### Error: "Conectividad con Twilio - Error conectando"

**Solución:**
1. Verificar TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN
2. Verificar conectividad a internet
3. Verificar que las credenciales sean válidas en Twilio Console

### Advertencia: "ALLOWED_HOSTS='*' permite cualquier host"

**Solución:**
```bash
# En .env - especificar hosts permitidos
ALLOWED_HOSTS=bgr-shrimp.onrender.com,www.bgr-export.com
```

### Advertencia: "ADMIN_API_TOKEN no configurada"

**Solución:**
```bash
# Generar token
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Agregar a .env
ADMIN_API_TOKEN=tu_admin_token_generado_aqui
```

## Integración con CI/CD

### GitHub Actions

```yaml
name: Pre-Deploy Checklist

on:
  push:
    branches: [ main ]

jobs:
  pre-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run pre-deploy checklist
        run: python scripts/pre_deploy_checklist.py
        env:
          TWILIO_ACCOUNT_SID: ${{ secrets.TWILIO_ACCOUNT_SID }}
          TWILIO_AUTH_TOKEN: ${{ secrets.TWILIO_AUTH_TOKEN }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          ENVIRONMENT: production
          DEBUG: false
```

### Render.com

Agregar como pre-deploy command en `render.yaml`:

```yaml
services:
  - type: web
    name: bgr-shrimp-bot
    env: python
    buildCommand: pip install -r requirements.txt
    preDeployCommand: python scripts/pre_deploy_checklist.py
    startCommand: python start.py
```

## Mantenimiento

### Agregar Nueva Verificación

1. Crear método en clase `PreDeploymentChecker`:

```python
def check_nueva_funcionalidad(self) -> Tuple[bool, str, Optional[str]]:
    """Verifica nueva funcionalidad"""
    try:
        # Lógica de verificación
        return True, "Detalles del check", None
    except Exception as e:
        return False, f"Error: {str(e)}", None
```

2. Agregar llamada en `run_all_checks()`:

```python
self.check_item("Nueva funcionalidad", 
               self.check_nueva_funcionalidad, 
               is_critical=True)  # o False
```

### Modificar Criterios de Verificación

Editar el método correspondiente en `scripts/pre_deploy_checklist.py` y ajustar la lógica de validación.

## Referencias

- [Documentación de Twilio](https://www.twilio.com/docs)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [OpenAI API](https://platform.openai.com/docs)
- [Render.com Deployment](https://render.com/docs)

## Soporte

Para problemas o preguntas sobre el checklist de pre-despliegue:
1. Revisar este README
2. Revisar el reporte JSON generado
3. Contactar al equipo de desarrollo
