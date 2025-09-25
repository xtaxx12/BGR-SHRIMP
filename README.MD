# 🦐 ShrimpBot - BGR Export WhatsApp Bot

Bot de WhatsApp para consultas de precios de camarón de BGR Export con integración a Google Sheets y cálculos automáticos.

## ✨ Características

- 🤖 **Interfaz conversacional inteligente** con menús interactivos
- 📊 **Datos en tiempo real** desde Google Sheets
- 🧮 **Cálculos automáticos** usando fórmulas del Excel (FOB, Glaseo, Flete)
- 🦐 **Múltiples productos**: HOSO, HLSO, P&D IQF, P&D BLOQUE, PuD-EUROPA, EZ PEEL, PuD-EEUU, COOKED, PRE-COCIDO, COCIDO SIN TRATAR
- 📏 **Todas las tallas disponibles** según inventario
- 💰 **Cálculos de totales** para cantidades específicas
- 🌍 **Soporte para destinos** internacionales
- 📱 **Integración completa** con WhatsApp Business API
- 📄 **Generación de PDFs** para cotizaciones

## 🚀 Instalación Local

### Prerrequisitos
- Python 3.8+
- Cuenta de Twilio con WhatsApp Business API
- Google Sheets con datos de precios (opcional)

### Pasos
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
   # Edita .env con tus credenciales reales
   ```

5. **Ejecuta el bot**
   ```bash
   python start.py
   ```

## ☁️ Despliegue en Render

### Variables de Entorno Requeridas

```bash
# Twilio WhatsApp (OBLIGATORIO)
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+tu_numero

# Configuración del Servidor
PORT=10000
DEBUG=False
BASE_URL=https://tu-app.onrender.com

# Google Sheets (RECOMENDADO)
GOOGLE_SHEETS_ID=tu_sheet_id
GOOGLE_SHEETS_CREDENTIALS={"type":"service_account",...}

# Opcional
EXCEL_PATH=data/CALCULO_DE_PRECIOS-AGUAJE17.xlsx
OPENAI_API_KEY=tu_openai_key
```

## 📱 Uso del Bot

### Comandos Disponibles

- `hola` - Mostrar menú principal
- `1` - Consultar precios
- `2` - Información de productos
- `3` - Contacto comercial
- `menu` - Volver al menú principal
- `confirmar` - Generar PDF de cotización
- `ayuda` - Mostrar ayuda

### Flujo de Consulta

1. **Saludo inicial** → Menú principal
2. **Seleccionar "Precios"** → Lista de tallas
3. **Elegir talla** → Lista de productos disponibles
4. **Seleccionar producto** → Cotización completa
5. **Confirmar** → Generar PDF

### Ejemplos de Consultas Directas

```
Usuario: "precio HLSO 16/20"
Usuario: "21/25 para 15000 lb destino China"
Usuario: "P&D IQF 26/30"
```

## 🧮 Cálculos Automáticos

El bot usa las **fórmulas exactas** del Excel:

1. **PRECIO BASE** = Precio desde Google Sheets
2. **PRECIO FOB** = `Precio Base - Costo Fijo`
3. **PRECIO GLASEO** = `Precio FOB × Factor Glaseo`
4. **PRECIO FINAL** = `Precio Glaseo + Flete`

### Factores (configurables):
- **Costo Fijo**: $0.29
- **Factor Glaseo**: 0.7
- **Flete**: $0.20

## 📊 Fuentes de Datos

### Prioridad de Datos:
1. **Google Sheets** (tiempo real) - Recomendado
2. **Excel local** (fallback)
3. **Datos de ejemplo** (desarrollo)

### Estructura de Google Sheets:
- Hoja: "PRECIOS FOB"
- Productos organizados en columnas
- Tallas en filas
- Precios en USD por kg y lb

## 🔧 Arquitectura

```
app/
├── routes.py              # Rutas principales de WhatsApp
├── services/
│   ├── google_sheets.py   # Integración con Google Sheets
│   ├── excel.py          # Manejo de Excel local
│   ├── pricing.py        # Lógica de precios
│   ├── interactive.py    # Mensajes interactivos
│   ├── session.py        # Manejo de sesiones
│   ├── utils.py          # Utilidades y formateo
│   ├── pdf_generator.py  # Generación de PDFs
│   └── whatsapp_sender.py # Envío de mensajes
├── data/                 # Archivos Excel
└── generated_pdfs/       # PDFs generados
```

## 🔒 Seguridad

- ❌ **NUNCA** subas el archivo `.env` al repositorio
- ✅ Usa `.env.example` como plantilla
- ✅ Configura las variables de entorno en tu servidor de producción
- ✅ Las credenciales de Google Sheets están encriptadas

## 🚀 Características Avanzadas

- **Sesiones persistentes** por usuario
- **Validación de entrada** robusta
- **Manejo de errores** completo
- **Logs detallados** para debugging
- **Fallback automático** entre fuentes de datos
- **Cálculos precisos** con redondeo apropiado

## 📈 Monitoreo

El bot incluye logging detallado para:
- Conexiones a Google Sheets
- Cálculos de precios
- Interacciones de usuarios
- Errores y excepciones

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es privado y pertenece a BGR Export.

## 📞 Soporte

Para soporte técnico o preguntas sobre el bot:
- Email: soporte@bgrexport.com
- WhatsApp: +593 XXX XXXX