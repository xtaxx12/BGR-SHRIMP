# Cotización Consolidada - Múltiples Productos

## 🎯 Funcionalidad Implementada

Permite al bot procesar mensajes con **múltiples productos** y generar una **cotización consolidada** en un solo PDF con tabla de todos los productos.

## 📋 Ejemplo de Uso

### Mensaje del Cliente
```
Precios para esto por favor ..
HOSO 50-60 block 10x4
HLSO 16-20 block 10x4
HLSO 26-30 block 10x4
HLSO 36-40 block 10x4
HLSO 51-60 block 10x4
PYD TAIL OFF 61-70 IQF 5X2
16-20 EZPEEL IQF 10X2
26-30 EZPEEL IQF 10X2
DDP LA or Houston
```

### Respuesta del Bot
```
📋 Detecté 8 productos para cotizar:
   1. HOSO 50/60
   2. HLSO 16/20
   3. HLSO 26/30
   4. HLSO 36/40
   5. HLSO 51/60
   6. P&D IQF 61/70
   7. EZPEEL 16/20
   8. EZPEEL 26/30

🌍 Destino: LA / Houston

❄️ ¿Qué glaseo necesitas para todos los productos?
• 10% glaseo (factor 0.90)
• 20% glaseo (factor 0.80)
• 30% glaseo (factor 0.70)

💡 Responde con el número: 10, 20 o 30
```

### Cliente Responde
```
20
```

### Bot Calcula y Genera PDF
```
✅ Precios calculados para 6/8 productos

⚠️ No se encontraron precios para:
   • EZPEEL 16/20
   • EZPEEL 26/30

🌐 Selecciona el idioma para la cotización consolidada:

1️⃣ Español 🇪🇸
2️⃣ English 🇺🇸
```

### Cliente Selecciona Idioma
```
1
```

### Bot Envía PDF
```
✅ Cotización consolidada generada

🌐 Idioma: Español 🇪🇸
📦 Productos: 6
❄️ Glaseo: 20%

⚠️ 2 producto(s) sin precio disponible

📄 PDF enviado por WhatsApp
```

## 📄 Formato del PDF Consolidado

El PDF incluye:

1. **Logo de BGR Export**
2. **Información General:**
   - Fecha de cotización
   - Destino (si se especifica)
   - Glaseo aplicado

3. **Tabla de Productos:**
   ```
   ┌────────────────────────────────────────────────────────┐
   │ PRODUCTO      │ TALLA  │ PRECIO FOB │ PRECIO CFR      │
   ├────────────────────────────────────────────────────────┤
   │ HOSO          │ 50/60  │ $4.52/kg   │ $4.07/kg       │
   │ HLSO          │ 16/20  │ $8.88/kg   │ $7.05/kg       │
   │ HLSO          │ 26/30  │ $7.18/kg   │ $5.99/kg       │
   │ HLSO          │ 36/40  │ $6.19/kg   │ $5.73/kg       │
   │ HLSO          │ 51/60  │ $5.33/kg   │ $5.20/kg       │
   │ P&D IQF       │ 61/70  │ $7.75/kg   │ $6.07/kg       │
   └────────────────────────────────────────────────────────┘
   ```

4. **Notas:**
   - Precios sujetos a confirmación final
   - Glaseo aplicado: 20%
   - Flete incluido en precio CFR

5. **Información de Contacto**

## 🔧 Implementación Técnica

### 1. Detección de Múltiples Productos

**Archivo:** `app/services/openai_service.py`

```python
def detect_multiple_products(self, message: str) -> List[Dict]:
    """
    Detecta múltiples productos en un mensaje
    Analiza línea por línea buscando:
    - Producto (HOSO, HLSO, P&D, EZPEEL, etc.)
    - Talla (formato XX/XX o XX-XX)
    """
```

**Patrones detectados:**
- `HOSO`, `HLSO`
- `P&D IQF`, `PYD TAIL OFF`
- `P&D BLOQUE`, `BLOCK`
- `EZPEEL`, `EZ PEEL`

### 2. Estados de Sesión

**Nuevos estados agregados:**

1. **`waiting_for_multi_glaseo`**
   - Usuario detectó múltiples productos
   - Esperando que especifique glaseo

2. **`waiting_for_multi_language`**
   - Precios calculados
   - Esperando selección de idioma

### 3. Generador de PDF Consolidado

**Archivo:** `app/services/pdf_generator.py`

```python
def generate_consolidated_quote_pdf(
    self, 
    products_info: list,
    user_phone: str = None,
    language: str = "es",
    glaseo_percentage: int = 20,
    destination: str = None
) -> str:
    """
    Genera PDF con tabla de múltiples productos
    """
```

**Características:**
- Tabla con filas alternadas (mejor legibilidad)
- Multiidioma (español/inglés)
- Información consolidada
- Diseño profesional

### 4. Flujo en Routes

**Archivo:** `app/routes.py`

```python
# 1. Detectar múltiples productos
multiple_products = openai_service.detect_multiple_products(Body)

if multiple_products and len(multiple_products) > 1:
    # Mostrar lista y pedir glaseo
    session_manager.set_session_state(user_id, 'waiting_for_multi_glaseo', {
        'products': multiple_products
    })

# 2. Usuario responde con glaseo
elif session['state'] == 'waiting_for_multi_glaseo':
    # Calcular precios para todos
    for product_data in products:
        price_info = pricing_service.get_shrimp_price(query)
        products_info.append(price_info)
    
    # Pedir idioma
    session_manager.set_session_state(user_id, 'waiting_for_multi_language', {
        'products_info': products_info
    })

# 3. Usuario selecciona idioma
elif session['state'] == 'waiting_for_multi_language':
    # Generar PDF consolidado
    pdf_path = pdf_generator.generate_consolidated_quote_pdf(...)
    # Enviar por WhatsApp
```

## ✅ Ventajas

1. **Eficiencia:** Un solo PDF en lugar de múltiples
2. **Profesional:** Tabla organizada y clara
3. **Comparación fácil:** Cliente ve todos los precios juntos
4. **Menos spam:** No envía 8 PDFs separados
5. **Flexible:** Maneja productos sin precio disponible

## 🧪 Testing

### Test Implementado
```bash
python test_consolidated_quote.py
```

**Resultado:**
```
✅ Detectados: 8 productos
✅ Precios calculados: 6/8
✅ PDF generado: 2684 bytes
✅ Test completado exitosamente
```

## 📊 Casos de Uso

### Caso 1: Todos los Productos con Precio
```
Cliente: [8 productos]
Bot: [Detecta 8]
Cliente: 20% glaseo
Bot: ✅ 8/8 productos calculados
Cliente: Español
Bot: [Envía PDF con 8 productos]
```

### Caso 2: Algunos Productos Sin Precio
```
Cliente: [8 productos]
Bot: [Detecta 8]
Cliente: 20% glaseo
Bot: ✅ 6/8 productos calculados
     ⚠️ 2 sin precio disponible
Cliente: Español
Bot: [Envía PDF con 6 productos + nota de 2 sin precio]
```

### Caso 3: Un Solo Producto (Flujo Normal)
```
Cliente: "Proforma HLSO 16/20"
Bot: [Detecta 1 producto]
Bot: [Usa flujo normal, no consolidado]
```

## 🔄 Compatibilidad

- ✅ Compatible con flujo existente de un solo producto
- ✅ Compatible con modificación de flete
- ✅ Compatible con ambos idiomas
- ✅ Compatible con todos los productos existentes

## 📝 Archivos Modificados

1. **`app/services/openai_service.py`**
   - Agregado `detect_multiple_products()`

2. **`app/services/pdf_generator.py`**
   - Agregado `generate_consolidated_quote_pdf()`

3. **`app/routes.py`**
   - Agregada detección de múltiples productos
   - Agregados estados `waiting_for_multi_glaseo` y `waiting_for_multi_language`
   - Agregado flujo completo de cotización consolidada

4. **`app/services/utils.py`**
   - Agregado `parse_multiple_products()` (también en openai_service.py)

## 🚀 Estado

**✅ IMPLEMENTACIÓN COMPLETADA Y PROBADA**

- ✅ Detección de múltiples productos
- ✅ Cálculo de precios para todos
- ✅ Generación de PDF consolidado
- ✅ Envío por WhatsApp
- ✅ Manejo de productos sin precio
- ✅ Multiidioma
- ✅ Tests pasando

---

**Fecha de implementación:** 11/10/2025  
**Estado:** ✅ Listo para producción
