# 🔒 Flujo de Consentimiento para Entrenamiento

## 📋 Resumen

El sistema solicita consentimiento al usuario la primera vez que interactúa con el bot, cumpliendo con GDPR y leyes de privacidad.

---

## 🔄 Flujo Completo

### **1. Primera Interacción del Usuario**

```
Usuario: "Hola, necesito precios"
         ↓
Bot detecta: Primera vez (no ha dado consentimiento)
         ↓
Bot envía mensaje de consentimiento
```

**Mensaje enviado:**
```
👋 ¡Bienvenido a BGR Export!

🤖 Soy tu asistente para cotizaciones de camarón.

📊 **Solicitud de Consentimiento:**
Para mejorar nuestro servicio, ¿autorizas que usemos tus mensajes 
de forma anonimizada para entrenar nuestra IA?

🔒 **Garantizamos:**
• Toda información personal será anonimizada
• Cumplimos con GDPR y leyes de privacidad
• Puedes revocar el consentimiento cuando quieras

**Responde:**
• **Sí** o **1** para aceptar
• **No** o **2** para rechazar
```

---

### **2. Usuario Acepta**

```
Usuario: "Sí" o "1" o "acepto"
         ↓
Sistema: consent_for_training = True
         ↓
Bot confirma y continúa
```

**Mensaje de confirmación:**
```
✅ ¡Gracias! Tus mensajes nos ayudarán a mejorar el servicio.

🔒 Toda tu información será anonimizada y protegida.

Ahora, ¿en qué puedo ayudarte? 🦐
```

**¿Qué pasa después?**
- ✅ Todos los mensajes del usuario se capturan automáticamente
- ✅ Se anonimizan antes de almacenar
- ✅ Se procesan para entrenamiento
- ✅ El usuario puede seguir usando el bot normalmente

---

### **3. Usuario Rechaza**

```
Usuario: "No" o "2" o "rechazar"
         ↓
Sistema: consent_for_training = False
         ↓
Bot confirma y continúa
```

**Mensaje de confirmación:**
```
👍 Entendido. No usaremos tus mensajes para entrenamiento.

Ahora, ¿en qué puedo ayudarte? 🦐
```

**¿Qué pasa después?**
- ❌ Los mensajes NO se capturan para entrenamiento
- ✅ El usuario puede seguir usando el bot normalmente
- ✅ Puede cambiar de opinión más tarde

---

## 🔧 Comandos Disponibles

### **Ver Estado del Consentimiento**

```
Usuario: "consentimiento" o "consent" o "privacidad"
         ↓
Bot muestra estado actual y opciones
```

**Respuesta si ACEPTADO:**
```
🔒 **Estado de Consentimiento**

Estado actual: ✅ ACEPTADO

Tus mensajes se usan de forma anonimizada para mejorar el servicio.

**Para revocar el consentimiento:**
Escribe: 'revocar consentimiento' o 'no consent'

🔒 Toda tu información está protegida y anonimizada.
```

**Respuesta si NO ACEPTADO:**
```
🔒 **Estado de Consentimiento**

Estado actual: ❌ NO ACEPTADO

Tus mensajes NO se usan para entrenamiento.

**Para otorgar consentimiento:**
Escribe: 'acepto consentimiento' o 'accept consent'

Esto nos ayudará a mejorar el servicio para todos.
```

---

### **Revocar Consentimiento**

```
Usuario: "revocar consentimiento" o "no consent" o "revocar"
         ↓
Sistema: consent_for_training = False
         ↓
Bot confirma
```

**Respuesta:**
```
✅ **Consentimiento revocado**

Tus mensajes ya NO se usarán para entrenamiento.

Puedes volver a otorgarlo cuando quieras escribiendo 'consentimiento'.
```

---

### **Otorgar Consentimiento (después de haberlo rechazado)**

```
Usuario: "acepto consentimiento" o "accept consent" o "acepto"
         ↓
Sistema: consent_for_training = True
         ↓
Bot confirma
```

**Respuesta:**
```
✅ **Consentimiento otorgado**

¡Gracias! Tus mensajes nos ayudarán a mejorar el servicio.

🔒 Toda tu información será anonimizada y protegida.

Puedes revocarlo cuando quieras escribiendo 'revocar consentimiento'.
```

---

## 📊 Datos Almacenados

### **Con Consentimiento:**

```json
{
  "user_id": "whatsapp:+593999999999",
  "consent_for_training": true,
  "consent_timestamp": 1700000000.0,
  "consent_asked": true
}
```

### **Sin Consentimiento:**

```json
{
  "user_id": "whatsapp:+593999999999",
  "consent_for_training": false,
  "consent_timestamp": 1700000000.0,
  "consent_asked": true
}
```

---

## 🔒 Garantías de Privacidad

### **1. Anonimización Automática**

Antes de almacenar cualquier mensaje, se anonimizan:
- ✅ Números de teléfono → `[PHONE]`
- ✅ Emails → `[EMAIL]`
- ✅ Direcciones → `[ADDRESS]`
- ✅ IDs → `[ID]`
- ✅ Números de cuenta → `[ACCOUNT]`

### **2. Datos NO Anonimizados**

Se preservan términos comerciales:
- ✅ Productos (HLSO, HOSO, etc.)
- ✅ Tallas (16/20, 21/25, etc.)
- ✅ Términos (glaseo, flete, CFR, etc.)

### **3. Cumplimiento GDPR**

- ✅ Consentimiento explícito requerido
- ✅ Información clara sobre el uso
- ✅ Derecho a revocar en cualquier momento
- ✅ Datos anonimizados
- ✅ Transparencia total

---

## 🎯 Casos de Uso

### **Caso 1: Usuario Nuevo Acepta**

```
1. Usuario: "Hola"
   Bot: [Solicitud de consentimiento]

2. Usuario: "Sí"
   Bot: "✅ ¡Gracias! Ahora, ¿en qué puedo ayudarte?"

3. Usuario: "HLSO 16/20 con 20% glaseo"
   Bot: [Genera proforma]
   Sistema: [Captura mensaje para entrenamiento]
```

### **Caso 2: Usuario Nuevo Rechaza**

```
1. Usuario: "Hola"
   Bot: [Solicitud de consentimiento]

2. Usuario: "No"
   Bot: "👍 Entendido. Ahora, ¿en qué puedo ayudarte?"

3. Usuario: "HLSO 16/20 con 20% glaseo"
   Bot: [Genera proforma]
   Sistema: [NO captura mensaje]
```

### **Caso 3: Usuario Cambia de Opinión**

```
1. Usuario: "consentimiento"
   Bot: [Muestra estado actual]

2. Usuario: "acepto consentimiento"
   Bot: "✅ Consentimiento otorgado"

3. [Desde ahora se capturan mensajes]
```

### **Caso 4: Usuario Revoca**

```
1. Usuario: "revocar consentimiento"
   Bot: "✅ Consentimiento revocado"

2. [Desde ahora NO se capturan mensajes]
```

---

## 📈 Estadísticas

### **Ver Tasa de Consentimiento**

```bash
curl http://localhost:8000/webhook/training/stats
```

**Respuesta:**
```json
{
  "sessions": {
    "total": 100,
    "with_consent": 75,
    "consent_rate": "75.0%"
  }
}
```

---

## 🛠️ Implementación Técnica

### **Verificar Consentimiento en Código**

```python
from app.services.session import session_manager

# Verificar si tiene consentimiento
has_consent = session_manager.get_training_consent(user_id)

if has_consent:
    # Capturar mensaje para entrenamiento
    pipeline.capture_message(user_id, message, "user")
```

### **Establecer Consentimiento**

```python
# Otorgar
session_manager.set_training_consent(user_id, True)

# Revocar
session_manager.set_training_consent(user_id, False)
```

---

## ✅ Checklist de Cumplimiento

- [x] Solicitud de consentimiento en primera interacción
- [x] Información clara sobre el uso de datos
- [x] Opción de aceptar o rechazar
- [x] Anonimización automática
- [x] Derecho a revocar en cualquier momento
- [x] Comando para ver estado
- [x] Comando para cambiar consentimiento
- [x] Registro de timestamp del consentimiento
- [x] Documentación completa
- [x] Cumplimiento GDPR

---

## 📚 Referencias

- [GDPR Official Site](https://gdpr.eu/)
- [OpenAI Data Usage Policy](https://openai.com/policies/usage-policies)
- [WhatsApp Business Policy](https://www.whatsapp.com/legal/business-policy)

---

**Última actualización:** 2024-11-26
