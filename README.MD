# 📦 Bot de WhatsApp para Consulta de Precios de Camarón  

Este proyecto implementa un **bot de WhatsApp** para **BGR EXPORT** que automatiza la consulta de precios de camarón, cálculo de costos de flete y glaseo.  

El sistema utiliza **Python con FastAPI**, se conecta a **Twilio WhatsApp API** y obtiene la información desde un archivo **Excel (hoja PRECIOS FOB)** que se actualiza periódicamente.  

---

## 🚀 Funcionalidades  
- Consulta de precios de camarón según talla ingresada por el usuario.  
- Cálculo automático de costos adicionales:  
  - **Costo Fijo**  
  - **Glaseo (factor de rendimiento)**  
  - **Flete**  
- Generación de respuestas claras en formato tabla o imagen.  
- Lectura dinámica del archivo Excel como base de datos.  
- Escenarios flexibles:  
  - Bot con reglas predefinidas.  
  - Bot con IA (procesamiento de lenguaje natural).  

---

## 📊 Calculadora de Precios  

El sistema replica la lógica de la **calculadora del Excel (sección derecha de la hoja PRECIOS FOB)**.  

**Ejemplo de cálculo:**  
- Producto: Camarón **talla 16/20**  
- Precio base: **$8.55 por libra**  

**Ajustes aplicados:**  
1. **Costo Fijo:** $0.25 por libra  
2. **Glaseo (factor de rendimiento):** 0.7 → (70% camarón real, 30% hielo)  
3. **Flete:** $0.20 por libra  

**Resultado:**  
- Precio final de venta ≈ **$12.22 por libra**  

---

## 🏗️ Arquitectura del Sistema  

**Flujo general:**  

Usuario WhatsApp → Twilio WhatsApp API → FastAPI (Railway) → Lectura Excel → Respuesta al usuario  

---

**Componentes principales:**  
- **Lenguaje backend:** Python (FastAPI)  
- **Hosting:** Railway (escalable y económico)  
- **Mensajería:** Twilio WhatsApp API  
- **Datos:** Excel (hoja PRECIOS FOB)  
- **Opcional:** OpenAI GPT-4o-mini para IA conversacional  

---

## ⚙️ Tecnologías Recomendadas  

- **Backend:** Python 3.11+, FastAPI  
- **Excel:** `pandas`, `openpyxl`  
- **WhatsApp API:** Twilio  
- **Generación de imágenes/tablas:** Pillow  
- **Hosting:** Railway  
- **Opcional IA:** OpenAI GPT-4o-mini  

---

## 💰 Escenarios de Costos  

### Escenario 1: Bot con IA  
- Twilio WhatsApp API: $0.005 por mensaje  
- OpenAI GPT-4o-mini: $0.00015 por mensaje  
- Railway hosting: $5–$10/mes  
- **Total estimado: $15–$20/mes**  

### Escenario 2: Bot sin IA (basado en reglas)  
- Twilio WhatsApp API: $0.005 por mensaje  
- Railway hosting: $5–$10/mes  
- **Total estimado: $10–$15/mes**  

---

## 📂 Estructura esperada del proyecto  

bot-whatsapp/
│── app/
│ ├── main.py # Backend FastAPI
│ ├── routes.py # Endpoints para Twilio
│ ├── services/
│ │ ├── excel.py # Lógica de lectura de Excel
│ │ ├── pricing.py # Calculadora de precios
│ │ └── utils.py
│── data/
│ └── precios_fob.xlsx # Base de datos Excel
│── tests/
│── requirements.txt
│── README.md

---

## ▶️ Ejemplo de Flujo  

**Usuario:**  
Precio HLSO 16/20 para 15,000 lb destino China

**Bot responde:**  
📦 Producto: HLSO
📏 Talla: 16/20
💲 Precio base: $8.55/lb
⚙️ Costo fijo: $0.25/lb
🧊 Glaseo (factor): 0.7
🚚 Flete: $0.20/lb

💲 Precio final estimado: $12.22/lb


---

## 📌 Notas  
- El Excel es la **fuente de verdad**.  
- El cliente puede actualizar los precios y tallas sin tocar el código.  
- El bot reflejará automáticamente los cambios.  


