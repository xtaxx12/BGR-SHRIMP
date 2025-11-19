"""
Modelos Pydantic para documentación de API y validación de datos
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ProductType(str, Enum):
    """Tipos de productos de camarón disponibles"""
    HLSO = "HLSO"
    HOSO = "HOSO"
    PD_IQF = "P&D IQF"
    PD_BLOQUE = "P&D BLOQUE"
    EZ_PEEL = "EZ PEEL"
    PUD_EUROPA = "PuD-EUROPA"
    PUD_EEUU = "PuD-EEUU"
    COOKED = "COOKED"
    PRE_COCIDO = "PRE-COCIDO"
    COCIDO_SIN_TRATAR = "COCIDO SIN TRATAR"


class SizeType(str, Enum):
    """Tallas de camarón disponibles"""
    U15 = "U15"
    SIZE_16_20 = "16/20"
    SIZE_20_30 = "20/30"
    SIZE_21_25 = "21/25"
    SIZE_26_30 = "26/30"
    SIZE_30_40 = "30/40"
    SIZE_31_35 = "31/35"
    SIZE_36_40 = "36/40"
    SIZE_40_50 = "40/50"
    SIZE_41_50 = "41/50"
    SIZE_50_60 = "50/60"
    SIZE_51_60 = "51/60"
    SIZE_60_70 = "60/70"
    SIZE_61_70 = "61/70"
    SIZE_70_80 = "70/80"
    SIZE_71_90 = "71/90"


class LanguageType(str, Enum):
    """Idiomas soportados para PDFs"""
    SPANISH = "es"
    ENGLISH = "en"


class HealthStatus(BaseModel):
    """Modelo de respuesta para health check básico"""
    status: str = Field(..., description="Estado general del servicio", example="healthy")
    service: str = Field(..., description="Nombre del servicio", example="bgr-whatsapp-bot")
    version: str = Field(..., description="Versión del servicio", example="2.0.0")
    environment: str = Field(..., description="Entorno de ejecución", example="production")
    components: Dict[str, bool] = Field(
        ...,
        description="Estado de componentes críticos",
        example={
            "twilio_configured": True,
            "google_sheets_configured": True,
            "openai_configured": True
        }
    )
    message: Optional[str] = Field(None, description="Mensaje adicional si hay problemas")


class ComponentCheck(BaseModel):
    """Estado de un componente individual"""
    status: str = Field(..., description="Estado del componente", example="ok")
    configured: bool = Field(..., description="Si el componente está configurado", example=True)
    data_loaded: Optional[bool] = Field(None, description="Si los datos están cargados")
    error: Optional[str] = Field(None, description="Mensaje de error si aplica")


class DetailedHealthStatus(BaseModel):
    """Modelo de respuesta para health check detallado"""
    status: str = Field(..., description="Estado general del sistema", example="healthy")
    timestamp: float = Field(..., description="Timestamp Unix de la verificación", example=1700000000.0)
    checks: Dict[str, ComponentCheck] = Field(
        ...,
        description="Estado detallado de cada componente"
    )


class PriceInfo(BaseModel):
    """Información de precio de un producto"""
    producto: str = Field(..., description="Nombre del producto", example="HLSO")
    talla: str = Field(..., description="Talla del producto", example="16/20")
    precio_base_kg: float = Field(..., description="Precio base por kg", example=11.45)
    precio_fob_kg: float = Field(..., description="Precio FOB por kg", example=11.70)
    precio_final_kg: float = Field(..., description="Precio final CFR por kg", example=11.95)
    factor_glaseo: Optional[float] = Field(None, description="Factor de glaseo aplicado", example=0.80)
    glaseo_percentage: Optional[int] = Field(None, description="Porcentaje de glaseo", example=20)
    flete: Optional[float] = Field(None, description="Costo de flete por kg", example=0.25)
    destination: Optional[str] = Field(None, description="Destino del envío", example="Houston")
    usar_libras: bool = Field(False, description="Si usa libras en lugar de kg")
    cliente_nombre: Optional[str] = Field(None, description="Nombre del cliente")


class ErrorResponse(BaseModel):
    """Respuesta de error estándar"""
    error: bool = Field(True, description="Indica que es un error")
    error_message: str = Field(..., description="Mensaje de error descriptivo")
    product: Optional[str] = Field(None, description="Producto solicitado")
    size: Optional[str] = Field(None, description="Talla solicitada")
    available_sizes: Optional[List[str]] = Field(None, description="Tallas disponibles para el producto")


class WhatsAppMessage(BaseModel):
    """Mensaje de WhatsApp recibido"""
    Body: str = Field(..., description="Contenido del mensaje", example="Precio HLSO 16/20")
    From: str = Field(..., description="Número de teléfono del remitente", example="whatsapp:+593999999999")
    To: str = Field(..., description="Número de teléfono del destinatario", example="whatsapp:+14155238886")
    MessageSid: str = Field(..., description="ID único del mensaje", example="SM1234567890abcdef")
    NumMedia: int = Field(0, description="Número de archivos multimedia adjuntos")
    MediaUrl0: Optional[str] = Field(None, description="URL del primer archivo multimedia")
    MediaContentType0: Optional[str] = Field(None, description="Tipo de contenido del primer archivo")


class AdminDataStatus(BaseModel):
    """Estado de los datos del sistema"""
    status: str = Field(..., description="Estado general de los datos", example="ok")
    google_sheets_connected: bool = Field(..., description="Si Google Sheets está conectado")
    products_loaded: int = Field(..., description="Número de productos cargados", example=8)
    total_sizes: int = Field(..., description="Total de tallas disponibles", example=45)
    last_update: Optional[str] = Field(None, description="Timestamp de última actualización")
    products: Dict[str, List[str]] = Field(
        ...,
        description="Productos y sus tallas disponibles",
        example={
            "HLSO": ["16/20", "21/25", "26/30"],
            "HOSO": ["20/30", "30/40", "40/50"]
        }
    )


class ReloadDataResponse(BaseModel):
    """Respuesta de recarga de datos"""
    message: str = Field(..., description="Mensaje de confirmación", example="Datos recargados exitosamente")
    success: bool = Field(..., description="Si la recarga fue exitosa")
    products_loaded: int = Field(..., description="Número de productos cargados")
    timestamp: float = Field(..., description="Timestamp de la recarga")


class RootResponse(BaseModel):
    """Respuesta del endpoint raíz"""
    message: str = Field(..., description="Mensaje de bienvenida")
    version: str = Field(..., description="Versión de la API")
    description: str = Field(..., description="Descripción del servicio")
    docs: str = Field(..., description="URL de la documentación")
    health: str = Field(..., description="URL del health check")


# Ejemplos para documentación
EXAMPLE_PRICE_INFO = {
    "producto": "HLSO",
    "talla": "16/20",
    "precio_base_kg": 11.45,
    "precio_fob_kg": 11.70,
    "precio_final_kg": 11.95,
    "factor_glaseo": 0.80,
    "glaseo_percentage": 20,
    "flete": 0.25,
    "destination": "Houston",
    "usar_libras": False,
    "cliente_nombre": "Cliente Ejemplo"
}

EXAMPLE_ERROR_RESPONSE = {
    "error": True,
    "error_message": "La talla 20/30 no está disponible para HLSO. Tallas disponibles: 16/20, 21/25, 26/30, 31/35, 36/40, 41/50, 51/60, 61/70, 71/90",
    "product": "HLSO",
    "size": "20/30",
    "available_sizes": ["16/20", "21/25", "26/30", "31/35", "36/40", "41/50", "51/60", "61/70", "71/90"]
}

EXAMPLE_WHATSAPP_MESSAGE = {
    "Body": "Precio cfr de HLSO 16/20 con 0.25 de flete",
    "From": "whatsapp:+593999999999",
    "To": "whatsapp:+14155238886",
    "MessageSid": "SM1234567890abcdef",
    "NumMedia": 0
}
