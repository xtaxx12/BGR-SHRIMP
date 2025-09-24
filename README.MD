# 🦐 ShrimpBot - BGR Export WhatsApp Bot

Bot de WhatsApp para consultas de precios de camarón de BGR Export con cálculos automáticos usando fórmulas de Excel.

## ✨ Características

- 🤖 **Interfaz conversacional inteligente** con menús interactivos
- 📊 **Consultas de precios en tiempo real** desde Excel local
- 🧮 **Cálculos automáticos** usando fórmulas del Excel (FOB, Glaseo, Flete)
- 🦐 **Múltiples productos**: HLSO, P&D IQF, P&D BLOQUE, PuD-EUROPA, EZ PEEL
- 📏 **Todas las tallas**: 16/20, 21/25, 26/30, 31/35, 36/40, 41/50, 51/60, 61/70, 71/90
- 💰 **Cálculos de totales** para cantidades específicas
- 🌍 **Soporte para destinos** internacionales
- 📱 **Integración completa** con WhatsApp Business API

## 🚀 Instalación

### Prerrequisitos
- Python 3.8+
- Cuenta de Twilio con WhatsApp Business API
- Archivo Excel con precios en `data/`

### Pasos
1. **Clona el repositorio**
   ```bash
   git clone https://github.com/xtaxx12/BGR-SHRIMP.git
   cd BGR-SHRIMP
   ```

2. **Crea entorno virtual**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Instala dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura variables de entorno**
   ```bash
   cp .env.example .env
   # Edita .env con tus credenciales reales
   ```

5. **Ejecuta el bot**
   ```bash
   python start.py
   ```

## ⚙️ Configuración

### Variables de Entorno Requeridas

Copia `.env.example` a `.env` y configura:

```bash
# Twilio WhatsApp (REQUERIDO)
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+tu_numero

# Servidor
PORT=8000
DEBUG=True

# Excel (REQUERIDO)
EXCEL_PATH=data/CALCULO_DE_PRECIOS-AGUAJE17.xlsx
```

## 📱 Uso del Bot

### Comandos Disponibles

- `hola` - Mostrar menú principal
- `precios` - Ir directamente a consulta de precios
- `menu` - Volver al menú principal
- `ayuda` - Mostrar ayuda

### Ejemplos de Consultas

```
Usuario: "precio HLSO 16/20"
Usuario: "21/25 para 15000 lb destino China"
Usuario: "P&D IQF 26/30"
```

## 🧮 Cálculos Automáticos

El bot usa las **fórmulas exactas** de tu Excel:

1. **PRECIO FOB** = `Precio Base - Costo Fijo`
2. **PRECIO GLASEO** = `Precio FOB × Factor Glaseo`
3. **PRECIO FINAL** = `Precio Glaseo + Costo Fijo + Flete`

### Factores (leídos automáticamente del Excel):
- **Costo Fijo**: $0.29
- **Factor Glaseo**: 0.7
- **Flete**: $0.20

## 🔒 Seguridad

- ❌ **NUNCA** subas el archivo `.env` al repositorio
- ✅ Usa `.env.example` como plantilla
- ✅ Configura las variables de entorno en tu servidor de producción

## � Sopor:te

Para soporte técnico o preguntas sobre el bot, contacta al equipo de desarrollo.