import re
from typing import Dict, Optional

def parse_user_message(message: str) -> Optional[Dict]:
    """
    Parsea el mensaje del usuario para extraer información relevante
    """
    if not message:
        return None
    
    message = message.strip().upper()
    
    # Patrones para extraer información
    size_pattern = r'\b(\d+/\d+)\b'
    quantity_pattern = r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:LB|LIBRAS?|POUNDS?)\b'
    destination_pattern = r'(?:DESTINO|PARA|A)\s+([A-Z\s]+?)(?:\s|$)'
    
    result = {}
    
    # Extraer talla
    size_match = re.search(size_pattern, message)
    if size_match:
        result['size'] = size_match.group(1)
    
    # Extraer cantidad
    quantity_match = re.search(quantity_pattern, message)
    if quantity_match:
        result['quantity'] = quantity_match.group(1)
    
    # Extraer destino
    destination_match = re.search(destination_pattern, message)
    if destination_match:
        result['destination'] = destination_match.group(1).strip()
    
    # Si no encontramos talla, intentar extraer solo números
    if not result.get('size'):
        # Buscar patrones como "16 20", "16-20", etc.
        alt_size_pattern = r'\b(\d+)[\s\-/](\d+)\b'
        alt_match = re.search(alt_size_pattern, message)
        if alt_match:
            result['size'] = f"{alt_match.group(1)}/{alt_match.group(2)}"
    
    return result if result else None

def format_price_response(price_info: Dict) -> str:
    """
    Formatea la respuesta con la información de precios
    """
    try:
        response = f"📦 **BGR EXPORT - Cotización Camarón**\n\n"
        response += f"📏 **Talla:** {price_info['size']}\n"
        response += f"🦐 **Producto:** {price_info['producto']}\n"
        response += f"💲 **Precio base:** ${price_info['precio_base']:.2f}/lb\n\n"
        
        response += f"⚙️ **Ajustes aplicados:**\n"
        response += f"• Costo fijo: ${price_info['costo_fijo']:.2f}/lb\n"
        response += f"• Glaseo (factor): {price_info['factor_glaseo']} ({int(price_info['factor_glaseo']*100)}% camarón real)\n"
        response += f"• Flete: ${price_info['flete']:.2f}/lb\n\n"
        
        response += f"💰 **Precio final estimado: ${price_info['precio_final']:.2f}/lb**\n"
        
        # Agregar información adicional si está disponible
        if price_info.get('quantity'):
            try:
                qty = float(price_info['quantity'].replace(',', ''))
                total = qty * price_info['precio_final']
                response += f"\n📊 **Para {price_info['quantity']} lb:**\n"
                response += f"💵 **Total estimado: ${total:,.2f}**"
            except:
                pass
        
        if price_info.get('destination'):
            response += f"\n🌍 **Destino:** {price_info['destination']}"
        
        response += f"\n\n_Precios sujetos a confirmación final_"
        
        return response
        
    except Exception as e:
        return f"❌ Error formateando respuesta: {str(e)}"

def extract_size_from_text(text: str) -> Optional[str]:
    """
    Extrae la talla del camarón del texto
    """
    if not text:
        return None
    
    # Patrones comunes para tallas
    patterns = [
        r'\b(\d+/\d+)\b',  # 16/20
        r'\b(\d+)\s*[-/]\s*(\d+)\b',  # 16-20, 16 / 20
        r'\b(\d+)\s+(\d+)\b'  # 16 20
    ]
    
    text = text.upper().strip()
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            if len(match.groups()) == 1:
                return match.group(1)
            else:
                return f"{match.group(1)}/{match.group(2)}"
    
    return None