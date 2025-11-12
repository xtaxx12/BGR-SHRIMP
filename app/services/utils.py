import logging
import re

logger = logging.getLogger(__name__)

def parse_multiple_products(message: str) -> list[dict] | None:
    """
    Detecta y extrae múltiples productos del mensaje
    Retorna una lista de diccionarios con producto y talla
    Soporta términos en español, inglés y portugués
    """
    if not message:
        return None

    message_upper = message.upper()
    products_found = []

    # Patrones para productos (expandidos con términos en español/portugués)
    product_patterns = {
        'HOSO': r'\b(?:HOSO|INTEIRO|ENTERO|WHOLE)\b',
        'HLSO': r'\bHLSO\b',
        'P&D IQF': r'\b(?:P&D|PYD|P\s*&\s*D)\s*(?:IQF|TAIL\s*OFF)?\b',
        'P&D BLOQUE': r'\b(?:P&D|PYD)\s*(?:BLOQUE|BLOCK)\b',
        'EZPEEL': r'\b(?:EZ\s*PEEL|EZPEEL)\b',
        'EZ PEEL': r'\b(?:EZ\s*PEEL|EZPEEL)\b',
        'COOKED': r'\b(?:COOKED|COCIDO|COCEDERO|COZIDO)\b',
        'PRE-COCIDO': r'\b(?:PRE-COCIDO|PRECOCIDO|PRE\s*COOKED)\b',
        'COCIDO SIN TRATAR': r'\b(?:COCIDO\s*SIN\s*TRATAR|UNTREATED\s*COOKED)\b',
    }

    # Detectar si menciona "Colas" o "Tails" (productos pelados)
    has_colas = bool(re.search(r'\b(?:COLAS|TAILS|COLA|TAIL)\b', message_upper))
    
    # Detectar si menciona términos de producto cocido
    has_cocido = bool(re.search(r'\b(?:COCIDO|COCEDERO|COOKED|COZIDO)\b', message_upper))

    # Buscar todas las tallas en el mensaje (formato XX/XX)
    size_matches = re.finditer(r'(\d+)[/](\d+)', message)
    
    for match in size_matches:
        size = f"{match.group(1)}/{match.group(2)}"
        
        # Obtener contexto alrededor de la talla (50 caracteres antes y después)
        start = max(0, match.start() - 50)
        end = min(len(message), match.end() + 50)
        context = message[start:end].upper()
        
        # Buscar producto en el contexto
        product_found = None
        for product_name, pattern in product_patterns.items():
            if re.search(pattern, context):
                product_found = product_name
                break

        # Si no se encontró producto específico, intentar inferir
        if not product_found:
            # Si menciona "Colas" y producto cocido, probablemente COOKED
            if has_colas and has_cocido:
                product_found = 'COOKED'
            # Si menciona "Inteiro" o "Entero", probablemente HOSO
            elif 'INTEIRO' in context or 'ENTERO' in context:
                product_found = 'HOSO'
            # Si tiene "BLOCK" o "BLOQUE", es P&D BLOQUE
            elif 'BLOCK' in context or 'BLOQUE' in context:
                product_found = 'P&D BLOQUE'
            # Si tiene "IQF", es P&D IQF
            elif 'IQF' in context:
                product_found = 'P&D IQF'
            # Si menciona cocido sin especificar, usar COOKED
            elif has_cocido:
                product_found = 'COOKED'

        if size:
            products_found.append({
                'product': product_found,  # Puede ser None si no se detectó
                'size': size,
                'context': context.strip(),
                'has_colas': has_colas,
                'has_cocido': has_cocido
            })

    return products_found if products_found else None

def parse_user_message(message: str) -> dict | None:
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

def parse_ai_analysis_to_query(ai_analysis: dict) -> dict | None:
    """
    Convierte el análisis de IA en una consulta de precio válida con parámetros personalizados
    IMPORTANTE: NO usa valores por defecto para glaseo - debe ser especificado por el usuario
    """
    if not ai_analysis or ai_analysis.get('intent') not in ['pricing', 'proforma']:
        return None

    # Extraer información del análisis de IA
    product = ai_analysis.get('product')
    size = ai_analysis.get('size')
    quantity = ai_analysis.get('quantity')
    destination = ai_analysis.get('destination')
    glaseo_factor = ai_analysis.get('glaseo_factor')
    glaseo_percentage = ai_analysis.get('glaseo_percentage')  # Porcentaje original
    flete_custom = ai_analysis.get('flete_custom')
    is_ddp = ai_analysis.get('is_ddp', False)  # Flag para precio DDP (ya incluye flete)
    usar_libras = ai_analysis.get('usar_libras', False)
    cliente_nombre = ai_analysis.get('cliente_nombre')

    # Validar que tengamos producto y talla
    if not size:
        return None

    # Lógica inteligente: Si no hay producto pero la talla es exclusiva de HOSO, asumir HOSO
    if not product and size:
        # Tallas que solo existen en HOSO según la tabla de precios
        hoso_exclusive_sizes = ['20/30', '30/40', '40/50', '50/60', '60/70', '70/80']
        if size in hoso_exclusive_sizes:
            product = 'HOSO'

    # Si aún no hay producto después de la lógica inteligente, pedir al usuario que especifique
    if not product:
        return None  # Esto hará que el bot pida al usuario que especifique el producto

    # Determinar unidad base según destino
    unit = 'lb' if usar_libras else 'kg'

    # Procesar flete personalizado del usuario
    flete_value = None
    flete_solicitado = False

    # Si es DDP, SIEMPRE necesitamos el flete para desglosar el precio
    if is_ddp:
        if flete_custom:
            # Usuario especificó el flete en el mensaje DDP
            try:
                flete_value = float(flete_custom)
                flete_solicitado = True
                logger.info(f"📦 Precio DDP con flete ${flete_value:.2f} especificado")
            except:
                # Flete inválido, solicitar al usuario
                flete_solicitado = True
                flete_value = None
                logger.info("📦 Precio DDP detectado - se solicitará valor de flete")
        else:
            # DDP sin flete especificado - DEBE pedirlo
            flete_solicitado = True
            flete_value = None
            logger.info("📦 Precio DDP detectado SIN flete - se solicitará valor de flete al usuario")
    # Marcar flete solicitado si:
    # 1. Hay valor personalizado de flete, O
    # 2. Hay destino (porque el análisis básico solo detecta destino si menciona flete)
    elif flete_custom:
        try:
            flete_value = float(flete_custom)
            flete_solicitado = True
        except:
            pass
    elif destination:
        # Si hay destino, significa que el análisis básico detectó palabras de flete
        flete_solicitado = True

    # Procesar factor de glaseo - CRÍTICO: NO USAR VALOR POR DEFECTO
    # IMPORTANTE: Si glaseo_percentage es 0, significa "sin glaseo" (especificado explícitamente)
    glaseo_value = None
    if glaseo_percentage == 0:
        # Usuario especificó 0% glaseo → Sin glaseo (CFR simple)
        glaseo_value = None
        logger.info("📊 Glaseo 0% detectado en análisis → Sin glaseo (CFR simple)")
    elif glaseo_factor:
        try:
            # Si viene como "10" convertir a 0.10
            glaseo_num = float(glaseo_factor)
            if glaseo_num > 1:
                glaseo_value = glaseo_num / 100  # 10 → 0.10
            else:
                glaseo_value = glaseo_num  # 0.10 → 0.10
        except:
            glaseo_value = None  # NUNCA usar valor por defecto
    else:
        glaseo_value = None  # NUNCA usar valor por defecto - pedir al usuario

    # Crear consulta estructurada con parámetros personalizados
    query = {
        'product': product,
        'size': size,
        'quantity': quantity,
        'destination': destination,
        'unit': unit,
        'glaseo_factor': glaseo_value,
        'glaseo_percentage': glaseo_percentage,  # Porcentaje original solicitado
        'flete_custom': flete_value,  # Solo si se especificó
        'flete_solicitado': flete_solicitado,  # Flag para saber si pidió flete
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

def format_price_response(price_info: dict) -> str:
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

        response = "🦐 **BGR EXPORT - Cotización Camarón** 🦐\n\n"
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
            response += "📧 Email: amerino@bgrexport.com\n"
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
        is_houston = destination and destination.lower() == 'houston'

        # Precios FOB
        if 'precio_fob_kg' in price_info:
            response += "🚢 **Precio FOB (Base - Costo Fijo):**\n"
            if is_houston:
                response += f"   • ${price_info['precio_fob_kg']:.2f}/kg\n\n"
            else:
                response += f"   • ${price_info['precio_fob_kg']:.2f}/kg - ${price_info['precio_fob_lb']:.2f}/lb\n\n"

        # Determinar qué precio mostrar según si incluye flete
        incluye_flete = price_info.get('incluye_flete', False)

        if incluye_flete:
            # Mostrar precio CFR (con flete)
            if 'precio_final_kg' in price_info:
                flete_value = price_info.get('flete', 0)
                flete_especificado = valores_usuario.get('flete_especificado')
                glaseo_especificado_flag = price_info.get('glaseo_especificado', False)

                # Determinar el tipo de cálculo CFR
                if glaseo_especificado_flag:
                    # CFR con glaseo especificado
                    if flete_especificado:
                        response += f"✈️ **Precio CFR (FOB + Glaseo + Flete ${flete_value:.2f}):**\n"
                    elif is_houston:
                        response += f"✈️ **Precio CFR (FOB + Glaseo + Flete Houston ${flete_value:.2f}):**\n"
                    elif usar_libras:
                        response += f"✈️ **Precio CFR (FOB + Glaseo + Flete USA ${flete_value:.2f}):**\n"
                    else:
                        response += f"✈️ **Precio CFR (FOB + Glaseo + Flete ${flete_value:.2f}):**\n"
                else:
                    # CFR simple (sin glaseo)
                    if flete_especificado:
                        response += f"✈️ **Precio CFR (FOB + Flete ${flete_value:.2f}):**\n"
                    else:
                        response += f"✈️ **Precio CFR (FOB + Flete ${flete_value:.2f}):**\n"

                if is_houston:
                    response += f"   • ${price_info['precio_final_kg']:.2f}/kg\n\n"
                else:
                    response += f"   • ${price_info['precio_final_kg']:.2f}/kg - ${price_info['precio_final_lb']:.2f}/lb\n\n"
        else:
            # Mostrar solo precio con glaseo (sin flete)
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

        # Solo mostrar flete si se incluye en el cálculo
        if incluye_flete:
            flete_value = price_info.get('flete', 0)
            flete_especificado = valores_usuario.get('flete_especificado')
            destination = price_info.get('destination', '')

            if flete_especificado:
                response += f"• Flete: ${flete_value:.2f} (especificado por usuario)\n"
            elif destination and destination.lower() == 'houston':
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

def extract_size_from_text(text: str) -> str | None:
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
