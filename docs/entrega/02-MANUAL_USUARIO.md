# Manual de Usuario - BGR Shrimp Bot

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Primeros Pasos](#primeros-pasos)
3. [Consultas de Precios](#consultas-de-precios)
4. [Generación de Proformas](#generación-de-proformas)
5. [Comandos Disponibles](#comandos-disponibles)
6. [Casos de Uso Comunes](#casos-de-uso-comunes)
7. [Preguntas Frecuentes](#preguntas-frecuentes)
8. [Solución de Problemas](#solución-de-problemas)

---

## Introducción

### ¿Qué es BGR Shrimp Bot?

BGR Shrimp Bot es tu asistente virtual de WhatsApp para consultar precios de camarón y generar cotizaciones profesionales de manera instantánea. El bot está disponible 24/7 y puede procesar múltiples consultas simultáneamente.

### Características Principales

- 🦐 **Consulta de precios** para 8 tipos de productos
- 📏 **16 tallas diferentes** disponibles
- 💰 **Cálculos automáticos** de FOB, CFR y DDP
- 📄 **Proformas en PDF** en español e inglés
- 🎤 **Mensajes de voz** soportados
- 🌍 **Múltiples destinos** con cálculo de flete
- ❄️ **Glaseo flexible** (10%, 20%, 30%)

---

## Primeros Pasos

### Cómo Iniciar una Conversación

1. **Abre WhatsApp** en tu teléfono
2. **Busca el contacto** del BGR Shrimp Bot
3. **Envía un mensaje** de saludo o escribe `menu`

**Ejemplo de primer mensaje:**
```
Hola
```

**Respuesta del bot:**
```
👋 ¡Hola! Soy el asistente de BGR Export.

¿En qué puedo ayudarte hoy?

📋 Escribe "menu" para ver opciones
💰 O pregúntame directamente por precios
```

### Menú Principal

Para ver el menú principal en cualquier momento, escribe:
```
menu
```

**Opciones del menú:**
1. 💰 Consultar precios
2. 📄 Generar proforma
3. 🌐 Cambiar idioma
4. ℹ️ Ayuda

---

## Consultas de Precios

### Productos Disponibles

El bot maneja los siguientes tipos de camarón:

| Código | Nombre Completo | Descripción |
|--------|----------------|-------------|
| **HOSO** | Head-On Shell-On | Con cabeza y cáscara (entero) |
| **HLSO** | Headless Shell-On | Sin cabeza, con cáscara |
| **P&D IQF** | Peeled & Deveined IQF | Pelado y desvenado individual |
| **P&D BLOQUE** | Peeled & Deveined Block | Pelado y desvenado en bloque |
| **EZ PEEL** | Easy Peel | Fácil pelado |
| **PuD-EUROPA** | Peeled unDeveined Europa | Pelado sin desvena para Europa |
| **PuD-EEUU** | Peeled unDeveined USA | Pelado sin desvena para EEUU |
| **COOKED** | Cooked | Cocido |

### Tallas Disponibles

```
U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40, 
40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90
```

### Formas de Consultar Precios

#### Consulta Simple

**Formato básico:**
```
[Producto] [Talla]
```

**Ejemplos:**
```
HLSO 16/20
P&D IQF 21/25
HOSO 30/40
```

**Respuesta del bot:**
```
🦐 HLSO 16/20

💰 Precios disponibles:
• FOB: $8.50/kg
• CFR (con glaseo 20%): $9.20/kg
• DDP: Requiere destino y flete

📦 Inventario: Disponible
🏭 Origen: Ecuador

¿Deseas generar una proforma? Escribe "confirmar"
```

#### Consulta con Glaseo

**Formato:**
```
[Producto] [Talla] glaseo [porcentaje]%
```

**Ejemplos:**
```
HLSO 16/20 glaseo 10%
P&D IQF 21/25 con 20% glaseo
HOSO 30/40 al 30%
```

#### Consulta con Destino

**Formato:**
```
[Producto] [Talla] para [destino]
```

**Ejemplos:**
```
HLSO 16/20 para China
P&D IQF 21/25 destino Houston
HOSO 30/40 a Miami
```

#### Consulta Completa (DDP)

**Formato:**
```
[Producto] [Talla] DDP [destino] flete [valor]
```

**Ejemplos:**
```
HLSO 16/20 DDP China flete 0.25
P&D IQF 21/25 DDP Houston con flete de 0.30
```

### Consultas Múltiples

Puedes consultar varios productos a la vez:

**Ejemplo:**
```
Necesito precios de:
HLSO 16/20
HLSO 21/25
P&D IQF 26/30
Todos con glaseo 20%
```

**Respuesta del bot:**
```
📋 Detecté 3 productos para cotizar:
   1. HLSO 16/20
   2. HLSO 21/25
   3. P&D IQF 26/30

❄️ Glaseo: 20%

✅ Precios calculados para 3/3 productos

🌐 Selecciona el idioma para la cotización consolidada:
1️⃣ Español 🇪🇸
2️⃣ English 🇺🇸
```

### Mensajes de Voz

El bot puede procesar mensajes de audio:

1. **Mantén presionado** el botón de micrófono en WhatsApp
2. **Graba tu consulta** (ejemplo: "Precio de HLSO 16/20")
3. **Suelta** para enviar

**El bot responderá:**
```
🎤 Audio recibido: "Precio de HLSO 16/20"

[Procesa la consulta normalmente]
```

---

## Generación de Proformas

### Flujo Básico de Proforma

#### Paso 1: Consulta el Precio

```
HLSO 16/20 glaseo 20%
```

#### Paso 2: Confirma la Generación

```
confirmar
```

o

```
generar proforma
```

#### Paso 3: Selecciona el Idioma

**El bot preguntará:**
```
🌐 ¿En qué idioma deseas la proforma?

1️⃣ Español 🇪🇸
2️⃣ English 🇺🇸

Responde con el número o escribe el idioma
```

**Tu respuesta:**
```
1
```
o
```
español
```

#### Paso 4: Recibe el PDF

```
✅ Proforma generada y enviada en Español 🇪🇸

[El bot envía el PDF automáticamente]
```

### Proforma con Nombre de Cliente

**Incluye el nombre en tu consulta:**
```
Proforma HLSO 16/20 para Juan Pérez
```

o después de la consulta:
```
Cliente: Juan Pérez
```

### Proforma con Cantidad Específica

```
15000 libras de HLSO 16/20
```

o

```
10 toneladas de P&D IQF 21/25
```

### Proforma Consolidada

Para múltiples productos:

```
Proforma consolidada:
HLSO 16/20
HLSO 21/25
P&D IQF 26/30
Glaseo 20%
Cliente: Mariscos del Pacífico
```

**El bot generará un PDF con todos los productos**

### Modificar Flete de Proforma

Si necesitas cambiar el flete después de generar una proforma:

```
modifica el flete a 0.30
```

o

```
cambiar flete 0.25
```

**El bot regenerará la proforma con el nuevo flete**

---

## Comandos Disponibles

### Comandos Principales

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `menu` | Muestra el menú principal | `menu` |
| `precios` | Inicia consulta de precios | `precios` |
| `confirmar` | Genera proforma de última consulta | `confirmar` |
| `idioma` | Cambia idioma de proformas | `idioma` |
| `ayuda` | Muestra ayuda y comandos | `ayuda` |
| `cancelar` | Cancela operación actual | `cancelar` |

### Comandos de Información

| Comando | Descripción |
|---------|-------------|
| `productos` | Lista productos disponibles |
| `tallas` | Lista tallas disponibles |
| `destinos` | Lista destinos con flete |
| `terminos` | Explica términos FOB, CFR, DDP |

### Atajos Rápidos

- **Última cotización:** `última` o `last`
- **Repetir:** `repetir` o `otra vez`
- **Limpiar sesión:** `limpiar` o `reset`

---

## Casos de Uso Comunes

### Caso 1: Consulta Rápida de Precio

**Objetivo:** Obtener precio FOB de un producto

**Pasos:**
1. Envía: `HLSO 16/20`
2. Recibe precio FOB inmediatamente

**Tiempo estimado:** 2-3 segundos

---

### Caso 2: Cotización CFR con Glaseo

**Objetivo:** Precio con glaseo específico

**Pasos:**
1. Envía: `P&D IQF 21/25 glaseo 20%`
2. Recibe precio CFR con glaseo aplicado
3. Envía: `confirmar`
4. Selecciona idioma: `español`
5. Recibe PDF por WhatsApp

**Tiempo estimado:** 30-60 segundos

---

### Caso 3: Cotización DDP Completa

**Objetivo:** Precio puerta a puerta con flete

**Pasos:**
1. Envía: `HLSO 16/20 DDP China`
2. Bot pregunta por flete
3. Respondes: `flete 0.25`
4. Recibe precio DDP calculado
5. Envía: `confirmar`
6. Selecciona idioma
7. Recibe PDF

**Tiempo estimado:** 1-2 minutos

---

### Caso 4: Cotización Múltiple

**Objetivo:** Proforma con varios productos

**Pasos:**
1. Envía:
   ```
   Necesito cotización de:
   HLSO 16/20
   HLSO 21/25
   P&D IQF 26/30
   Glaseo 20%
   ```
2. Bot calcula todos los precios
3. Selecciona idioma
4. Recibe PDF consolidado

**Tiempo estimado:** 1-2 minutos

---

### Caso 5: Modificar Flete

**Objetivo:** Cambiar flete de proforma existente

**Pasos:**
1. Ya tienes una proforma generada
2. Envía: `modifica flete a 0.30`
3. Bot recalcula y regenera PDF
4. Recibe nueva proforma

**Tiempo estimado:** 30-45 segundos

---

### Caso 6: Consulta por Voz

**Objetivo:** Usar mensaje de audio

**Pasos:**
1. Graba audio: "Precio de HLSO 16/20"
2. Bot transcribe y procesa
3. Recibe respuesta normal

**Tiempo estimado:** 5-10 segundos

---

## Preguntas Frecuentes

### Sobre Precios

**P: ¿Los precios están actualizados?**  
R: Sí, los precios se sincronizan en tiempo real con Google Sheets. Siempre recibes los precios más recientes.

**P: ¿Qué significa FOB, CFR y DDP?**  
R: 
- **FOB** (Free On Board): Precio en puerto de origen
- **CFR** (Cost and Freight): FOB + flete marítimo
- **DDP** (Delivered Duty Paid): Precio puerta a puerta incluyendo todos los costos

**P: ¿Cómo se calcula el glaseo?**  
R: El glaseo reduce el peso neto. Por ejemplo, con 20% glaseo, el factor es 0.80 (80% del peso es camarón).

**P: ¿Puedo consultar precios sin generar proforma?**  
R: Sí, simplemente consulta el precio y no confirmes. No estás obligado a generar PDF.

### Sobre Proformas

**P: ¿En qué idiomas puedo generar proformas?**  
R: Español e inglés. Puedes cambiar el idioma en cada proforma.

**P: ¿Cuánto tarda en generarse el PDF?**  
R: Entre 2-5 segundos normalmente.

**P: ¿Puedo incluir el nombre del cliente?**  
R: Sí, menciona el nombre en tu consulta: "Proforma para Juan Pérez"

**P: ¿Las proformas tienen validez legal?**  
R: Sí, son documentos oficiales de BGR Export con todos los datos necesarios.

**P: ¿Puedo generar una proforma con múltiples productos?**  
R: Sí, lista todos los productos en un mensaje y el bot generará una proforma consolidada.

### Sobre el Bot

**P: ¿El bot está disponible 24/7?**  
R: Sí, puedes consultar precios en cualquier momento.

**P: ¿Cuántas consultas puedo hacer?**  
R: Hasta 30 consultas por minuto. Es suficiente para uso normal.

**P: ¿El bot entiende mensajes de voz?**  
R: Sí, puedes enviar audios y el bot los transcribirá automáticamente.

**P: ¿Qué pasa si escribo mal un producto?**  
R: El bot intentará entender tu consulta. Si no puede, te pedirá aclaración.

**P: ¿Puedo usar el bot en inglés?**  
R: Sí, el bot entiende consultas en español e inglés.

### Sobre Problemas Técnicos

**P: ¿Qué hago si el bot no responde?**  
R: Espera 30 segundos y reintenta. Si persiste, contacta soporte.

**P: ¿Qué hago si recibo un error?**  
R: Escribe `menu` para reiniciar o contacta soporte con el mensaje de error.

**P: ¿El bot guarda mi historial?**  
R: Sí, guarda tu última cotización para que puedas modificarla o regenerarla.

---

## Solución de Problemas

### Problema: Bot no responde

**Síntomas:** Envías mensaje pero no hay respuesta

**Soluciones:**
1. Verifica tu conexión a internet
2. Espera 30 segundos (puede haber demora)
3. Envía `menu` para reiniciar
4. Contacta soporte si persiste

---

### Problema: Error al generar PDF

**Síntomas:** "❌ Error generando la proforma"

**Soluciones:**
1. Verifica que consultaste un precio válido
2. Intenta nuevamente: `confirmar`
3. Si persiste, consulta el precio de nuevo
4. Contacta soporte con detalles

---

### Problema: Precio no encontrado

**Síntomas:** "❌ No se encontró precio para..."

**Soluciones:**
1. Verifica que el producto existe (ver lista de productos)
2. Verifica que la talla es correcta (ver lista de tallas)
3. Intenta con formato: `PRODUCTO TALLA` (ej: `HLSO 16/20`)
4. Contacta soporte si el producto debería existir

---

### Problema: Bot no entiende mi consulta

**Síntomas:** Bot pide aclaración o responde incorrectamente

**Soluciones:**
1. Usa formato simple: `PRODUCTO TALLA`
2. Evita abreviaciones no estándar
3. Escribe `menu` y usa opciones guiadas
4. Consulta ejemplos en este manual

---

### Problema: PDF no se descarga

**Síntomas:** Recibes link pero no se descarga

**Soluciones:**
1. Toca el link nuevamente
2. Verifica tu conexión a internet
3. Intenta desde navegador web
4. Solicita reenvío: `enviar última proforma`

---

### Problema: Flete incorrecto

**Síntomas:** El flete en la proforma no es el esperado

**Soluciones:**
1. Verifica que especificaste el flete correctamente
2. Usa formato: `flete 0.25` (con punto decimal)
3. Modifica el flete: `modifica flete a 0.30`
4. Regenera la proforma

---

## Contacto y Soporte

### Soporte Técnico

**WhatsApp:** +593 968058769  
**Email:** rojassebas765@gmail.com  
**Horario:** 24/7 para incidentes críticos

### Reportar Problemas

Al reportar un problema, incluye:
1. Descripción del problema
2. Mensaje que enviaste
3. Respuesta del bot (captura de pantalla)
4. Hora aproximada del incidente

### Sugerencias y Mejoras

Tus comentarios son importantes. Envía sugerencias a:
**Email:** rojassebas765@gmail.com

---

## Glosario de Términos

**FOB (Free On Board):** Precio del producto en el puerto de origen, sin incluir flete.

**CFR (Cost and Freight):** Precio FOB más el costo del flete marítimo.

**DDP (Delivered Duty Paid):** Precio total incluyendo todos los costos hasta la puerta del cliente.

**Glaseo:** Capa de hielo que protege el camarón. Se expresa en porcentaje del peso total.

**Talla:** Tamaño del camarón, expresado en cantidad de piezas por libra (ej: 16/20 = 16 a 20 camarones por libra).

**Proforma:** Cotización formal en formato PDF con todos los detalles del producto y precios.

**IQF (Individually Quick Frozen):** Congelado rápido individual, cada camarón congelado por separado.

---

**Versión del Manual:** 1.0  
**Última Actualización:** Enero 2025  
**Para:** BGR Export  
**Confidencialidad:** Uso interno
