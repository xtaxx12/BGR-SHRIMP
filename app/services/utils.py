import re
from typing import Dict, Optional

def parse_user_message(message: str) -> Optional[Dict]:
    """
    Parsea el mensaje del usuario para extraer información relevante
    """
    if not message:
        return None
    
    message_original = message.strip()
    message = message_original.upper()
    
    # Excluir saludos simples y mensajes conversacionales
    simple_messages = [
        'HOLA', 'HELLO', 'HI', 'BUENOS DIAS', 'BUENAS TARDES', 'BUENAS NOCHES',
        'COMO ESTAS', 'QUE TAL', 'Q HACES', 'COMO ANDAS', 'AYUDA', 'HELP',
        'MENU', 'GRACIAS', 'THANKS', 'OK', 'SI', 'NO', 'BIEN', 'MAL'
    ]
    
    if message.strip() in simple_messages:
        return None
    
    # Patrones para extraer información
    size_pattern = r'\b(\d+/\d+)\b'
    quantity_pattern = r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:LB|LIBRAS?|POUNDS?|KG|KILOS?)\b'
    destination_pattern = r'(?:DESTINO|PARA|A)\s+([A-Z\s]+?)(?:\s|$)'
    
    # Patrones para productos
    product_patterns = {
        'HOSO': r'\bHOSO\b',
        'HLSO': r'\bHLSO\b',
        'P&D IQF': r'\b(?:P&D\s*IQF|PD\s*IQF|PEELED\s*DEVEINED\s*IQF)\b',
        'P&D BLOQUE': r'\b(?:P&D\s*BLOQUE|PD\s*BLOQUE|PEELED\s*DEVEINED\s*BLOQUE)\b',
        'PuD-EUROPA': r'\b(?:PUD\s*EUROPA|P&D\s*EUROPA|EUROPA)\b',
        'EZ PEEL': r'\b(?:EZ\s*PEEL|EZPEEL|EASY\s*PEEL)\b'
    }
    
    result = {}
    
    # Extraer producto
    for product, pattern in product_patterns.items():
        if re.search(pattern, message):
            result['product'] = product
            break
    
    # Si no se encuentra producto específico, usar HLSO por defecto
    if 'product' not in result:
        result['product'] = 'HLSO'
    
    # Extraer talla
    size_match = re.search(size_pattern, message)
    if size_match:
        result['size'] = size_match.group(1)
    
    # Extraer cantidad y unidad
    quantity_match = re.search(quantity_pattern, message)
    if quantity_match:
        result['quantity'] = quantity_match.group(1)
        # Determinar unidad
        if re.search(r'\b(?:KG|KILOS?)\b', message):
            result['unit'] = 'kg'
        else:
            result['unit'] = 'lb'
    
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
    Formatea la respuesta con la información de precios calculados
    """
    try:
        response = f"🦐 **BGR EXPORT - Cotización Camarón** 🦐\n\n"
        response += f"📏 **Talla:** {price_info['talla']}\n"
        response += f"🏷️ **Producto:** {price_info['producto']}\n\n"
        
        # Verificar si el producto no tiene precio establecido
        # Si tenemos precios calculados válidos, no mostrar "sin precio"
        has_calculated_prices = (
            'precio_fob_kg' in price_info and 
            price_info.get('precio_fob_kg', 0) > 0
        )
        
        if not has_calculated_prices and (price_info.get('sin_precio', False) or price_info.get('precio_kg', 0) == 0):
            response += "⚠️ **SIN PRECIO ESTABLECIDO**\n\n"
            response += "📞 Para obtener cotización de este producto, contacta directamente con BGR Export.\n\n"
            response += "🏢 **Información de contacto:**\n"
            response += "   • Email: ventas@bgrexport.com\n"
            response += "   • WhatsApp: +593 XXX XXXX\n\n"
            return response
        
        # Si tenemos precios calculados con fórmulas del Excel
        elif 'precio_fob_kg' in price_info:
            response += f"💰 **PRECIOS CALCULADOS:**\n\n"
            
            # Precio base
            response += f"📊 **Precio Base:**\n"
            response += f"   • ${price_info['precio_base_kg']:.2f}/kg - ${price_info['precio_base_lb']:.2f}/lb\n\n"
            
            # Precio FOB
            response += f"🚢 **Precio FOB:**\n"
            response += f"   • ${price_info['precio_fob_kg']:.2f}/kg - ${price_info['precio_fob_lb']:.2f}/lb\n\n"
            
            # Precio con glaseo
            response += f"❄️ **Precio con Glaseo:**\n"
            response += f"   • ${price_info['precio_glaseo_kg']:.2f}/kg - ${price_info['precio_glaseo_lb']:.2f}/lb\n\n"
            
            # Precio final con flete
            response += f"✈️ **Precio Final (Glaseo + Flete):**\n"
            response += f"   • ${price_info['precio_flete_kg']:.2f}/kg - ${price_info['precio_flete_lb']:.2f}/lb\n\n"
            
            # Mostrar factores utilizados
            if 'factores' in price_info:
                factores = price_info['factores']
                response += f"⚙️ **Factores aplicados:**\n"
                response += f"   • Costo fijo: ${factores['costo_fijo']:.2f}\n"
                response += f"   • Factor glaseo: {factores['factor_glaseo']:.1f}\n"
                response += f"   • Flete: ${factores['flete']:.2f}\n\n"
            
            # Indicar método de cálculo
            response += f"🧮 **Calculado con:** {price_info.get('calculado_con', 'Excel')}\n\n"
            
        else:
            # Formato original para compatibilidad
            response += f"💲 **Precio:** ${price_info.get('precio_kg', 0):.2f}/kg - ${price_info.get('precio_lb', 0):.2f}/lb\n\n"
        
        # Agregar información adicional si está disponible
        if price_info.get('quantity'):
            try:
                qty = float(price_info['quantity'].replace(',', ''))
                unit = price_info.get('unit', 'lb')
                
                # Usar precio final si está disponible, sino precio base
                if 'precio_flete_kg' in price_info:
                    if unit == 'kg':
                        unit_price = price_info['precio_flete_kg']
                        total = qty * unit_price
                        response += f"📊 **Para {price_info['quantity']} kg (precio final):**\n"
                        response += f"💵 **Total estimado: ${total:,.2f}**\n\n"
                    else:
                        unit_price = price_info['precio_flete_lb']
                        total = qty * unit_price
                        response += f"📊 **Para {price_info['quantity']} lb (precio final):**\n"
                        response += f"💵 **Total estimado: ${total:,.2f}**\n\n"
                else:
                    # Usar precio original
                    if unit == 'kg':
                        unit_price = price_info.get('precio_kg', 0)
                        total = qty * unit_price
                        response += f"📊 **Para {price_info['quantity']} kg:**\n"
                        response += f"💵 **Total estimado: ${total:,.2f}**\n\n"
                    else:
                        unit_price = price_info.get('precio_lb', 0)
                        total = qty * unit_price
                        response += f"📊 **Para {price_info['quantity']} lb:**\n"
                        response += f"💵 **Total estimado: ${total:,.2f}**\n\n"
            except:
                pass
        
        if price_info.get('destination'):
            response += f"🌍 **Destino:** {price_info['destination']}\n\n"
        
        response += f"📋 _Precios FOB sujetos a confirmación final_\n"
        response += f"📞 **Contacto:** BGR Export\n"
        response += f"💡 _Escribe 'menu' para más opciones_"
        
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