# 🦐 ShrimpBot - BGR Export WhatsApp Bot v2.0

Bot empresarial de WhatsApp para consultas de precios de camarón de BGR Export con arquitectura mejorada, seguridad robusta y mejores prácticas de desarrollo.

## ✨ Características Principales

### 🚀 Funcionalidades de Negocio
- 🤖 **Interfaz conversacional inteligente** con IA opcional (OpenAI)
- 📊 **Datos en tiempo real** desde Google Sheets con fallback a Excel local
- 🧮 **Cálculos automáticos precisos** usando fórmulas empresariales
- 🦐 **Catálogo completo de productos**: HOSO, HLSO, P&D IQF, P&D BLOQUE, etc.
- 📏 **Todas las tallas disponibles** con inventario en tiempo real
- 💰 **Cotizaciones detalladas** con cálculos FOB, Glaseo y Flete
- 🌍 **Soporte multi-destino** con costos de flete personalizados
- 📄 **Generación de PDFs profesionales** en múltiples idiomas (ES/EN)
- 🎤 **Transcripción de mensajes de audio** vía OpenAI

### 🔒 Mejoras de Seguridad v2.0
- 🛡️ **Validación de webhooks Twilio** con firma criptográfica
- 🚦 **Rate limiting inteligente** por usuario (30 req/min)
- 🔐 **Autenticación Bearer** para endpoints administrativos
- 🧹 **Sanitización de entrada** contra inyecciones
- 📝 **Logging estructurado** con filtrado de datos sensibles
- 🔍 **Headers de seguridad** (HSTS, CSP, X-Frame-Options)
- ⚡ **Protección contra spam** y mensajes duplicados
- 🔑 **Gestión segura de secretos** con validación en producción

### 🏗️ Arquitectura Mejorada
- 📦 **Inyección de dependencias** con ServiceContainer
- 🎯 **Manejo robusto de errores** con excepciones personalizadas
- 📊 **Logging estructurado JSON** para análisis
- 🔄 **Middleware de request tracking** con IDs únicos
- 📈 **Métricas y health checks** integrados
- 🧪 **Arquitectura testeable** con separación de responsabilidades

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.11+
- Cuenta de Twilio con WhatsApp Business API
- Google Cloud Service Account (para Google Sheets)
- PostgreSQL/Redis (opcional para sesiones persistentes)

### Instalación Local

1. **Clona el repositorio**
   ```bash
   git clone https://github.com/tu-usuario/BGR-SHRIMP.git
   cd BGR-SHRIMP
   ```

2. **Crea entorno virtual**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. **Instala dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura variables de entorno**
   ```bash
   cp .env.example .env
   # Edita .env con tus credenciales
   ```

5. **Ejecuta el bot**
   ```bash
   python start.py
   ```

## 🔧 Configuración de Entorno

### Variables Críticas (Requeridas)
```bash
# Twilio WhatsApp
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Seguridad
SECRET_KEY=<genera-con-secrets.token_urlsafe(32)>
ADMIN_API_TOKEN=<token-seguro-para-admin>
ENVIRONMENT=production  # development/staging/production
```

### Variables de Datos (Recomendadas)
```bash
# Google Sheets (tiempo real)
GOOGLE_SHEETS_ID=1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_SHEETS_CREDENTIALS='{"type":"service_account",...}'

# Configuración del servidor
BASE_URL=https://tu-dominio.com
PORT=8000
DEBUG=false
```

### Variables de Seguridad Adicionales
```bash
# Rate Limiting
RATE_LIMIT_MAX_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60

# Hosts y CORS
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
CORS_ORIGINS=https://tu-frontend.com

# Límites
MAX_MESSAGE_LENGTH=1000
MAX_FILE_SIZE=10485760  # 10MB
REQUEST_TIMEOUT=30
```

## 📊 Arquitectura del Sistema

```
BGR-SHRIMP/
├── app/
│   ├── main.py              # Aplicación FastAPI con middlewares
│   ├── config.py            # Configuración centralizada
│   ├── routes.py            # Endpoints con seguridad
│   ├── dependencies.py      # Contenedor de servicios (DI)
│   ├── security.py          # Utilidades de seguridad
│   ├── exceptions.py        # Manejo de errores personalizado
│   ├── logging_config.py    # Sistema de logging estructurado
│   └── services/
│       ├── pricing.py       # Lógica de negocio principal
│       ├── google_sheets.py # Integración Google Sheets
│       ├── excel.py         # Procesamiento Excel local
│       ├── interactive.py   # Menús interactivos
│       ├── session.py       # Gestión de sesiones
│       ├── pdf_generator.py # Generación de cotizaciones
│       ├── whatsapp_sender.py # Cliente Twilio
│       ├── openai_service.py  # IA conversacional
│       └── audio_handler.py   # Procesamiento de audio
├── data/                    # Archivos de datos
├── logs/                    # Logs estructurados
├── generated_pdfs/          # PDFs generados
└── tests/                   # Suite de pruebas
```

## 🔒 Características de Seguridad

### Autenticación y Autorización
- **Webhook Validation**: Validación criptográfica de requests de Twilio
- **Bearer Auth**: Tokens para endpoints administrativos
- **Session Management**: Sesiones seguras por usuario

### Protección contra Ataques
- **Rate Limiting**: Límite configurable por IP/usuario
- **Input Validation**: Sanitización estricta de entrada
- **CORS Policy**: Control de orígenes permitidos
- **Security Headers**: Protección XSS, Clickjacking, etc.

### Privacidad y Compliance
- **Data Sanitization**: Filtrado automático de datos sensibles en logs
- **Secure File Handling**: Manejo seguro de archivos temporales
- **Audit Logging**: Registro de eventos de seguridad

## 📱 Uso del Bot

### Comandos Principales
- `menu` - Menú principal interactivo
- `precios` - Consulta directa de precios
- `confirmar` - Generar PDF de cotización
- `idioma` - Cambiar idioma de proformas
- `ayuda` - Mostrar comandos disponibles

### Flujo de Cotización
1. **Consulta** → "Precio HLSO 16/20"
2. **Respuesta** → Cotización detallada con cálculos
3. **Confirmación** → "confirmar"
4. **Idioma** → Selección ES/EN
5. **PDF** → Envío automático por WhatsApp

### Consultas Inteligentes
```
"Necesito precio de HLSO 16/20 para China"
"Cotización P&D IQF 21/25 con 10% glaseo"
"15000 libras de EZ PEEL 26/30 destino Houston"
"Generar proforma para Juan Pérez"
```

## 🔧 Endpoints Administrativos

### Gestión del Sistema
```bash
# Health Check
GET /health
Authorization: Bearer <token>

# Recargar datos
POST /webhook/reload-data
Authorization: Bearer <admin-token>

# Estado de datos
GET /webhook/data-status
Authorization: Bearer <admin-token>

# Test de Twilio
GET /webhook/test-twilio
Authorization: Bearer <admin-token>
```

## 📈 Monitoreo y Logs

### Sistema de Logging
- **Structured Logging**: Formato JSON para análisis
- **Log Rotation**: Rotación diaria automática
- **Error Tracking**: Logs separados para errores
- **Security Audit**: Log específico de eventos de seguridad
- **Business Events**: Métricas de negocio (cotizaciones, PDFs)

### Archivos de Log
```
logs/
├── app.log          # Log general de aplicación
├── errors.log       # Errores y excepciones
├── security.log     # Eventos de seguridad
└── business.log     # Métricas de negocio
```

## 🚀 Despliegue en Producción

### Checklist de Seguridad
- [ ] `DEBUG=false` y `ENVIRONMENT=production`
- [ ] `SECRET_KEY` única y segura
- [ ] `ADMIN_API_TOKEN` configurado
- [ ] `ALLOWED_HOSTS` restringido
- [ ] HTTPS habilitado con certificado válido
- [ ] Backup de datos configurado
- [ ] Monitoreo de errores activo
- [ ] Rate limiting ajustado

### Plataformas Soportadas
- **Render**: Configuración incluida en `render.yaml`
- **Railway**: Archivo `railway.json` incluido
- **Heroku**: Compatible con `Procfile`
- **Docker**: Dockerfile disponible
- **VPS**: Scripts de deployment incluidos

## 🧪 Testing

```bash
# Ejecutar tests unitarios
pytest tests/unit/

# Tests de integración
pytest tests/integration/

# Coverage report
pytest --cov=app tests/

# Linting y formato
ruff check app/
black app/
```

## 📊 Métricas de Performance

- **Response Time**: < 200ms promedio
- **Uptime Target**: 99.9%
- **Rate Limit**: 30 req/min por usuario
- **PDF Generation**: < 3 segundos
- **Memory Usage**: < 512MB típico

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m '🚀 Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

### Estándares de Código
- **Type Hints**: Usar tipos en todas las funciones
- **Docstrings**: Documentar clases y métodos públicos
- **Testing**: Cobertura mínima del 80%
- **Security**: Pasar análisis de seguridad

## 📄 Licencia

Proyecto privado de BGR Export. Todos los derechos reservados.

## 📞 Soporte

**Soporte Técnico:**
- Email: soporte@bgr-export.com
- WhatsApp Empresarial: +593 968058769

**Desarrollador:**
- Email: rojassebas765@gmail.com
- GitHub: @tu-usuario

---

**Versión:** 2.0.0 | **Última actualización:** Enero 2025