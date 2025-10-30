# Sistema de Validación y Certificación

Este directorio contiene el sistema completo de validación y certificación de calidad para el BGR Shrimp Bot.

## 📋 Componentes

### 1. Script Maestro (`master_validation.py`)
Script principal que orquesta todo el proceso de validación y certificación.

### 2. Checklist de Pre-Despliegue (`pre_deploy_checklist.py`)
Script automatizado que valida que el sistema esté listo para despliegue a producción.

**Uso:**
```bash
python scripts/pre_deploy_checklist.py
```

**Funcionalidad:**
- Valida variables de entorno requeridas y opcionales
- Verifica conectividad con servicios externos (Twilio, Google Sheets, OpenAI)
- Valida configuración de seguridad (HTTPS, rate limiting, tokens)
- Verifica sistema de logs y monitoreo
- Genera reporte detallado en JSON

**Documentación completa:** Ver `scripts/README_PRE_DEPLOY.md`

### 3. Script Maestro de Validación (`master_validation.py`)
Script principal que orquesta todo el proceso de validación y certificación.

**Uso:**
```bash
python scripts/master_validation.py
```

**Funcionalidad:**
- Ejecuta la suite completa de tests
- Valida todos los puntos críticos del sistema
- Genera certificado de calidad en PDF y TXT
- Proporciona resumen consolidado de resultados

### 4. Ejecutor de Tests (`run_validation.py`)
Ejecuta todos los tests existentes y genera reporte consolidado.

**Uso:**
```bash
python scripts/run_validation.py
```

**Tests ejecutados:**
- `test_quality_assurance.py` - Validaciones de QA
- `test_flexible_glaseo.py` - Cálculos de glaseo
- `test_consolidated_quote.py` - Cotizaciones consolidadas
- `test_hoso_3040_calculation.py` - Cálculos específicos
- `test_session_preservation.py` - Preservación de sesiones
- `test_routes_flete.py` - Rutas de flete
- `test_routes_glaseo.py` - Rutas de glaseo
- `test_natural_conversation.py` - Conversación natural

**Salida:**
- `validation_report.json` - Reporte detallado en JSON

### 5. Validador de Puntos Críticos (`validate_critical_points.py`)
Verifica funcionalidades esenciales del sistema.

**Uso:**
```bash
python scripts/validate_critical_points.py
```

**Puntos críticos validados:**
- CP1: Tiempo de respuesta de consulta < 3 segundos
- CP2: Generación de PDF < 5 segundos
- CP3: Detección de DDP sin flete
- CP4: Sesiones concurrentes independientes
- CP5: Validación de webhook Twilio
- CP6: Validación de productos válidos
- CP7: Validación de tallas válidas
- CP8: Cálculo correcto de glaseo (0% - 50%)

**Salida:**
- Resultados en consola
- Datos disponibles para certificado

### 6. Generador de Certificado (`generate_quality_certificate.py`)
Genera certificado de calidad en formato PDF y TXT.

**Uso:**
```bash
python scripts/generate_quality_certificate.py
```

**Requisitos:**
- `reportlab` para generación de PDF (opcional)
- Si no está disponible, genera certificado en texto plano

**Salida:**
- `quality_certificate.pdf` - Certificado en PDF (si reportlab disponible)
- `quality_certificate.txt` - Certificado en texto plano (siempre)

## 🚀 Uso Recomendado

### Flujo Completo de Pre-Despliegue

1. **Checklist de Pre-Despliegue** (Primero)
```bash
python scripts/pre_deploy_checklist.py
```
Verifica que el entorno esté configurado correctamente.

2. **Validación Completa** (Después)
```bash
python scripts/master_validation.py
```
Ejecuta tests y valida puntos críticos.

### Validación Completa (Recomendado)
```bash
python scripts/master_validation.py
```

Este comando ejecuta todo el proceso de validación y certificación en una sola ejecución.

### Validación Individual

Si necesitas ejecutar componentes individuales:

```bash
# Solo tests
python scripts/run_validation.py

# Solo puntos críticos
python scripts/validate_critical_points.py

# Solo certificado (requiere reportes previos)
python scripts/generate_quality_certificate.py
```

## 📊 Archivos Generados

### Pre-Despliegue
- `pre_deploy_checklist_report.json` - Reporte de checklist de pre-despliegue

### Validación Completa
- `validation_report.json` - Reporte detallado de todos los tests
- `critical_points_report.json` - Reporte de puntos críticos
- `quality_certificate.pdf` - Certificado de calidad en PDF
- `quality_certificate.txt` - Certificado de calidad en texto plano

## 📦 Dependencias

### Requeridas
- Python 3.7+
- Todas las dependencias del proyecto BGR Shrimp Bot

### Opcionales
- `reportlab` - Para generación de certificados en PDF

**Instalación de reportlab:**
```bash
pip install reportlab
```

## ✅ Criterios de Certificación

### Certificación Exitosa (Exit Code 0)
- ✅ Todos los tests pasan (100%)
- ✅ Todos los puntos críticos pasan (100%)
- 🎉 Sistema listo para producción

### Certificación Condicional (Exit Code 1)
- ⚠️ Tasa de éxito de tests ≥ 90%
- ⚠️ Tasa de éxito de puntos críticos ≥ 90%
- 📝 Requiere correcciones menores

### Certificación Fallida (Exit Code 2)
- ❌ Tasa de éxito de tests < 90%
- ❌ Tasa de éxito de puntos críticos < 90%
- 🔧 Requiere correcciones significativas

## 🔍 Interpretación de Resultados

### Tests Pasados
```
✅ PASÓ - test_quality_assurance.py (2.34s)
```
El test se ejecutó exitosamente sin errores.

### Tests Fallados
```
❌ FALLÓ - test_natural_conversation.py (0.15s)
   Error: OpenAI API key not configured
```
El test falló. Revisar el error para determinar la causa.

### Puntos Críticos
```
✅ PASÓ - CP1: Tiempo de respuesta de consulta < 3s (0.234s)
   Respuesta en 0.234s con precio $7.31/kg
```
El punto crítico cumple con los requisitos de performance.

## 🛠️ Troubleshooting

### Error: "No module named 'reportlab'"
**Solución:** Instalar reportlab o usar certificado en texto plano
```bash
pip install reportlab
```

### Error: "OpenAI API key not configured"
**Solución:** Configurar variable de entorno OPENAI_API_KEY
```bash
export OPENAI_API_KEY="tu-api-key"
```

### Error: "No se encontró validation_report.json"
**Solución:** Ejecutar primero el script de validación
```bash
python scripts/run_validation.py
```

### Tests timeout
**Solución:** Verificar conectividad con servicios externos (Twilio, Google Sheets, OpenAI)

## 📝 Notas

- Los tests se ejecutan con timeout de 60 segundos cada uno
- Los puntos críticos tienen requisitos de performance específicos
- El certificado PDF requiere reportlab instalado
- El certificado TXT siempre se genera como fallback
- Los reportes JSON contienen información detallada para debugging

## 🔄 Integración Continua

Este sistema puede integrarse en pipelines de CI/CD:

```yaml
# Ejemplo para GitHub Actions
- name: Run Validation
  run: python scripts/master_validation.py
  
- name: Upload Certificate
  uses: actions/upload-artifact@v2
  with:
    name: quality-certificate
    path: quality_certificate.pdf
```

## 📞 Soporte

Para problemas o preguntas sobre el sistema de validación, contactar al equipo de desarrollo.
