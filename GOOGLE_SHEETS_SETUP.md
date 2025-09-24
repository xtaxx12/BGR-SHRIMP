# 📊 Configuración de Google Sheets para ShrimpBot

## 🎯 Objetivo
Configurar ShrimpBot para obtener los datos de precios directamente desde Google Sheets en lugar de un archivo Excel local.

## 📋 Pasos de Configuración

### 1. Preparar Google Sheets
1. **Sube tu archivo Excel a Google Sheets**
   - Ve a [Google Sheets](https://sheets.google.com)
   - Crea una nueva hoja o sube tu archivo Excel existente
   - Asegúrate de que tenga una hoja llamada "PRECIOS FOB"
   - Copia el ID de la hoja desde la URL (la parte entre `/d/` y `/edit`)

### 2. Crear Service Account en Google Cloud
1. **Ve a Google Cloud Console**
   - Visita [Google Cloud Console](https://console.cloud.google.com)
   - Crea un nuevo proyecto o selecciona uno existente

2. **Habilitar APIs necesarias**
   - Ve a "APIs & Services" > "Library"
   - Busca y habilita "Google Sheets API"
   - Busca y habilita "Google Drive API"

3. **Crear Service Account**
   - Ve a "APIs & Services" > "Credentials"
   - Haz clic en "Create Credentials" > "Service Account"
   - Completa el nombre y descripción
   - Haz clic en "Create and Continue"
   - No necesitas asignar roles específicos, haz clic en "Done"

4. **Generar clave JSON**
   - En la lista de Service Accounts, haz clic en el que acabas de crear
   - Ve a la pestaña "Keys"
   - Haz clic en "Add Key" > "Create new key"
   - Selecciona "JSON" y haz clic en "Create"
   - Se descargará un archivo JSON con las credenciales

### 3. Compartir Google Sheets con Service Account
1. **Obtener email del Service Account**
   - Abre el archivo JSON descargado
   - Copia el valor de `client_email`

2. **Compartir la hoja**
   - Ve a tu Google Sheets
   - Haz clic en "Share" (Compartir)
   - Pega el email del Service Account
   - Dale permisos de "Viewer" (Lector)
   - Haz clic en "Send"

### 4. Configurar Variables de Entorno

#### Opción A: Archivo .env (Desarrollo)
```bash
# ID de Google Sheets (desde la URL)
GOOGLE_SHEETS_ID=1ABC123def456GHI789jkl

# Credenciales JSON (todo en una línea)
GOOGLE_SHEETS_CREDENTIALS={"type": "service_account", "project_id": "tu-proyecto", ...}
```

#### Opción B: Variables de Entorno del Sistema (Producción)
```bash
export GOOGLE_SHEETS_ID="1ABC123def456GHI789jkl"
export GOOGLE_SHEETS_CREDENTIALS='{"type": "service_account", "project_id": "tu-proyecto", ...}'
```

### 5. Formato del JSON de Credenciales
El contenido del archivo JSON descargado debe ser convertido a una sola línea:

```json
{"type": "service_account", "project_id": "tu-proyecto-123", "private_key_id": "abc123", "private_key": "-----BEGIN PRIVATE KEY-----\nTU_CLAVE_PRIVADA\n-----END PRIVATE KEY-----\n", "client_email": "tu-service-account@tu-proyecto.iam.gserviceaccount.com", "client_id": "123456789", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/tu-service-account%40tu-proyecto.iam.gserviceaccount.com"}
```

## 🔄 Funcionamiento

### Fuente de Datos Híbrida
1. **Primaria**: Google Sheets (datos siempre actualizados)
2. **Fallback**: Excel local (si Google Sheets no está disponible)
3. **Ejemplo**: Datos de muestra (si ninguna fuente está disponible)

### Recarga Automática
- Los datos se recargan automáticamente en cada consulta
- Endpoint manual: `POST /webhook/reload-data`

## 🧪 Verificación

### Probar la Configuración
```bash
# Activar entorno virtual
venv\Scripts\activate

# Probar conexión
python -c "from app.services.google_sheets import GoogleSheetsService; gs = GoogleSheetsService(); print('✅ Configurado correctamente' if gs.prices_data else '❌ Error de configuración')"
```

### Logs de Verificación
Busca estos mensajes en los logs:
- ✅ `"Conexión con Google Sheets establecida exitosamente"`
- ✅ `"Datos cargados desde Google Sheets: X tallas en Y productos"`
- ⚠️ `"Credenciales de Google Sheets no configuradas, usando datos de ejemplo"`

## 🔧 Troubleshooting

### Error: "Credenciales no configuradas"
- Verifica que las variables `GOOGLE_SHEETS_ID` y `GOOGLE_SHEETS_CREDENTIALS` estén configuradas
- Asegúrate de que el JSON esté en una sola línea sin saltos de línea

### Error: "Permission denied"
- Verifica que hayas compartido la hoja con el email del Service Account
- Asegúrate de que las APIs estén habilitadas en Google Cloud

### Error: "Worksheet not found"
- Verifica que tu Google Sheets tenga una hoja llamada "PRECIOS FOB"
- Asegúrate de que el ID de la hoja sea correcto

## 🚀 Ventajas de Google Sheets

1. **Datos Siempre Actualizados**: Los cambios en Google Sheets se reflejan inmediatamente
2. **Colaboración**: Múltiples personas pueden actualizar los precios
3. **Acceso Remoto**: No necesitas acceso al servidor para actualizar datos
4. **Historial**: Google Sheets mantiene un historial de cambios
5. **Backup Automático**: Los datos están respaldados en la nube

## 📱 Uso con ShrimpBot

Una vez configurado, ShrimpBot:
- ✅ Obtendrá precios actualizados en tiempo real
- ✅ Funcionará igual que antes para los usuarios
- ✅ Tendrá fallback al Excel local si hay problemas
- ✅ Mostrará logs claros sobre la fuente de datos utilizada