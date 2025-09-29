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

def parse_ai_analysis_to_query(ai_analysis: Dict) -> Optional[Dict]:
    """
    Convierte el análisis de IA en una consulta de precio válida con parámetros personalizados
    """
    if not ai_analysis or ai_analysis.get('intent') not in ['pricing', 'proforma']:
        return None
    
    # Extraer información del análisis de IA
    product = ai_analysis.get('product')
    size = ai_analysis.get('size')
    quantity = ai_analysis.get('quantity')
    destination = ai_analysis.get('destination')
    glaseo_factor = ai_analysis.get('glaseo_factor')
    flete_custom = ai_analysis.get('flete_custom')
    usar_libras = ai_analysis.get('usar_libras', False)
    cliente_nombre = ai_analysis.get('cliente_nombre')
    
    # Validar que tengamos al menos talla (producto puede ser inferido)
    if not size:
        return None
    
    # Si no hay producto específico, usar HLSO por defecto
    if not product:
        product = 'HLSO'
    
    # Determinar unidad base según destino
    unit = 'lb' if usar_libras else 'kg'
    
    # Procesar flete personalizado del usuario
    flete_value = None
    if flete_custom:
        try:
            flete_value = float(flete_custom)
        except:
            pass
    
    # Si no hay flete personalizado, usar valor por defecto
    # NO cambiar automáticamente por destino - debe venir de Google Sheets
    if not flete_value:
        flete_value = 0.20  # Valor por defecto (debería venir de Sheets)
    
    # Procesar factor de glaseo
    glaseo_value = None
    if glaseo_factor:
        try:
            # Si viene como "10" convertir a 0.10
            glaseo_num = float(glaseo_factor)
            if glaseo_num > 1:
                glaseo_value = glaseo_num / 100  # 10 → 0.10
            else:
                glaseo_value = glaseo_num  # 0.10 → 0.10
        except:
            glaseo_value = 0.70  # Default
    else:
        glaseo_value = 0.70  # Default
    
    # Crear consulta estructurada con parámetros personalizados
    query = {
        'product': product,
        'size': size,
        'quantity': quantity,
        'destination': destination,
        'unit': unit,
        'glaseo_factor': glaseo_value,
        'flete_value': flete_value,
        'usar_libras': usar_libras,
        'cliente_nombre': cliente_nombre,
        'custom_calculation': True  # Indica que usa cálculos personalizados
    }
    
    return query
    
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
    Formatea la respuesta con la información de precios calculados dinámicamente
    """
    try:
        # Información básica
        product = price_info.get('producto', price_info.get('product', 'N/A'))
        size = price_info.get('talla', price_info.get('size', 'N/A'))
        is_dynamic = price_info.get('calculo_dinamico', False)
        usar_libras = price_info.get('usar_libras', False)
        valores_usuario = price_info.get('valores_usuario', {})
        
        response = f"🦐 **BGR EXPORT - Cotización Camarón** 🦐\n\n"
        response += f"📏 **Talla:** {size}\n"
        response += f"🏷️ **Producto:** {product}\n"
        
        if is_dynamic:
            response += "⚙️ **Cálculo Dinámico (Valores del Usuario)**\n"
        
        response += "\n"
        
        # Verificar si el producto no tiene precio establecido
        has_calculated_prices = (
            'precio_fob_kg' in price_info and 
            price_info.get('precio_fob_kg', 0) > 0
        )
        
        if not has_calculated_prices and (price_info.get('sin_precio', False) or price_info.get('precio_kg', 0) == 0):
            response += "⚠️ **SIN PRECIO ESTABLECIDO**\n\n"
            response += "📞 Para obtener cotización de este producto, contacta directamente con BGR Export.\n\n"
            response += "🏢 **Información de contacto:**\n"
            response += "📧 Email: ventas@bgrexport.com\n"
            response += "📱 WhatsApp: +593 98-805-7425\n"
            response += "🌐 Web: www.bgrexport.com"
            return response
        
        response += "💰 **PRECIOS CALCULADOS:**\n\n"
        
        # Mostrar origen del precio base
        precio_base_especificado = valores_usuario.get('precio_base_especificado')
        if precio_base_especificado:
            response += f"📊 **Precio Base (Usuario):** ${precio_base_especificado:.2f}/kg\n\n"
        elif 'precio_kg' in price_info:
            response += f"📊 **Precio Base (Excel):** ${price_info['precio_kg']:.2f}/kg\n\n"
        
        # Determinar si es Houston (solo kilos) o otras ciudades USA (libras)
        destination = price_info.get('destination', '')
        is_houston = destination.lower() == 'houston'
        
        # Precios FOB
        if 'precio_fob_kg' in price_info:
            response += "🚢 **Precio FOB (Base - Costo Fijo):**\n"
            if is_houston:
                response += f"   • ${price_info['precio_fob_kg']:.2f}/kg\n\n"
            else:
                response += f"   • ${price_info['precio_fob_kg']:.2f}/kg - ${price_info['precio_fob_lb']:.2f}/lb\n\n"
        
        # Precios con glaseo
        if 'precio_glaseo_kg' in price_info:
            glaseo_factor = price_info.get('factor_glaseo', 0)
            glaseo_especificado = valores_usuario.get('glaseo_especificado')
            
            if glaseo_especificado:
                glaseo_percent = glaseo_especificado * 100
                response += f"❄️ **Precio con Glaseo ({glaseo_percent:.0f}% - Usuario):**\n"
            else:
                glaseo_percent = glaseo_factor * 100
                response += f"❄️ **Precio con Glaseo ({glaseo_percent:.0f}%):**\n"
            
            if is_houston:
                response += f"   • ${price_info['precio_glaseo_kg']:.2f}/kg\n\n"
            else:
                response += f"   • ${price_info['precio_glaseo_kg']:.2f}/kg - ${price_info['precio_glaseo_lb']:.2f}/lb\n\n"
        
        # Precio final
        if 'precio_final_kg' in price_info:
            flete_value = price_info.get('flete', 0)
            flete_especificado = valores_usuario.get('flete_especificado')
            
            if flete_especificado:
                response += f"✈️ **Precio Final (Glaseo + Flete Usuario ${flete_value:.2f}):**\n"
            elif is_houston:
                response += f"✈️ **Precio Final (Glaseo + Flete Houston ${flete_value:.2f}):**\n"
            elif usar_libras:
                response += f"✈️ **Precio Final (Glaseo + Flete USA ${flete_value:.2f}):**\n"
            else:
                response += f"✈️ **Precio Final (Glaseo + Flete ${flete_value:.2f}):**\n"
            
            if is_houston:
                response += f"   • ${price_info['precio_final_kg']:.2f}/kg\n\n"
            else:
                response += f"   • ${price_info['precio_final_kg']:.2f}/kg - ${price_info['precio_final_lb']:.2f}/lb\n\n"
        
        # Información adicional
        if price_info.get('destination'):
            response += f"🌍 **Destino:** {price_info['destination']}\n"
        
        if price_info.get('quantity'):
            response += f"📦 **Cantidad:** {price_info['quantity']}\n"
        
        if price_info.get('cliente_nombre'):
            response += f"👤 **Cliente:** {price_info['cliente_nombre']}\n"
        
        # Factores utilizados
        response += "\n📋 **Factores aplicados:**\n"
        response += f"• Costo fijo: ${price_info.get('costo_fijo', 0.29):.2f}\n"
        
        glaseo_factor = price_info.get('factor_glaseo', 0)
        glaseo_especificado = valores_usuario.get('glaseo_especificado')
        if glaseo_especificado:
            response += f"• Factor glaseo: {glaseo_factor:.1%} (especificado por usuario)\n"
        else:
            response += f"• Factor glaseo: {glaseo_factor:.1%}\n"
        
        flete_value = price_info.get('flete', 0)
        flete_especificado = valores_usuario.get('flete_especificado')
        destination = price_info.get('destination', '')
        
        if flete_especificado:
            response += f"• Flete: ${flete_value:.2f} (especificado por usuario)\n"
        elif destination.lower() == 'houston':
            response += f"• Flete: ${flete_value:.2f} (Houston - desde Sheets)\n"
        elif usar_libras:
            response += f"• Flete: ${flete_value:.2f} (USA - desde Sheets)\n"
        else:
            response += f"• Flete: ${flete_value:.2f} (desde Sheets)\n"
        
        response += "\n📋 _Precios FOB sujetos a confirmación final_\n"
        response += "📞 **Contacto:** BGR Export\n"
        response += "💡 _Escribe 'confirmar' para generar PDF_"
        
        return response
        
    except Exception as e:
        logger.error(f"Error formateando respuesta de precio: {str(e)}")
        return "❌ Error generando cotización. Intenta nuevamente."

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