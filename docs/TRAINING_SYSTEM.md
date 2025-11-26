# 🎓 Sistema de Entrenamiento con Mensajes de Usuarios

Sistema completo para capturar, procesar y exportar mensajes de usuarios para mejorar la IA del bot.

## 📋 Características

- ✅ **Consentimiento obligatorio** - Cumple con GDPR
- ✅ **Anonimización automática** - Protege datos sensibles
- ✅ **Pipeline ETL completo** - Captura → Análisis → Validación → Exportación
- ✅ **Análisis automático** - Usa OpenAI para etiquetar datos
- ✅ **Validación QA** - Verifica calidad antes de exportar
- ✅ **Exportación JSONL** - Listo para fine-tuning de OpenAI
- ✅ **API REST** - Endpoints de administración
- ✅ **Métricas y logs** - Monitoreo completo

---

## 🏗️ Arquitectura

```
Usuario → SessionManager → Pipeline ETL → Análisis → QA → Exportación
                ↓
          Consentimiento
                ↓
          Anonimización
```

### Componentes

1. **SessionManager** (`app/services/session.py`)
   - Maneja consentimiento
   - Captura mensajes automáticamente
   - Hook ETL integrado

2. **TrainingPipeline** (`app/services/training_pipeline.py`)
   - Cola ETL
   - Filtrado automático
   - Análisis con OpenAI
   - Validación QA
   - Exportación JSONL

3. **Anonymizer** (`app/utils/anonymizer.py`)
   - Anonimiza teléfonos, emails, direcciones
   - Protege IDs y números de cuenta
   - Whitelist para términos comerciales

4. **Training Routes** (`app/routes/training_routes.py`)
   - API REST para administración
   - Endpoints de estadísticas
   - Control de procesamiento

---

## 🚀 Uso

### 1. Solicitar Consentimiento

```python
from app.services.session import session_manager

# Establecer consentimiento
session_manager.set_training_consent(user_id, True)

# Verificar consentimiento
has_consent = session_manager.get_training_consent(user_id)
```

### 2. Captura Automática

Los mensajes se capturan automáticamente cuando:
- El usuario tiene consentimiento activo
- El mensaje es de tipo "user"
- El mensaje pasa el filtro inicial

```python
# Esto se hace automáticamente en SessionManager.add_to_conversation()
session_manager.add_to_conversation(user_id, "user", "HLSO 16/20 con 20% glaseo")
```

### 3. Procesar Cola ETL

```bash
# Vía API
curl -X POST http://localhost:8000/webhook/training/process \
  -H "Content-Type: application/json" \
  -d '{"max_items": 100}'

# Vía Python
from app.services.training_pipeline import get_training_pipeline
from app.services.openai_service import OpenAIService
from app.services.quality_assurance import QualityAssuranceService

pipeline = get_training_pipeline()
openai_service = OpenAIService()
qa_service = QualityAssuranceService()

results = pipeline.process_queue(
    openai_service=openai_service,
    qa_service=qa_service,
    max_items=100
)
```

### 4. Exportar para Fine-Tuning

```bash
# Vía script
python scripts/export_for_finetune.py --min-confidence 0.85

# Vía API
curl -X POST http://localhost:8000/webhook/training/export \
  -H "Content-Type: application/json" \
  -d '{"min_confidence": 0.85, "train_split": 0.9}'
```

---

## 📊 API Endpoints

### GET /webhook/training/stats
Obtiene estadísticas del sistema.

**Respuesta:**
```json
{
  "success": true,
  "pipeline": {
    "captured": 150,
    "anonymized": 150,
    "filtered_out": 20,
    "analyzed": 130,
    "qa_passed": 100,
    "qa_failed": 30,
    "exported": 100,
    "needs_review": 10,
    "queue_size": 5,
    "processed_size": 100,
    "rejected_size": 30
  },
  "anonymization": {
    "total_processed": 150,
    "phones_found": 5,
    "emails_found": 3,
    "addresses_found": 2
  },
  "sessions": {
    "total": 50,
    "with_consent": 30,
    "consent_rate": "60.0%"
  }
}
```

### POST /webhook/training/process
Procesa la cola ETL.

**Request:**
```json
{
  "max_items": 100
}
```

**Respuesta:**
```json
{
  "success": true,
  "results": {
    "processed": 50,
    "passed_qa": 40,
    "failed_qa": 5,
    "needs_review": 5,
    "errors": 0
  }
}
```

### POST /webhook/training/export
Exporta datos a JSONL.

**Request:**
```json
{
  "min_confidence": 0.85,
  "train_split": 0.9
}
```

**Respuesta:**
```json
{
  "success": true,
  "train_examples": 90,
  "valid_examples": 10,
  "total": 100,
  "files": {
    "train": "data/finetune/train.jsonl",
    "valid": "data/finetune/valid.jsonl"
  }
}
```

### POST /webhook/training/consent/{user_id}
Establece consentimiento.

**Request:**
```json
{
  "consent": true
}
```

### GET /webhook/training/consent/{user_id}
Obtiene consentimiento.

**Respuesta:**
```json
{
  "success": true,
  "user_id": "whatsapp:+593999999999",
  "consent": true,
  "consent_timestamp": 1700000000.0
}
```

---

## 📁 Estructura de Datos

### Cola ETL (`data/etl_queue/`)
Mensajes pendientes de procesamiento.

```json
{
  "user_id": "[PHONE]",
  "role": "user",
  "original_length": 45,
  "content": "HLSO 16/20 con 20% glaseo",
  "metadata": {
    "state": "idle",
    "has_quote": false
  },
  "captured_at": "2024-01-15T10:30:00",
  "status": "pending"
}
```

### Procesados (`data/processed/`)
Mensajes analizados y validados.

```json
{
  "user_id": "[PHONE]",
  "role": "user",
  "content": "HLSO 16/20 con 20% glaseo",
  "analysis": {
    "intent": "proforma",
    "product": "HLSO",
    "size": "16/20",
    "glaseo_percentage": 20,
    "confidence": 0.95
  },
  "qa_passed": true,
  "qa_errors": [],
  "status": "approved"
}
```

### Exportados (`data/finetune/`)
Formato JSONL para fine-tuning.

**train.jsonl:**
```jsonl
{"prompt": "Usuario: HLSO 16/20 con 20% glaseo\nAsistente:", "completion": " ¡Perfecto! Generando tu proforma...\n"}
{"prompt": "Usuario: Precio CFR Houston\nAsistente:", "completion": " Para calcular el precio CFR necesito...\n"}
```

---

## 🔒 Privacidad y Seguridad

### Anonimización

El sistema anonimiza automáticamente:
- ✅ Números de teléfono → `[PHONE]`
- ✅ Emails → `[EMAIL]`
- ✅ Direcciones → `[ADDRESS]`
- ✅ IDs → `[ID]`
- ✅ Números de cuenta → `[ACCOUNT]`
- ✅ Nombres (opcional) → `[NAME]`

### Whitelist

NO se anonimizan:
- Productos (HLSO, HOSO, etc.)
- Tallas (16/20, 21/25, etc.)
- Términos comerciales (glaseo, flete, CFR, etc.)
- Ciudades comunes (Houston, Lisboa, etc.)

### Consentimiento

- Obligatorio antes de capturar
- Puede revocarse en cualquier momento
- Se registra timestamp del consentimiento

---

## 📈 Métricas

### Pipeline
- `captured`: Mensajes capturados
- `anonymized`: Mensajes anonimizados
- `filtered_out`: Mensajes descartados
- `analyzed`: Mensajes analizados con OpenAI
- `qa_passed`: Mensajes que pasaron QA
- `qa_failed`: Mensajes que fallaron QA
- `exported`: Mensajes exportados
- `needs_review`: Mensajes que necesitan revisión humana

### Anonimización
- `total_processed`: Total procesados
- `phones_found`: Teléfonos encontrados
- `emails_found`: Emails encontrados
- `addresses_found`: Direcciones encontradas

---

## 🛠️ Mantenimiento

### Limpiar Cola
```python
import shutil
shutil.rmtree("data/etl_queue")
Path("data/etl_queue").mkdir(parents=True)
```

### Revisar Rechazados
```python
from pathlib import Path
import json

for file in Path("data/rejected").glob("*.json"):
    with open(file) as f:
        record = json.load(f)
        print(f"Rechazado: {record['content']}")
        print(f"Errores: {record['qa_errors']}")
```

### Exportar Todo
```bash
python scripts/export_for_finetune.py --source both --min-confidence 0.80
```

---

## 🎯 Mejores Prácticas

1. **Procesar regularmente** - Ejecutar `process_queue()` cada hora
2. **Revisar needs_review** - Validar manualmente ejemplos con baja confianza
3. **Monitorear métricas** - Verificar tasas de QA y confianza
4. **Actualizar whitelist** - Agregar nuevos términos comerciales
5. **Backup datos** - Respaldar `data/processed/` regularmente
6. **Validar exports** - Revisar JSONL antes de usar para fine-tuning

---

## 🚨 Troubleshooting

### No se capturan mensajes
- Verificar consentimiento: `session_manager.get_training_consent(user_id)`
- Verificar filtros en `_should_capture()`

### QA falla mucho
- Ajustar `min_confidence` más bajo
- Revisar validaciones en QA service
- Verificar datos en Google Sheets

### Exportación vacía
- Verificar archivos en `data/processed/`
- Verificar `min_confidence` no sea muy alto
- Procesar cola primero

---

## 📚 Referencias

- [OpenAI Fine-Tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [GDPR Compliance](https://gdpr.eu/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 🤝 Contribuir

Para agregar nuevas funcionalidades:

1. Actualizar `TrainingPipeline`
2. Agregar endpoint en `training_routes.py`
3. Actualizar esta documentación
4. Agregar tests

---

**Última actualización:** 2024-01-15
