# ShrimpBot - BGR Export WhatsApp Bot v2.1

Bot empresarial de WhatsApp para consultas de precios de camaron de BGR Export con arquitectura mejorada, seguridad robusta, sistema de entrenamiento de IA y mejores practicas de desarrollo.

## Caracteristicas Principales

### Funcionalidades de Negocio
- **Interfaz conversacional inteligente** con IA opcional (OpenAI)
- **Datos en tiempo real** desde Google Sheets con fallback a Excel local
- **Calculos automaticos precisos** usando formulas empresariales
- **Catalogo completo de productos**: HOSO, HLSO, P&D IQF, P&D BLOQUE, etc.
- **Todas las tallas disponibles** con inventario en tiempo real
- **Cotizaciones detalladas** con calculos FOB, Glaseo y Flete
- **Soporte multi-destino** con costos de flete personalizados
- **Generacion de PDFs profesionales** en multiples idiomas (ES/EN)
- **Transcripcion de mensajes de audio** via OpenAI

### Sistema de Entrenamiento de IA v2.1 (NUEVO)
- **RAG (Retrieval-Augmented Generation)**: Busqueda semantica con embeddings OpenAI
- **Pipeline ETL completo**: Captura -> Anonimizacion -> Analisis -> QA -> Exportacion
- **Revision Humana**: Dashboard web para validar datos de entrenamiento
- **Cumplimiento GDPR**: Consentimiento obligatorio y anonimizacion automatica
- **Fine-Tuning Ready**: Exportacion JSONL lista para OpenAI
- **Quality Assurance**: Validacion automatica de precios, productos y tallas
- **Persistencia SQLite**: Captura de mensajes que sobrevive reinicios en Render

### Mejoras de Seguridad v2.0
- **Validacion de webhooks Twilio** con firma criptografica
- **Rate limiting inteligente** por usuario (30 req/min)
- **Autenticacion Bearer** para endpoints administrativos
- **Sanitizacion de entrada** contra inyecciones
- **Logging estructurado** con filtrado de datos sensibles
- **Headers de seguridad** (HSTS, CSP, X-Frame-Options)
- **Proteccion contra spam** y mensajes duplicados
- **Gestion segura de secretos** con validacion en produccion

### Arquitectura Mejorada
- **Inyeccion de dependencias** con ServiceContainer
- **Manejo robusto de errores** con excepciones personalizadas
- **Logging estructurado JSON** para analisis
- **Middleware de request tracking** con IDs unicos
- **Metricas y health checks** integrados
- **Arquitectura testeable** con separacion de responsabilidades

---

## Instalacion y Configuracion

### Prerrequisitos
- Python 3.11+
- Cuenta de Twilio con WhatsApp Business API
- Google Cloud Service Account (para Google Sheets)
- OpenAI API Key (para IA, RAG y entrenamiento)
- PostgreSQL/Redis (opcional para sesiones persistentes)

### Instalacion Local

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

---

## Configuracion de Entorno

### Variables Criticas (Requeridas)
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

# Configuracion del servidor
BASE_URL=https://tu-dominio.com
PORT=8000
DEBUG=false
```

### Variables de OpenAI e IA (Nuevas v2.1)
```bash
# OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Modelo Fine-Tuned (opcional - si no se especifica usa gpt-3.5-turbo)
OPENAI_FINETUNED_MODEL=ft:gpt-3.5-turbo:bgr-export:shrimp-bot:xxxxx

# RAG Configuration
RAG_MIN_SIMILARITY=0.7
RAG_TOP_K=3
```

### Variables de Seguridad Adicionales
```bash
# Rate Limiting
RATE_LIMIT_MAX_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60

# Hosts y CORS
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
CORS_ORIGINS=https://tu-frontend.com

# Limites
MAX_MESSAGE_LENGTH=1000
MAX_FILE_SIZE=10485760  # 10MB
REQUEST_TIMEOUT=30
```

---

## Arquitectura del Sistema

```
BGR-SHRIMP/
├── app/
│   ├── main.py                  # Aplicacion FastAPI con middlewares
│   ├── config.py                # Configuracion centralizada
│   ├── dependencies.py          # Contenedor de servicios (DI)
│   ├── security.py              # Utilidades de seguridad
│   ├── exceptions.py            # Manejo de errores personalizado
│   ├── logging_config.py        # Sistema de logging estructurado
│   ├── monitoring.py            # Metricas y monitoreo
│   ├── models.py                # Modelos Pydantic
│   │
│   ├── routes/                  # Endpoints organizados por dominio
│   │   ├── whatsapp_routes.py   # Webhook principal de WhatsApp
│   │   ├── admin_routes.py      # Endpoints administrativos
│   │   ├── training_routes.py   # API de entrenamiento (NUEVO)
│   │   ├── rag_routes.py        # API de RAG (NUEVO)
│   │   ├── review_routes.py     # API de revision humana (NUEVO)
│   │   ├── pdf_routes.py        # Generacion de PDFs
│   │   └── test_routes.py       # Endpoints de testing
│   │
│   ├── services/                # Logica de negocio
│   │   ├── pricing.py           # Logica de precios principal
│   │   ├── google_sheets.py     # Integracion Google Sheets
│   │   ├── excel.py             # Procesamiento Excel local
│   │   ├── excel_calculator.py  # Calculadora Excel
│   │   ├── interactive.py       # Menus interactivos
│   │   ├── session.py           # Gestion de sesiones
│   │   ├── pdf_generator.py     # Generacion de cotizaciones PDF
│   │   ├── whatsapp_sender.py   # Cliente Twilio
│   │   ├── openai_service.py    # IA conversacional + Fine-tuning
│   │   ├── audio_handler.py     # Procesamiento de audio/Whisper
│   │   ├── rag_service.py       # Sistema RAG (NUEVO)
│   │   ├── training_pipeline.py # Pipeline ETL (NUEVO)
│   │   ├── training_capture_db.py # Captura SQLite (NUEVO)
│   │   ├── human_review.py      # Revision humana (NUEVO)
│   │   └── quality_assurance.py # Validacion QA (NUEVO)
│   │
│   ├── utils/                   # Utilidades
│   │   ├── anonymizer.py        # Anonimizacion GDPR (NUEVO)
│   │   ├── language_utils.py    # Utilidades de idioma
│   │   ├── message_utils.py     # Procesamiento de mensajes
│   │   └── service_utils.py     # Utilidades de servicios
│   │
│   └── templates/               # Plantillas HTML
│       └── review_dashboard.html # Dashboard de revision (NUEVO)
│
├── data/                        # Archivos de datos
│   ├── etl_queue/               # Cola de mensajes pendientes (NUEVO)
│   ├── processed/               # Mensajes procesados (NUEVO)
│   ├── approved/                # Mensajes aprobados (NUEVO)
│   ├── rejected/                # Mensajes rechazados (NUEVO)
│   ├── finetune/                # Exportaciones JSONL (NUEVO)
│   ├── rag/                     # Indices RAG (NUEVO)
│   └── training_messages.db     # Base de datos SQLite (NUEVO)
│
├── docs/                        # Documentacion
│   ├── TRAINING_SYSTEM.md       # Guia del sistema de entrenamiento
│   ├── CONSENT_FLOW.md          # Flujo de consentimiento GDPR
│   └── entrega/                 # Documentacion de entrega
│
├── logs/                        # Logs estructurados
├── generated_pdfs/              # PDFs generados
├── scripts/                     # Scripts de utilidad
└── tests/                       # Suite de pruebas
```

---

## Sistema RAG (Retrieval-Augmented Generation)

El sistema RAG mejora las respuestas del bot recuperando contexto relevante de documentos indexados.

### Caracteristicas
- **Embeddings OpenAI**: Usa `text-embedding-3-small` para vectorizacion
- **Vector Store Local**: Almacenamiento eficiente con busqueda por similitud coseno
- **Tipos de Documentos**: prices, faq, conversation, product, policy, general
- **Persistencia**: Indices guardados en disco para recuperacion rapida

### Endpoints RAG
```bash
# Estadisticas del indice
GET /rag/stats

# Estado del servicio
GET /rag/health

# Indexar un documento
POST /rag/index
Content-Type: application/json
{
  "content": "El HLSO 16/20 tiene un precio base de $5.50/kg",
  "doc_type": "price",
  "metadata": {"product": "HLSO", "size": "16/20"}
}

# Indexar multiples documentos
POST /rag/index/batch
Content-Type: application/json
{
  "documents": [
    {"content": "...", "doc_type": "faq"},
    {"content": "...", "doc_type": "price"}
  ]
}

# Indexar precios desde Google Sheets
POST /rag/index/prices

# Indexar FAQs
POST /rag/index/faqs
Content-Type: application/json
{
  "faqs": [
    {"question": "Que es el glaseo?", "answer": "El glaseo es...", "category": "general"}
  ]
}

# Consultar documentos relevantes
POST /rag/query
Content-Type: application/json
{
  "query": "precio HLSO 16/20",
  "top_k": 3,
  "min_similarity": 0.7,
  "return_context": true
}

# Listar documentos indexados
GET /rag/documents

# Eliminar documento
DELETE /rag/documents/{doc_id}

# Limpiar todo el indice
DELETE /rag/clear
```

---

## Sistema de Entrenamiento de IA

Pipeline completo para capturar, procesar y exportar datos de entrenamiento para fine-tuning de OpenAI.

### Flujo del Pipeline ETL
```
Usuario → Consentimiento → Captura → Anonimizacion → Analisis OpenAI → QA → Revision → Exportacion
```

### Componentes

#### 1. Captura de Mensajes
- Requiere consentimiento explicito del usuario
- Almacenamiento en SQLite (sobrevive reinicios)
- Filtrado inicial de mensajes irrelevantes

#### 2. Anonimizacion (GDPR)
El sistema anonimiza automaticamente:
- Numeros de telefono → `[PHONE]`
- Emails → `[EMAIL]`
- Direcciones → `[ADDRESS]`
- IDs → `[ID]`
- Numeros de cuenta → `[ACCOUNT]`
- Nombres propios → `[NAME]`

**Whitelist** (NO se anonimizan):
- Productos: HLSO, HOSO, P&D, IQF, COOKED
- Tallas: 16/20, 21/25, 26/30, etc.
- Terminos comerciales: glaseo, flete, CFR, FOB
- Ciudades comunes: Houston, Miami, Lisboa

#### 3. Analisis Automatico
- Clasificacion de intent con OpenAI
- Extraccion de entidades (producto, talla, glaseo)
- Score de confianza (0-1)

#### 4. Quality Assurance
Validaciones automaticas:
- Productos validos
- Tallas en rango
- Glaseo 0-50%
- Precios en rangos esperados
- Fletes razonables

#### 5. Revision Humana
Dashboard web para:
- Ver items pendientes de revision
- Aprobar/Rechazar mensajes
- Editar contenido o analisis
- Re-analizar con OpenAI
- Aprobacion en lote

#### 6. Exportacion
- Formato JSONL para fine-tuning OpenAI
- Division train/validation configurable
- Filtro por confianza minima

### Endpoints de Entrenamiento
```bash
# Estadisticas del pipeline
GET /training/stats

# Procesar cola ETL
POST /training/process
Content-Type: application/json
{
  "max_items": 100
}

# Exportar para fine-tuning
POST /training/export
Content-Type: application/json
{
  "min_confidence": 0.85,
  "train_split": 0.9
}

# Establecer consentimiento
POST /training/consent/{user_id}
Content-Type: application/json
{
  "consent": true
}

# Obtener estado de consentimiento
GET /training/consent/{user_id}
```

### Endpoints de Revision Humana
```bash
# Dashboard web de revision
GET /review/dashboard

# Listar items pendientes
GET /review/pending?limit=50&offset=0&sort_by=captured_at

# Detalle de un item
GET /review/item/{item_id}

# Estadisticas de revision
GET /review/stats

# Aprobar item
POST /review/approve/{item_id}
Content-Type: application/json
{
  "reviewer": "admin",
  "notes": "Ejemplo de calidad"
}

# Rechazar item
POST /review/reject/{item_id}
Content-Type: application/json
{
  "reviewer": "admin",
  "reason": "Informacion incorrecta"
}

# Editar item
POST /review/edit/{item_id}
Content-Type: application/json
{
  "reviewer": "admin",
  "new_content": "Contenido corregido",
  "new_analysis": {"intent": "proforma", "confidence": 0.95}
}

# Re-analizar con OpenAI
POST /review/reanalyze/{item_id}

# Aprobar multiples items
POST /review/batch/approve
Content-Type: application/json
{
  "item_ids": ["id1", "id2", "id3"],
  "reviewer": "admin"
}

# Rechazar multiples items
POST /review/batch/reject
Content-Type: application/json
{
  "item_ids": ["id1", "id2"],
  "reviewer": "admin",
  "reason": "Baja calidad"
}

# Auto-aprobar items con alta confianza
POST /review/auto-approve
Content-Type: application/json
{
  "min_confidence": 0.95,
  "reviewer": "auto-system"
}
```

---

## Caracteristicas de Seguridad

### Autenticacion y Autorizacion
- **Webhook Validation**: Validacion criptografica de requests de Twilio
- **Bearer Auth**: Tokens para endpoints administrativos
- **Session Management**: Sesiones seguras por usuario

### Proteccion contra Ataques
- **Rate Limiting**: Limite configurable por IP/usuario
- **Input Validation**: Sanitizacion estricta de entrada
- **CORS Policy**: Control de origenes permitidos
- **Security Headers**: Proteccion XSS, Clickjacking, etc.

### Privacidad y Compliance
- **Data Sanitization**: Filtrado automatico de datos sensibles en logs
- **Secure File Handling**: Manejo seguro de archivos temporales
- **Audit Logging**: Registro de eventos de seguridad
- **GDPR Compliance**: Anonimizacion y consentimiento para entrenamiento

---

## Uso del Bot

### Comandos Principales
- `menu` - Menu principal interactivo
- `precios` - Consulta directa de precios
- `confirmar` - Generar PDF de cotizacion
- `idioma` - Cambiar idioma de proformas
- `ayuda` - Mostrar comandos disponibles

### Flujo de Cotizacion
1. **Consulta** -> "Precio HLSO 16/20"
2. **Respuesta** -> Cotizacion detallada con calculos
3. **Confirmacion** -> "confirmar"
4. **Idioma** -> Seleccion ES/EN
5. **PDF** -> Envio automatico por WhatsApp

### Consultas Inteligentes
```
"Necesito precio de HLSO 16/20 para China"
"Cotizacion P&D IQF 21/25 con 10% glaseo"
"15000 libras de EZ PEEL 26/30 destino Houston"
"Generar proforma para Juan Perez"
```

---

## Endpoints Administrativos

### Gestion del Sistema
```bash
# Health Check
GET /health

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

---

## Monitoreo y Logs

### Sistema de Logging
- **Structured Logging**: Formato JSON para analisis
- **Log Rotation**: Rotacion diaria automatica
- **Error Tracking**: Logs separados para errores
- **Security Audit**: Log especifico de eventos de seguridad
- **Business Events**: Metricas de negocio (cotizaciones, PDFs)
- **Training Events**: Metricas de entrenamiento (capturas, QA, exports)

### Archivos de Log
```
logs/
├── app.log          # Log general de aplicacion
├── errors.log       # Errores y excepciones
├── security.log     # Eventos de seguridad
└── business.log     # Metricas de negocio
```

---

## Despliegue en Produccion

### Checklist de Seguridad
- [ ] `DEBUG=false` y `ENVIRONMENT=production`
- [ ] `SECRET_KEY` unica y segura
- [ ] `ADMIN_API_TOKEN` configurado
- [ ] `OPENAI_API_KEY` configurado
- [ ] `ALLOWED_HOSTS` restringido
- [ ] HTTPS habilitado con certificado valido
- [ ] Backup de datos configurado
- [ ] Monitoreo de errores activo
- [ ] Rate limiting ajustado
- [ ] Base de datos SQLite respaldada

### Plataformas Soportadas
- **Render**: Configuracion incluida en `render.yaml`
- **Railway**: Archivo `railway.json` incluido
- **Heroku**: Compatible con `Procfile`
- **Docker**: Dockerfile disponible
- **VPS**: Scripts de deployment incluidos

---

## Testing

```bash
# Ejecutar tests unitarios
pytest tests/unit/

# Tests de integracion
pytest tests/integration/

# Coverage report
pytest --cov=app tests/

# Linting y formato
ruff check app/
black app/
```

---

## Metricas de Performance

- **Response Time**: < 200ms promedio
- **Uptime Target**: 99.9%
- **Rate Limit**: 30 req/min por usuario
- **PDF Generation**: < 3 segundos
- **Memory Usage**: < 512MB tipico
- **RAG Query**: < 500ms promedio
- **Training Pipeline**: 100 items/min

---

## Documentacion Adicional

| Documento | Descripcion |
|-----------|-------------|
| `docs/TRAINING_SYSTEM.md` | Guia completa del sistema de entrenamiento |
| `docs/CONSENT_FLOW.md` | Flujo de consentimiento GDPR |
| `docs/entrega/01-RESUMEN_EJECUTIVO.md` | Resumen ejecutivo del proyecto |
| `docs/entrega/02-MANUAL_USUARIO.md` | Manual de usuario |
| `docs/entrega/03-MANUAL_TECNICO.md` | Manual tecnico |
| `docs/entrega/04-GUIA_TROUBLESHOOTING.md` | Guia de solucion de problemas |
| `docs/entrega/05-API_DOCUMENTATION.md` | Documentacion de API |
| `docs/entrega/06-GUIA_MANTENIMIENTO.md` | Guia de mantenimiento |

---

## Contribucion

1. Fork el proyecto
2. Crea una rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

### Estandares de Codigo
- **Type Hints**: Usar tipos en todas las funciones
- **Docstrings**: Documentar clases y metodos publicos
- **Testing**: Cobertura minima del 80%
- **Security**: Pasar analisis de seguridad

---

## Licencia

Proyecto privado de BGR Export. Todos los derechos reservados.

---

## Soporte

**Soporte Tecnico:**
- Email: rojassebas765@gmail.com
- WhatsApp Empresarial: +593 968058769

**Desarrollador:**
- Email: rojassebas765@gmail.com
- GitHub: @xtaxx12

---

**Version:** 2.1.0 | **Ultima actualizacion:** Noviembre 2025
