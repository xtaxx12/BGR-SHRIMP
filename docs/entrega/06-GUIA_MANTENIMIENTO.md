# Guía de Mantenimiento - BGR Shrimp Bot

## Tabla de Contenidos

1. [Mantenimiento Preventivo](#mantenimiento-preventivo)
2. [Procedimientos de Actualización](#procedimientos-de-actualización)
3. [Backup y Restauración](#backup-y-restauración)
4. [Monitoreo y Alertas](#monitoreo-y-alertas)
5. [Optimización de Performance](#optimización-de-performance)
6. [Gestión de Logs](#gestión-de-logs)
7. [Actualización de Datos](#actualización-de-datos)
8. [Calendario de Mantenimiento](#calendario-de-mantenimiento)

---

## Mantenimiento Preventivo

### Tareas Diarias

#### 1. Verificar Health Check

**Frecuencia:** Cada mañana (9:00 AM)

**Procedimiento:**
```bash
# Verificar estado del sistema
curl https://bgr-shrimp.onrender.com/health

# Verificar que todos los componentes están "true"
# Si alguno está "false", investigar inmediatamente
```

**Acción si falla:**
- Revisar logs de error
- Verificar conectividad con servicios externos
- Contactar soporte si persiste

#### 2. Revisar Logs de Error

**Frecuencia:** Diaria

**Procedimiento:**
```bash
# Ver últimos errores
tail -n 50 logs/errors.log

# Buscar errores críticos
grep "CRITICAL\|ERROR" logs/errors.log | tail -n 20

# Verificar si hay patrones repetitivos
```

**Acción si hay errores:**
- Documentar errores recurrentes
- Crear tickets para bugs
- Aplicar fixes si es necesario

#### 3. Monitorear Métricas de Performance

**Frecuencia:** Diaria

**Procedimiento:**
```bash
# Verificar tiempos de respuesta
grep "process_time" logs/app.log | tail -n 100 | \
  awk '{sum+=$NF; count++} END {print "Promedio:", sum/count, "segundos"}'

# Verificar tasa de error
grep "status_code" logs/app.log | tail -n 1000 | \
  grep -c "500\|503"
```

**Métricas objetivo:**
- Tiempo de respuesta promedio: < 2 segundos
- Tasa de error: < 1%
- Uptime: > 99.9%

---

### Tareas Semanales

#### 1. Limpiar PDFs Antiguos

**Frecuencia:** Cada lunes

**Procedimiento:**
```bash
# Listar PDFs antiguos (> 7 días)
find generated_pdfs/ -name "*.pdf" -mtime +7

# Eliminar PDFs antiguos
find generated_pdfs/ -name "*.pdf" -mtime +7 -delete

# Verificar espacio liberado
du -sh generated_pdfs/
```

**Espacio esperado:**
- < 500MB en directorio de PDFs
- Si excede, reducir tiempo de retención

#### 2. Revisar Sesiones Activas

**Frecuencia:** Cada viernes

**Procedimiento:**
```bash
# Ver cantidad de sesiones
cat data/sessions.json | jq 'length'

# Ver sesiones antiguas (> 24 horas)
python -c "
import json
from datetime import datetime, timedelta

with open('data/sessions.json') as f:
    sessions = json.load(f)

old_sessions = []
cutoff = datetime.now() - timedelta(hours=24)

for user_id, session in sessions.items():
    updated = datetime.fromisoformat(session['updated_at'])
    if updated < cutoff:
        old_sessions.append(user_id)

print(f'Sesiones antiguas: {len(old_sessions)}')
"

# Limpiar sesiones antiguas si es necesario
```

#### 3. Analizar Métricas de Negocio

**Frecuencia:** Cada viernes

**Procedimiento:**
```bash
# Contar cotizaciones generadas esta semana
grep "quote_generated" logs/business.log | \
  grep "$(date -d '7 days ago' +%Y-%m-%d)" | wc -l

# Contar PDFs generados
grep "pdf_generated" logs/business.log | \
  grep "$(date -d '7 days ago' +%Y-%m-%d)" | wc -l

# Productos más consultados
grep "price_query" logs/business.log | \
  grep -o '"product":"[^"]*"' | sort | uniq -c | sort -rn | head -10
```

**Generar reporte:**
- Cotizaciones totales
- PDFs generados
- Productos más consultados
- Usuarios más activos
- Tiempo de respuesta promedio

#### 4. Verificar Integraciones Externas

**Frecuencia:** Cada miércoles

**Procedimiento:**
```bash
# Test de Twilio
curl -X GET https://bgr-shrimp.onrender.com/webhook/test-twilio \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Test de Google Sheets
curl -X GET https://bgr-shrimp.onrender.com/webhook/data-status \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Verificar balance de Twilio
# Ir a Twilio Console → Account → Balance
# Alertar si balance < $10
```

---

### Tareas Mensuales

#### 1. Actualizar Dependencias

**Frecuencia:** Primer lunes de cada mes

**Procedimiento:**
```bash
# 1. Verificar actualizaciones disponibles
pip list --outdated

# 2. Revisar changelogs de paquetes críticos
# - fastapi
# - twilio
# - openai
# - gspread

# 3. Actualizar en entorno de staging primero
pip install --upgrade <package>

# 4. Ejecutar tests
pytest tests/ --cov=app

# 5. Si tests pasan, actualizar requirements.txt
pip freeze > requirements.txt

# 6. Desplegar a staging
git add requirements.txt
git commit -m "chore: update dependencies"
git push staging main

# 7. Verificar en staging por 24 horas

# 8. Si todo OK, desplegar a producción
git push origin main
```

**Paquetes críticos a monitorear:**
- `fastapi` - Framework web
- `twilio` - Cliente Twilio
- `openai` - Cliente OpenAI
- `gspread` - Google Sheets
- `reportlab` - Generación de PDFs

#### 2. Backup Completo del Sistema

**Frecuencia:** Primer domingo de cada mes

**Procedimiento:**
```bash
# Crear directorio de backup
mkdir -p backups/$(date +%Y%m)

# Backup de sesiones
cp data/sessions.json backups/$(date +%Y%m)/sessions_$(date +%Y%m%d).json

# Backup de PDFs (últimos 30 días)
tar -czf backups/$(date +%Y%m)/pdfs_$(date +%Y%m%d).tar.gz \
  $(find generated_pdfs/ -name "*.pdf" -mtime -30)

# Backup de logs
tar -czf backups/$(date +%Y%m)/logs_$(date +%Y%m%d).tar.gz logs/

# Backup de configuración
cp .env backups/$(date +%Y%m)/env_$(date +%Y%m%d).txt

# Backup de Excel local
cp data/CALCULO_DE_PRECIOS-AGUAJE17.xlsx \
  backups/$(date +%Y%m)/excel_$(date +%Y%m%d).xlsx

# Verificar backups
ls -lh backups/$(date +%Y%m)/

# Subir a almacenamiento externo (opcional)
# aws s3 sync backups/ s3://bgr-backups/
```

#### 3. Revisión de Seguridad

**Frecuencia:** Mensual

**Procedimiento:**
```bash
# 1. Verificar logs de seguridad
grep "401\|403\|429" logs/security.log | tail -n 100

# 2. Verificar intentos de acceso no autorizado
grep "Invalid token\|Invalid signature" logs/security.log

# 3. Revisar rate limiting
grep "Too many requests" logs/app.log | \
  grep -o "whatsapp:[+0-9]*" | sort | uniq -c | sort -rn

# 4. Verificar headers de seguridad
curl -I https://bgr-shrimp.onrender.com/health | \
  grep -E "X-Content-Type-Options|X-Frame-Options|Strict-Transport-Security"

# 5. Escanear vulnerabilidades
pip-audit

# 6. Verificar certificado SSL
echo | openssl s_client -servername bgr-shrimp.onrender.com \
  -connect bgr-shrimp.onrender.com:443 2>/dev/null | \
  openssl x509 -noout -dates
```

#### 4. Optimización de Base de Datos

**Frecuencia:** Mensual

**Procedimiento:**
```bash
# 1. Verificar tamaño de sessions.json
du -h data/sessions.json

# 2. Si > 10MB, limpiar sesiones antiguas
python -c "
import json
from datetime import datetime, timedelta

with open('data/sessions.json') as f:
    sessions = json.load(f)

cutoff = datetime.now() - timedelta(days=7)
cleaned = {}

for user_id, session in sessions.items():
    updated = datetime.fromisoformat(session['updated_at'])
    if updated > cutoff:
        cleaned[user_id] = session

with open('data/sessions.json', 'w') as f:
    json.dump(cleaned, f, indent=2)

print(f'Sesiones antes: {len(sessions)}')
print(f'Sesiones después: {len(cleaned)}')
"

# 3. Verificar nuevo tamaño
du -h data/sessions.json
```

---

## Procedimientos de Actualización

### Actualización del Sistema

#### Actualización Menor (Bug Fixes)

**Ejemplo:** v2.0.0 → v2.0.1

**Procedimiento:**
```bash
# 1. Crear rama de fix
git checkout -b fix/bug-description

# 2. Aplicar fix y tests
# ... hacer cambios ...
pytest tests/

# 3. Commit y push
git add .
git commit -m "fix: descripción del bug"
git push origin fix/bug-description

# 4. Crear Pull Request
# Revisar y aprobar

# 5. Merge a main
git checkout main
git merge fix/bug-description

# 6. Tag de versión
git tag v2.0.1
git push origin v2.0.1

# 7. Deploy automático
# Render/Railway detecta push y despliega

# 8. Verificar deployment
curl https://bgr-shrimp.onrender.com/health

# 9. Monitorear por 1 hora
tail -f logs/app.log
```

#### Actualización Mayor (Nuevas Funcionalidades)

**Ejemplo:** v2.0.0 → v2.1.0

**Procedimiento:**
```bash
# 1. Crear rama de feature
git checkout -b feature/nueva-funcionalidad

# 2. Desarrollar feature
# ... hacer cambios ...

# 3. Tests completos
pytest tests/ --cov=app
python scripts/validate_critical_points.py

# 4. Deploy a staging
git push staging feature/nueva-funcionalidad

# 5. Testing en staging (mínimo 48 horas)
# - Tests funcionales
# - Tests de carga
# - Tests de integración

# 6. Si OK, merge a main
git checkout main
git merge feature/nueva-funcionalidad

# 7. Tag de versión
git tag v2.1.0
git push origin v2.1.0

# 8. Deploy a producción
# Automático con push

# 9. Monitoreo intensivo (24 horas)
# - Health checks cada 5 minutos
# - Revisar logs cada hora
# - Verificar métricas

# 10. Comunicar a stakeholders
# Email con changelog y mejoras
```

### Rollback de Actualización

**Cuándo hacer rollback:**
- Tasa de error > 5%
- Tiempo de respuesta > 5 segundos
- Funcionalidad crítica no funciona
- Pérdida de datos

**Procedimiento:**
```bash
# 1. Identificar versión anterior estable
git log --oneline

# 2. Revertir a versión anterior
git revert <commit-hash>
git push origin main

# 3. O hacer rollback en Render/Railway
# Dashboard → Deploys → Select previous deploy → Redeploy

# 4. Verificar que sistema funciona
curl https://bgr-shrimp.onrender.com/health
pytest tests/

# 5. Restaurar datos si es necesario
cp backups/sessions_latest.json data/sessions.json

# 6. Comunicar incidente
# Email a stakeholders con:
# - Qué falló
# - Qué se hizo
# - Estado actual
# - Próximos pasos

# 7. Post-mortem
# Documentar causa raíz
# Crear plan de prevención
```

---


## Backup y Restauración

### Estrategia de Backup

**Tipos de Backup:**

1. **Backup Diario Automático** (Sesiones)
2. **Backup Semanal** (PDFs recientes)
3. **Backup Mensual Completo** (Todo el sistema)

### Backup Manual

#### Backup de Sesiones

```bash
# Crear backup
cp data/sessions.json backups/sessions_$(date +%Y%m%d_%H%M%S).json

# Verificar backup
cat backups/sessions_$(date +%Y%m%d)*.json | jq . > /dev/null && echo "OK"

# Comprimir backups antiguos
find backups/ -name "sessions_*.json" -mtime +7 -exec gzip {} \;
```

#### Backup de PDFs

```bash
# Backup de PDFs recientes (últimos 7 días)
tar -czf backups/pdfs_$(date +%Y%m%d).tar.gz \
  $(find generated_pdfs/ -name "*.pdf" -mtime -7)

# Verificar contenido
tar -tzf backups/pdfs_$(date +%Y%m%d).tar.gz | head -10

# Tamaño del backup
du -h backups/pdfs_$(date +%Y%m%d).tar.gz
```

#### Backup de Logs

```bash
# Backup de logs del último mes
tar -czf backups/logs_$(date +%Y%m%d).tar.gz \
  $(find logs/ -name "*.log" -mtime -30)

# Verificar
tar -tzf backups/logs_$(date +%Y%m%d).tar.gz
```

#### Backup de Configuración

```bash
# Backup de variables de entorno (sin valores sensibles)
cat .env | grep -v "TOKEN\|KEY\|SECRET\|PASSWORD" > \
  backups/env_structure_$(date +%Y%m%d).txt

# Backup de archivos de configuración
tar -czf backups/config_$(date +%Y%m%d).tar.gz \
  .env.example \
  render.yaml \
  railway.json \
  Procfile \
  requirements.txt
```

### Restauración

#### Restaurar Sesiones

```bash
# 1. Detener servicio (opcional)
# En Render/Railway dashboard

# 2. Backup de sesiones actuales
cp data/sessions.json data/sessions_backup_$(date +%Y%m%d).json

# 3. Restaurar desde backup
cp backups/sessions_20250130.json data/sessions.json

# 4. Verificar integridad
cat data/sessions.json | jq . > /dev/null && echo "OK"

# 5. Reiniciar servicio
# En Render/Railway dashboard

# 6. Verificar funcionamiento
curl https://bgr-shrimp.onrender.com/health
```

#### Restaurar PDFs

```bash
# 1. Extraer backup
tar -xzf backups/pdfs_20250130.tar.gz -C generated_pdfs/

# 2. Verificar archivos restaurados
ls -lh generated_pdfs/ | tail -20

# 3. Verificar que PDFs son accesibles
curl -I https://bgr-shrimp.onrender.com/webhook/download-pdf/[filename].pdf
```

#### Restaurar Logs

```bash
# 1. Extraer backup
tar -xzf backups/logs_20250130.tar.gz -C logs/

# 2. Verificar logs restaurados
ls -lh logs/

# 3. Verificar contenido
tail -n 20 logs/app.log
```

### Backup Automático con Cron

**Script de Backup Automático:**

```bash
#!/bin/bash
# backup.sh - Script de backup automático

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d)

# Crear directorio de backup
mkdir -p $BACKUP_DIR/$DATE

# Backup de sesiones
cp data/sessions.json $BACKUP_DIR/$DATE/sessions.json

# Backup de PDFs recientes
tar -czf $BACKUP_DIR/$DATE/pdfs.tar.gz \
  $(find generated_pdfs/ -name "*.pdf" -mtime -7)

# Backup de logs
tar -czf $BACKUP_DIR/$DATE/logs.tar.gz logs/

# Limpiar backups antiguos (> 30 días)
find $BACKUP_DIR -type d -mtime +30 -exec rm -rf {} \;

# Log de backup
echo "$(date): Backup completado" >> $BACKUP_DIR/backup.log
```

**Configurar Cron:**

```bash
# Editar crontab
crontab -e

# Agregar línea para backup diario a las 2 AM
0 2 * * * /path/to/backup.sh

# Verificar cron
crontab -l
```

### Backup en la Nube

**AWS S3:**

```bash
# Instalar AWS CLI
pip install awscli

# Configurar credenciales
aws configure

# Subir backups a S3
aws s3 sync backups/ s3://bgr-backups/

# Verificar
aws s3 ls s3://bgr-backups/
```

**Google Cloud Storage:**

```bash
# Instalar gsutil
pip install gsutil

# Autenticar
gcloud auth login

# Subir backups
gsutil -m rsync -r backups/ gs://bgr-backups/

# Verificar
gsutil ls gs://bgr-backups/
```

---

## Monitoreo y Alertas

### Configurar UptimeRobot

**Paso 1: Crear Cuenta**
1. Ir a https://uptimerobot.com
2. Crear cuenta gratuita
3. Verificar email

**Paso 2: Agregar Monitor**
1. Dashboard → Add New Monitor
2. Monitor Type: HTTP(s)
3. Friendly Name: BGR Shrimp Bot
4. URL: https://bgr-shrimp.onrender.com/health
5. Monitoring Interval: 5 minutes
6. Monitor Timeout: 30 seconds

**Paso 3: Configurar Alertas**
1. Alert Contacts → Add Alert Contact
2. Email: tu-email@bgr.com
3. WhatsApp: +593968058769 (vía integración)
4. Alert When: Down

**Paso 4: Verificar**
- Esperar 5 minutos
- Verificar que monitor está "Up"
- Probar alerta deteniendo servicio

### Configurar Sentry (Error Tracking)

**Paso 1: Crear Proyecto**
1. Ir a https://sentry.io
2. Crear cuenta
3. Create Project → Python → FastAPI

**Paso 2: Instalar SDK**
```bash
pip install sentry-sdk[fastapi]
```

**Paso 3: Configurar en Código**
```python
# En app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://xxx@xxx.ingest.sentry.io/xxx",
    integrations=[FastApiIntegration()],
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1
)
```

**Paso 4: Configurar Variable de Entorno**
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

**Paso 5: Verificar**
```python
# Test de Sentry
sentry_sdk.capture_message("Test message from BGR Shrimp Bot")
```

### Alertas Personalizadas

**Script de Monitoreo:**

```python
#!/usr/bin/env python3
# monitor.py - Script de monitoreo personalizado

import requests
import smtplib
from email.mime.text import MIMEText
import time

def check_health():
    """Verifica health del sistema"""
    try:
        response = requests.get(
            "https://bgr-shrimp.onrender.com/health",
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking health: {e}")
        return False

def send_alert(message):
    """Envía alerta por email"""
    msg = MIMEText(message)
    msg['Subject'] = 'ALERTA: BGR Shrimp Bot'
    msg['From'] = 'alerts@bgr.com'
    msg['To'] = 'admin@bgr.com'
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('alerts@bgr.com', 'password')
        server.send_message(msg)

def main():
    """Loop principal de monitoreo"""
    consecutive_failures = 0
    
    while True:
        if check_health():
            consecutive_failures = 0
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: System healthy")
        else:
            consecutive_failures += 1
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: System unhealthy")
            
            if consecutive_failures >= 3:
                send_alert(f"Sistema caído por {consecutive_failures} checks consecutivos")
                consecutive_failures = 0  # Reset para no enviar spam
        
        time.sleep(300)  # Check cada 5 minutos

if __name__ == "__main__":
    main()
```

**Ejecutar como Servicio:**

```bash
# Crear servicio systemd
sudo nano /etc/systemd/system/bgr-monitor.service

[Unit]
Description=BGR Shrimp Bot Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 /path/to/monitor.py
Restart=always

[Install]
WantedBy=multi-user.target

# Habilitar y iniciar
sudo systemctl enable bgr-monitor
sudo systemctl start bgr-monitor

# Verificar status
sudo systemctl status bgr-monitor
```

---

## Optimización de Performance

### Análisis de Performance

**Identificar Cuellos de Botella:**

```bash
# 1. Analizar tiempos de respuesta
grep "process_time" logs/app.log | \
  awk '{print $NF}' | \
  sort -n | \
  awk '{
    sum+=$1; 
    arr[NR]=$1
  } 
  END {
    print "Min:", arr[1];
    print "Max:", arr[NR];
    print "Avg:", sum/NR;
    print "Median:", arr[int(NR/2)]
  }'

# 2. Identificar endpoints lentos
grep "process_time" logs/app.log | \
  grep -o '"path":"[^"]*".*"process_time":[0-9.]*' | \
  awk -F'"' '{print $4, $NF}' | \
  sort -k2 -rn | \
  head -10

# 3. Analizar uso de memoria
ps aux | grep python | awk '{print $6/1024 " MB"}'

# 4. Analizar uso de CPU
top -b -n 1 | grep python
```

### Optimizaciones Comunes

#### 1. Implementar Cache

```python
# Cache de precios de Google Sheets
from functools import lru_cache
from datetime import datetime, timedelta

class CachedPricingService:
    def __init__(self):
        self.cache_expiry = datetime.now()
        self.cache_duration = timedelta(minutes=5)
    
    @lru_cache(maxsize=100)
    def get_price_cached(self, product, size):
        # Verificar si cache expiró
        if datetime.now() > self.cache_expiry:
            self.get_price_cached.cache_clear()
            self.cache_expiry = datetime.now() + self.cache_duration
        
        return self.google_sheets_service.get_price(product, size)
```

#### 2. Optimizar Queries a Google Sheets

```python
# Cargar todos los datos una vez
class OptimizedGoogleSheetsService:
    def __init__(self):
        self.data_cache = {}
        self.last_reload = None
        
    def get_all_data(self):
        # Recargar solo si han pasado 5 minutos
        if (not self.last_reload or 
            datetime.now() - self.last_reload > timedelta(minutes=5)):
            self.data_cache = self.sheet.get_all_records()
            self.last_reload = datetime.now()
        
        return self.data_cache
    
    def get_price(self, product, size):
        data = self.get_all_data()
        # Buscar en cache local
        for row in data:
            if row['producto'] == product and row['talla'] == size:
                return row['precio']
        return None
```

#### 3. Optimizar Generación de PDFs

```python
# Reducir calidad de imágenes
from PIL import Image

def optimize_logo(logo_path):
    img = Image.open(logo_path)
    # Reducir tamaño si es muy grande
    if img.width > 500:
        ratio = 500 / img.width
        new_size = (500, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    # Guardar optimizado
    img.save(logo_path, optimize=True, quality=85)
```

#### 4. Usar Async para Operaciones I/O

```python
# Operaciones asíncronas
import asyncio
import aiohttp

async def send_multiple_messages(messages):
    """Envía múltiples mensajes en paralelo"""
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_message_async(session, msg)
            for msg in messages
        ]
        return await asyncio.gather(*tasks)
```

### Monitoreo de Performance

**Métricas a Monitorear:**

1. **Tiempo de Respuesta**
   - Objetivo: < 2 segundos promedio
   - Alerta si: > 5 segundos

2. **Uso de Memoria**
   - Objetivo: < 512MB
   - Alerta si: > 800MB

3. **Uso de CPU**
   - Objetivo: < 70%
   - Alerta si: > 90%

4. **Tasa de Error**
   - Objetivo: < 1%
   - Alerta si: > 5%

5. **Uptime**
   - Objetivo: 99.9%
   - Alerta si: < 99%

---

## Gestión de Logs

### Rotación de Logs

**Configuración de Rotación:**

```python
# En logging_config.py
import logging.handlers

def setup_logging():
    # Handler con rotación
    handler = logging.handlers.RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=30,     # Mantener 30 archivos
        encoding='utf-8'
    )
    
    # También rotación por tiempo
    time_handler = logging.handlers.TimedRotatingFileHandler(
        'logs/app.log',
        when='midnight',
        interval=1,
        backupCount=30
    )
```

### Análisis de Logs

**Comandos Útiles:**

```bash
# Errores más comunes
grep "ERROR" logs/errors.log | \
  grep -o '"message":"[^"]*"' | \
  sort | uniq -c | sort -rn | head -10

# Usuarios más activos
grep "user_id" logs/app.log | \
  grep -o '"user_id":"[^"]*"' | \
  sort | uniq -c | sort -rn | head -10

# Endpoints más usados
grep "path" logs/app.log | \
  grep -o '"path":"[^"]*"' | \
  sort | uniq -c | sort -rn | head -10

# Tiempos de respuesta por hora
grep "process_time" logs/app.log | \
  awk '{print substr($1,12,2), $NF}' | \
  awk '{sum[$1]+=$2; count[$1]++} END {
    for (hour in sum) 
      print hour":00 -", sum[hour]/count[hour], "segundos"
  }' | sort
```

### Limpieza de Logs

```bash
# Comprimir logs antiguos (> 7 días)
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;

# Eliminar logs muy antiguos (> 90 días)
find logs/ -name "*.log.gz" -mtime +90 -delete

# Verificar espacio usado
du -sh logs/
```

---

## Actualización de Datos

### Actualizar Precios en Google Sheets

**Procedimiento:**

1. **Editar Google Sheet**
   - Ir a Google Sheets
   - Abrir hoja de precios
   - Actualizar valores

2. **Recargar Datos en el Sistema**
   ```bash
   curl -X POST https://bgr-shrimp.onrender.com/webhook/reload-data \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

3. **Verificar Actualización**
   ```bash
   # Verificar que datos se cargaron
   curl -X GET https://bgr-shrimp.onrender.com/webhook/data-status \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   
   # Probar consulta de precio
   # Enviar mensaje de WhatsApp con producto actualizado
   ```

### Actualizar Excel Local

**Procedimiento:**

1. **Backup del Excel Actual**
   ```bash
   cp data/CALCULO_DE_PRECIOS-AGUAJE17.xlsx \
     backups/excel_$(date +%Y%m%d).xlsx
   ```

2. **Reemplazar Excel**
   ```bash
   # Copiar nuevo archivo
   cp /path/to/nuevo_excel.xlsx data/CALCULO_DE_PRECIOS-AGUAJE17.xlsx
   ```

3. **Verificar Formato**
   ```python
   # Verificar que Excel tiene estructura correcta
   python -c "
   from app.services.excel import ExcelService
   svc = ExcelService()
   products = svc.get_all_products()
   print(f'Productos cargados: {len(products)}')
   "
   ```

4. **Reiniciar Servicio**
   ```bash
   # En Render/Railway dashboard
   # Manual Deploy → Restart
   ```

### Agregar Nuevo Producto

**En Google Sheets:**

1. Agregar fila con:
   - Producto (ej: "NUEVO_PRODUCTO")
   - Talla (ej: "16/20")
   - Precio FOB
   - Disponibilidad
   - Origen

2. Recargar datos:
   ```bash
   curl -X POST https://bgr-shrimp.onrender.com/webhook/reload-data \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

3. Probar:
   ```
   # Enviar mensaje de WhatsApp
   "NUEVO_PRODUCTO 16/20"
   ```

**En Código (si requiere lógica especial):**

```python
# En app/services/pricing.py
VALID_PRODUCTS = [
    'HOSO', 'HLSO', 'P&D IQF', 'P&D BLOQUE',
    'EZ PEEL', 'PuD-EUROPA', 'PuD-EEUU', 'COOKED',
    'NUEVO_PRODUCTO'  # Agregar aquí
]
```

---

## Calendario de Mantenimiento

### Resumen de Tareas

| Frecuencia | Tarea | Tiempo Estimado | Responsable |
|------------|-------|-----------------|-------------|
| **Diaria** | Health check | 5 min | Admin |
| **Diaria** | Revisar logs de error | 10 min | Admin |
| **Diaria** | Monitorear métricas | 10 min | Admin |
| **Semanal** | Limpiar PDFs antiguos | 15 min | Admin |
| **Semanal** | Revisar sesiones | 15 min | Admin |
| **Semanal** | Analizar métricas de negocio | 30 min | Admin |
| **Semanal** | Verificar integraciones | 20 min | Admin |
| **Mensual** | Actualizar dependencias | 2 horas | Dev |
| **Mensual** | Backup completo | 30 min | Admin |
| **Mensual** | Revisión de seguridad | 1 hora | Dev |
| **Mensual** | Optimización de BD | 30 min | Admin |

### Checklist Mensual

```markdown
## Checklist de Mantenimiento - [Mes/Año]

### Semana 1
- [ ] Lunes: Limpiar PDFs antiguos
- [ ] Miércoles: Verificar integraciones
- [ ] Viernes: Analizar métricas semanales
- [ ] Domingo: Backup completo

### Semana 2
- [ ] Lunes: Actualizar dependencias
- [ ] Miércoles: Revisión de seguridad
- [ ] Viernes: Analizar métricas semanales

### Semana 3
- [ ] Lunes: Limpiar PDFs antiguos
- [ ] Miércoles: Verificar integraciones
- [ ] Viernes: Analizar métricas semanales
- [ ] Domingo: Optimización de BD

### Semana 4
- [ ] Lunes: Limpiar PDFs antiguos
- [ ] Miércoles: Verificar integraciones
- [ ] Viernes: Analizar métricas semanales y reporte mensual

### Tareas Adicionales
- [ ] Revisar y actualizar documentación
- [ ] Revisar tickets de soporte
- [ ] Planificar mejoras para próximo mes
```

---

## Contacto de Mantenimiento

**Soporte Técnico:**
- Email: rojassebas765@gmail.com
- WhatsApp: +593 968058769
- Horario: 24/7 para emergencias

**Escalamiento:**
1. Contactar por WhatsApp (respuesta < 30 min)
2. Si no responde, email (respuesta < 1 hora)
3. Para emergencias críticas, llamar directamente

---

**Versión:** 1.0  
**Última Actualización:** Enero 2025  
**Para:** BGR Export  
**Confidencialidad:** Uso interno
