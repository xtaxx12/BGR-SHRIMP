# Cambios Realizados: Manejo de Precio DDP

## Problema Original
Cuando el usuario enviaba un mensaje con "precio DDP" sin especificar el valor del flete, el sistema generaba la proforma aplicando un flete por defecto de $0.15/kg, lo cual era incorrecto.

## Solución Implementada

### 1. Eliminación de Flete por Defecto
**Archivos modificados:** `app/routes.py`

- **Línea ~613**: Eliminado `'flete_custom': 0.15` y `'flete_solicitado': True` del query para múltiples productos
- **Línea ~1218**: Eliminado `'flete_custom': 0.15` del query para productos con glaseo
- **Línea ~1241**: Eliminado `'flete': 0.15` de la última cotización consolidada

**Resultado:** El sistema ya NO aplica flete por defecto en ningún caso.

### 2. Detección de DDP
**Archivo modificado:** `app/services/openai_service.py`

- **Nuevos patrones de detección:**
  ```python
  ddp_patterns = [
      r'\bddp\b',      # DDP con límites de palabra
      r'ddp\s',        # DDP seguido de espacio
      r'\sddp',        # DDP precedido de espacio
      r'precio\s+ddp', 
      r'ddp\s+price', 
      r'delivered\s+duty\s+paid'
  ]
  ```

- **Nuevo campo en análisis:** `is_ddp: True/False`
  - Indica si el usuario mencionó "DDP" en el mensaje

### 3. Lógica de Solicitud de Flete
**Archivo modificado:** `app/services/utils.py`

Función `parse_ai_analysis_to_query()`:

```python
# Si es DDP, SIEMPRE necesitamos el flete para desglosar el precio
if is_ddp:
    if flete_custom:
        # Usuario especificó el flete en el mensaje DDP
        flete_solicitado = True
        flete_value = flete_custom
    else:
        # DDP sin flete especificado - DEBE pedirlo
        flete_solicitado = True
        flete_value = None
```

**Resultado:** Cuando se detecta DDP sin flete, marca `flete_solicitado=True` y `flete_custom=None`, lo que activa la solicitud de flete.

### 4. Manejo de Múltiples Productos con DDP
**Archivo modificado:** `app/routes.py`

- **Nuevo estado:** `waiting_for_multi_flete`
  - Se activa cuando se detectan múltiples productos con DDP sin flete

- **Verificación antes de calcular precios:**
  ```python
  if is_ddp and flete_custom is None:
      # Pedir flete antes de continuar
      session_manager.set_session_state(user_id, 'waiting_for_multi_flete', {...})
  ```

- **Manejador de respuesta:** Procesa la respuesta del usuario con el valor del flete y genera la cotización consolidada

### 5. Actualización de Prompts de OpenAI
**Archivo modificado:** `app/services/openai_service.py`

- Actualizado el prompt del sistema para incluir:
  - "DDP: Si menciona 'DDP' → DEBE pedir flete si no lo especifica"
  - Ejemplos de extracción con DDP

## Flujo Actual

### Caso 1: Usuario dice "DDP" SIN especificar flete
```
Usuario: "Precios HLSO 16-20 DDP LA al 15%"
         ↓
Sistema detecta: is_ddp=True, flete_custom=None, glaseo=15%
         ↓
Sistema responde: "🚢 Para calcular el precio DDP necesito el valor del flete..."
         ↓
Usuario: "0.25"
         ↓
Sistema calcula precio con flete $0.25 y genera proforma
```

### Caso 2: Usuario dice "DDP" CON flete especificado
```
Usuario: "Precios HLSO 16-20 DDP con flete 0.30 al 15%"
         ↓
Sistema detecta: is_ddp=True, flete_custom=0.30, glaseo=15%
         ↓
Sistema calcula precio directamente y genera proforma
```

### Caso 3: Usuario NO menciona DDP ni flete
```
Usuario: "Precios HLSO 16-20 al 15%"
         ↓
Sistema detecta: is_ddp=False, flete_custom=None, glaseo=15%
         ↓
Sistema calcula precio SIN flete (solo FOB con glaseo) y genera proforma
```

## Verificación

### Test creado: `test_ddp_detection.py`
Verifica que:
- ✅ DDP se detecta correctamente
- ✅ Glaseo se extrae correctamente (15%)
- ✅ `flete_solicitado=True` cuando DDP sin flete
- ✅ `flete_custom=None` cuando no se especifica

### Resultado de prueba:
```
✅ CORRECTO: DDP detectado SIN flete - el sistema PEDIRÁ el valor del flete
✅ CORRECTO: Glaseo 15% detectado correctamente
```

## Logs Esperados

### Antes (incorrecto):
```
2025-10-29 16:16:52,585 - app.services.excel_local_calculator - INFO - Factores: glaseo=0.85, flete=0.15, costo_fijo=0.29
```

### Ahora (correcto):
```
2025-10-29 XX:XX:XX - app.services.utils - INFO - 📦 Precio DDP detectado SIN flete - se solicitará valor de flete al usuario
2025-10-29 XX:XX:XX - app.routes - INFO - 📦 DDP detectado sin flete - pidiendo valor de flete para 8 productos
```

## Resumen
El sistema ahora:
1. ✅ NO aplica flete por defecto ($0.15)
2. ✅ Detecta correctamente "DDP" en mensajes
3. ✅ Pide el valor del flete cuando se menciona DDP sin especificarlo
4. ✅ Maneja correctamente múltiples productos con DDP
5. ✅ Solo aplica flete cuando el usuario lo especifica explícitamente
