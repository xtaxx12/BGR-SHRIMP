from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from twilio.twiml.messaging_response import MessagingResponse
from app.services.pricing import PricingService
from app.services.utils import parse_user_message, parse_ai_analysis_to_query, format_price_response
from app.services.interactive import InteractiveMessageService
from app.services.session import session_manager
from app.services.pdf_generator import PDFGenerator
from app.services.whatsapp_sender import WhatsAppSender
from app.services.openai_service import OpenAIService
from app.services.audio_handler import AudioHandler
from app.security import (
    validate_twilio_webhook, rate_limit, sanitize_input, 
    validate_phone_number, security, verify_admin_token,
    SecureTempFile, add_security_headers
)
from app.config import settings
import logging
import os
import time
import re
from typing import Set

logger = logging.getLogger(__name__)

webhook_router = APIRouter()

# Servicios se inicializarán de manera lazy
pricing_service = None
interactive_service = None
pdf_generator = None
openai_service = None
whatsapp_sender = None

# Cache para deduplicación de mensajes
processed_messages: Set[str] = set()
message_timestamps = {}

def cleanup_old_messages():
    """
    Limpia mensajes procesados antiguos (más de 5 minutos)
    """
    current_time = time.time()
    expired_messages = []
    
    for message_sid, timestamp in message_timestamps.items():
        if current_time - timestamp > 300:  # 5 minutos
            expired_messages.append(message_sid)
    
    for message_sid in expired_messages:
        processed_messages.discard(message_sid)
        message_timestamps.pop(message_sid, None)

def is_duplicate_message(message_sid: str) -> bool:
    """
    Verifica si un mensaje ya fue procesado
    """
    cleanup_old_messages()
    
    if message_sid in processed_messages:
        logger.warning(f"🔄 Mensaje duplicado detectado: {message_sid}")
        return True
    
    # Marcar como procesado
    processed_messages.add(message_sid)
    message_timestamps[message_sid] = time.time()
    return False

def get_services():
    """
    Inicializa los servicios de manera lazy
    """
    global pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service
    
    if pricing_service is None:
        pricing_service = PricingService()
        # Pasar el servicio de Excel al servicio interactivo para compartir datos
        interactive_service = InteractiveMessageService(pricing_service.excel_service)
        pdf_generator = PDFGenerator()
        whatsapp_sender = WhatsAppSender()
        openai_service = OpenAIService()
        logger.debug("✅ Servicios inicializados")
    
    return pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service

@webhook_router.post("/whatsapp")
@rate_limit(lambda req, **kwargs: kwargs.get('From', 'unknown'))
async def whatsapp_webhook(request: Request,
    Body: str = Form(""),
    From: str = Form(...),
    To: str = Form(...),
    MessageSid: str = Form(...),
    NumMedia: int = Form(0),
    MediaUrl0: str = Form(""),
    MediaContentType0: str = Form("")
):
    """
    Endpoint para recibir mensajes de WhatsApp desde Twilio
    """
    try:
        # Validar número de teléfono
        if not validate_phone_number(From):
            logger.warning(f"Invalid phone number format: {From}")
            raise HTTPException(status_code=400, detail="Invalid phone format")
        
        # Sanitizar entrada
        Body = sanitize_input(Body, max_length=settings.MAX_MESSAGE_LENGTH)
        
        # Verificar si es un mensaje duplicado
        if is_duplicate_message(MessageSid):
            # Retornar respuesta vacía para mensajes duplicados
            response = MessagingResponse()
            return PlainTextResponse(str(response), media_type="application/xml")
        
        logger.debug(f"Mensaje recibido de {From}: {Body}")
        logger.debug(f"Multimedia: NumMedia={NumMedia}, MediaUrl={MediaUrl0}, ContentType={MediaContentType0}")
        
        # Inicializar servicios si no están inicializados
        pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service = get_services()
        
        # Crear respuesta de Twilio
        response = MessagingResponse()
        
        # Procesar audio si está presente
        if NumMedia > 0 and MediaUrl0 and "audio" in MediaContentType0.lower():
            logger.info(f"🎤 Procesando mensaje de audio...")
            audio_handler = AudioHandler()
            
            # Descargar audio de forma segura
            with SecureTempFile(suffix=".ogg") as temp_path:
                audio_path = audio_handler.download_audio_from_twilio(MediaUrl0, temp_path)
            
            if audio_path:
                # Transcribir audio
                transcription = openai_service.transcribe_audio(audio_path)
                
                # Limpiar archivo temporal
                audio_handler.cleanup_temp_file(audio_path)
                
                if transcription:
                    # Usar la transcripción como el mensaje de texto
                    Body = transcription
                    logger.info(f"🎤 Transcripción procesada: '{Body}'")
                    
                    # Confirmar al usuario que se procesó el audio
                    response.message(f"🎤 Audio recibido: \"{transcription}\"")
                else:
                    response.message("❌ No pude procesar el audio. Por favor, envía un mensaje de texto.")
                    return PlainTextResponse(str(response), media_type="application/xml")
            else:
                response.message("❌ Error descargando el audio. Intenta nuevamente.")
                return PlainTextResponse(str(response), media_type="application/xml")
        
        # Si no hay mensaje de texto (ni transcripción), salir
        if not Body or Body.strip() == "":
            response.message("👋 ¡Hola! Envíame un mensaje de texto o audio para ayudarte con precios de camarón.")
            return PlainTextResponse(str(response), media_type="application/xml")
        
        # Obtener sesión del usuario
        user_id = From.replace("whatsapp:", "")
        session = session_manager.get_session(user_id)
        
        # VERIFICAR PRIMERO SI EL USUARIO ESTÁ EN UN ESTADO QUE REQUIERE RESPUESTA DIRECTA
        # Esto evita que el análisis de intención interfiera con respuestas esperadas
        if session['state'] == 'waiting_for_glaseo':
            # Usuario está respondiendo con el porcentaje de glaseo
            ai_query = session['data'].get('ai_query')
            
            if ai_query:
                # Intentar extraer el porcentaje de glaseo del mensaje
                glaseo_percentage = None
                glaseo_factor = None

                # Patrones para detectar porcentaje de glaseo
                glaseo_patterns = [
                    r'(\d+)\s*%',  # "20%"
                    r'(\d+)\s*porciento',  # "20 porciento"
                    r'(\d+)\s*por\s*ciento',  # "20 por ciento"
                    r'^(\d+)$',  # Solo el número "20"
                ]
                
                message_lower = Body.lower().strip()
                for pattern in glaseo_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        glaseo_percentage = int(match.group(1))
                        break
                
                # Convertir porcentaje a factor
                if glaseo_percentage == 10:
                    glaseo_factor = 0.90
                elif glaseo_percentage == 20:
                    glaseo_factor = 0.80
                elif glaseo_percentage == 30:
                    glaseo_factor = 0.70
                elif glaseo_percentage:
                    glaseo_factor = glaseo_percentage / 100
                
                if glaseo_factor:
                    # Actualizar ai_query con el glaseo
                    ai_query['glaseo_factor'] = glaseo_factor
                    ai_query['glaseo_percentage'] = glaseo_percentage
                    
                    # Intentar calcular el precio con el glaseo
                    price_info = pricing_service.get_shrimp_price(ai_query)
                    
                    if price_info:
                        logger.debug(f"✅ Datos de proforma validados con glaseo {glaseo_percentage}%")
                        
                        # Guardar datos de la proforma y preguntar por idioma
                        session_manager.set_session_state(user_id, 'waiting_for_proforma_language', {
                            'price_info': price_info,
                            'ai_query': ai_query
                        })
                        
                        # Mostrar resumen y opciones de idioma
                        product_name = price_info.get('producto', 'Camarón')
                        size = price_info.get('talla', '')
                        client_name = price_info.get('cliente_nombre', '')
                        
                        summary = f"📋 **Proforma lista para generar:**\n"
                        summary += f"🦐 Producto: {product_name} {size}\n"
                        summary += f"❄️ Glaseo: {glaseo_percentage}%\n"
                        if client_name:
                            summary += f"👤 Cliente: {client_name.title()}\n"
                        
                        language_message = f"""{summary}
🌐 **Selecciona el idioma para la proforma:**

1️⃣ Español 🇪🇸
2️⃣ English 🇺🇸

Responde con el número o escribe:
• "español" o "spanish"  
• "inglés" o "english" """
                        
                        response.message(language_message)
                        return PlainTextResponse(str(response), media_type="application/xml")
                    else:
                        logger.error(f"❌ Error calculando precio con glaseo {glaseo_percentage}%")
                        response.message("❌ Error procesando la solicitud. Intenta nuevamente.")
                        session_manager.clear_session(user_id)
                        return PlainTextResponse(str(response), media_type="application/xml")
                else:
                    # Glaseo no válido
                    product = ai_query.get('product', 'producto')
                    size = ai_query.get('size', 'talla')
                    
                    response.message(f"🤔 Porcentaje no válido. Por favor responde con:\n\n• **10** para 10% glaseo\n• **20** para 20% glaseo\n• **30** para 30% glaseo\n\nO escribe 'menu' para volver al inicio")
                    return PlainTextResponse(str(response), media_type="application/xml")
            else:
                response.message("❌ Error: No se encontraron datos de la solicitud. Por favor intenta nuevamente.")
                session_manager.clear_session(user_id)
                return PlainTextResponse(str(response), media_type="application/xml")
        
        # Análisis rápido de intención
        ai_analysis = openai_service._basic_intent_analysis(Body)
        logger.info(f"🔍 Análisis básico para {user_id}: {ai_analysis}")
        logger.info(f"🔍 Intent: {ai_analysis.get('intent')}, Confidence: {ai_analysis.get('confidence')}, Product: {ai_analysis.get('product')}, Size: {ai_analysis.get('size')}")
        
        # Solo usar OpenAI para casos complejos (no para saludos simples)
        if (ai_analysis.get('confidence', 0) < 0.7 and 
            ai_analysis.get('intent') not in ['greeting', 'menu_request'] and 
            openai_service.is_available()):
            openai_analysis = openai_service.analyze_user_intent(Body, session)
            logger.debug(f"🤖 Análisis OpenAI complementario para {user_id}: {openai_analysis}")
            
            # Combinar resultados: usar OpenAI si es más confiable, pero preservar datos específicos del fallback
            if openai_analysis.get('confidence', 0) > ai_analysis.get('confidence', 0):
                # Preservar datos importantes del análisis básico si OpenAI no los tiene
                basic_destination = ai_analysis.get('destination')
                basic_glaseo_percentage = ai_analysis.get('glaseo_percentage')
                
                ai_analysis = openai_analysis
                
                # Restaurar datos del análisis básico si OpenAI no los detectó
                if not ai_analysis.get('destination') and basic_destination:
                    ai_analysis['destination'] = basic_destination
                if not ai_analysis.get('glaseo_percentage') and basic_glaseo_percentage:
                    ai_analysis['glaseo_percentage'] = basic_glaseo_percentage
        
        # DETECTAR MÚLTIPLES PRODUCTOS PRIMERO
        multiple_products = openai_service.detect_multiple_products(Body)
        
        if multiple_products and len(multiple_products) > 1:
            logger.info(f"📋 Detectados {len(multiple_products)} productos en el mensaje")
            
            # Verificar si el usuario ya especificó el glaseo en el mensaje
            glaseo_factor = ai_analysis.get('glaseo_factor') if ai_analysis else None
            glaseo_percentage = ai_analysis.get('glaseo_percentage') if ai_analysis else None
            
            logger.info(f"🔍 Glaseo detectado en análisis: factor={glaseo_factor}, percentage={glaseo_percentage}")
            logger.info(f"🔍 Mensaje completo: {Body}")
            
            # Si no se detectó glaseo en el análisis, o si el glaseo detectado no es válido (10, 20, 30), intentar detectarlo manualmente
            if not glaseo_factor or not glaseo_percentage or glaseo_percentage not in [10, 20, 30]:
                message_lower = Body.lower()
                glaseo_patterns = [
                    r'al\s*(\d+)\s*%',
                    r'(\d+)\s*%\s*glaseo',
                    r'glaseo\s*(\d+)\s*%',
                    r'con\s*(\d+)\s*glaseo',
                    r'(\d+)\s*(?:de\s*)?glaseo',
                ]
                
                for pattern in glaseo_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        glaseo_percentage = int(match.group(1))
                        if glaseo_percentage == 10:
                            glaseo_factor = 0.90
                        elif glaseo_percentage == 20:
                            glaseo_factor = 0.80
                        elif glaseo_percentage == 30:
                            glaseo_factor = 0.70
                        else:
                            glaseo_factor = glaseo_percentage / 100
                        logger.info(f"✅ Glaseo detectado manualmente: {glaseo_percentage}% (factor {glaseo_factor})")
                        break
            
            if glaseo_factor and glaseo_percentage:
                # El usuario ya especificó el glaseo, procesar directamente
                logger.info(f"✅ Glaseo detectado en mensaje: {glaseo_percentage}%")
                
                # Calcular precios para todos los productos
                products_info = []
                failed_products = []
                
                for product_data in multiple_products:
                    try:
                        query = {
                            'product': product_data['product'],
                            'size': product_data['size'],
                            'glaseo_factor': glaseo_factor,
                            'glaseo_percentage': glaseo_percentage,
                            'flete_custom': 0.15,
                            'flete_solicitado': True,
                            'custom_calculation': True
                        }
                        
                        price_info = pricing_service.get_shrimp_price(query)
                        
                        if price_info:
                            products_info.append(price_info)
                        else:
                            failed_products.append(f"{product_data['product']} {product_data['size']}")
                    except Exception as e:
                        logger.error(f"❌ Error calculando precio para {product_data['product']} {product_data['size']}: {str(e)}")
                        failed_products.append(f"{product_data['product']} {product_data['size']}")
                
                if products_info:
                    # Guardar para selección de idioma
                    session_manager.set_session_state(user_id, 'waiting_for_multi_language', {
                        'products_info': products_info,
                        'glaseo_percentage': glaseo_percentage,
                        'failed_products': failed_products
                    })
                    # Guardar como última cotización consolidada para permitir modificación de flete
                    session_manager.set_last_quote(user_id, {
                        'consolidated': True,
                        'products_info': products_info,
                        'glaseo_percentage': glaseo_percentage,
                        'failed_products': failed_products
                    })
                    
                    # Mostrar resumen y pedir idioma
                    success_count = len(products_info)
                    total_count = len(multiple_products)
                    
                    summary = f"✅ **Precios calculados para {success_count}/{total_count} productos**\n"
                    summary += f"❄️ Glaseo: {glaseo_percentage}%\n\n"
                    
                    if failed_products:
                        summary += f"⚠️ No se encontraron precios para:\n"
                        for fp in failed_products:
                            summary += f"   • {fp}\n"
                        summary += "\n"
                    
                    summary += f"🌐 **Selecciona el idioma para la cotización consolidada:**\n\n"
                    summary += f"1️⃣ Español 🇪🇸\n"
                    summary += f"2️⃣ English 🇺🇸\n\n"
                    summary += f"Responde con el número o escribe:\n"
                    summary += f"• \"español\" o \"spanish\"\n"
                    summary += f"• \"inglés\" o \"english\""
                    
                    response.message(summary)
                else:
                    response.message("❌ No se pudieron calcular precios para ningún producto. Verifica los productos y tallas.")
                    session_manager.clear_session(user_id)
                
                return PlainTextResponse(str(response), media_type="application/xml")
            else:
                # No especificó glaseo, pedirlo
                session_manager.set_session_state(user_id, 'waiting_for_multi_glaseo', {
                    'products': multiple_products,
                    'message': Body
                })
                
                # Mostrar lista de productos detectados
                products_list = "\n".join([f"   {i+1}. {p['product']} {p['size']}" 
                                          for i, p in enumerate(multiple_products)])
                
                # Detectar destino si está en el mensaje
                destination = ai_analysis.get('destination') if ai_analysis else None
                destination_text = f"\n🌍 Destino: {destination}" if destination else ""
                
                multi_message = f"""📋 **Detecté {len(multiple_products)} productos para cotizar:**

{products_list}{destination_text}

❄️ **¿Qué glaseo necesitas para todos los productos?**
• **10%** glaseo (factor 0.90)
• **20%** glaseo (factor 0.80)
• **30%** glaseo (factor 0.70)

💡 Responde con el número: 10, 20 o 30"""
                
                response.message(multi_message)
                return PlainTextResponse(str(response), media_type="application/xml")
        
        # PROCESAMIENTO PRIORITARIO DE PROFORMA
        # Si el análisis detecta una solicitud de proforma, preguntar por idioma primero
        logger.info(f"🔍 Verificando condición proforma: intent={ai_analysis.get('intent')}, confidence={ai_analysis.get('confidence')}")
        if ai_analysis and ai_analysis.get('intent') == 'proforma' and ai_analysis.get('confidence', 0) > 0.7:
            logger.info(f"🎯 Solicitud de proforma detectada para {user_id}")
            ai_query = parse_ai_analysis_to_query(ai_analysis)
            logger.info(f"🤖 Consulta generada por IA: {ai_query}")
            
            # Verificar si falta información crítica
            if not ai_query:
                # Verificar qué información específica falta
                product = ai_analysis.get('product')
                size = ai_analysis.get('size')
                
                if not product and size:
                    # Tiene talla pero no producto - pedir producto específico
                    missing_product_message = f"""🦐 **Detecté la talla {size}, pero necesito saber el tipo de camarón:**

📋 **Productos disponibles:**
• **HLSO** - Sin cabeza, con cáscara (más popular)
• **HOSO** - Con cabeza y cáscara (entero)
• **P&D IQF** - Pelado y desvenado individual
• **P&D BLOQUE** - Pelado y desvenado en bloque
• **PuD-EUROPA** - Calidad premium para Europa
• **EZ PEEL** - Fácil pelado

💡 **Ejemplo:** "Proforma HLSO {size}" o "Cotización P&D IQF {size}"

¿Cuál necesitas? 🤔"""
                    
                    response.message(missing_product_message)
                    return PlainTextResponse(str(response), media_type="application/xml")
                
                elif not size and product:
                    # Tiene producto pero no talla - pedir talla
                    missing_size_message = f"""📏 **Detecté {product}, pero necesito la talla:**

📋 **Tallas disponibles:**
U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40, 40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90

💡 **Ejemplo:** "Proforma {product} 16/20" o "Cotización {product} 21/25"

¿Qué talla necesitas? 🤔"""
                    
                    response.message(missing_size_message)
                    return PlainTextResponse(str(response), media_type="application/xml")
                
                else:
                    # Falta tanto producto como talla
                    missing_both_message = """🦐 **Para generar tu proforma necesito:**

1️⃣ **Tipo de camarón:**
• HLSO, HOSO, P&D IQF, P&D BLOQUE, etc.

2️⃣ **Talla:**
• 16/20, 21/25, 26/30, etc.

💡 **Ejemplo completo:** 
"Proforma HLSO 16/20" o "Cotización P&D IQF 21/25"

¿Qué producto y talla necesitas? 🤔"""
                    
                    response.message(missing_both_message)
                    return PlainTextResponse(str(response), media_type="application/xml")
            
            if ai_query:
                # Verificar que se puede generar la cotización
                price_info = pricing_service.get_shrimp_price(ai_query)
                
                if price_info:
                    logger.debug(f"✅ Datos de proforma validados para: {ai_query}")
                    
                    # Guardar datos de la proforma y preguntar por idioma
                    session_manager.set_session_state(user_id, 'waiting_for_proforma_language', {
                        'price_info': price_info,
                        'ai_query': ai_query
                    })
                    
                    # Mostrar resumen y opciones de idioma
                    product_name = price_info.get('producto', 'Camarón')
                    size = price_info.get('talla', '')
                    client_name = price_info.get('cliente_nombre', '')
                    
                    summary = f"📋 **Proforma lista para generar:**\n"
                    summary += f"🦐 Producto: {product_name} {size}\n"
                    if client_name:
                        summary += f"👤 Cliente: {client_name.title()}\n"
                    
                    language_message = f"""{summary}
🌐 **Selecciona el idioma para la proforma:**

1️⃣ Español 🇪🇸
2️⃣ English 🇺🇸

Responde con el número o escribe:
• "español" o "spanish"  
• "inglés" o "english" """
                    
                    response.message(language_message)
                    return PlainTextResponse(str(response), media_type="application/xml")
                else:
                    # Verificar si falta el glaseo específicamente
                    glaseo_factor = ai_query.get('glaseo_factor') if ai_query else None
                    
                    if glaseo_factor is None:
                        # Falta el glaseo - pedir al usuario que lo especifique
                        product = ai_query.get('product', 'producto') if ai_query else 'producto'
                        size = ai_query.get('size', 'talla') if ai_query else 'talla'
                        
                        glaseo_message = f"""❄️ **Para calcular el precio CFR de {product} {size} necesito el glaseo:**

📋 **Opciones de glaseo disponibles:**
• **10%** glaseo (factor 0.90)
• **20%** glaseo (factor 0.80) 
• **30%** glaseo (factor 0.70)

💡 **Ejemplos:**
• "Proforma {product} {size} glaseo 10%"
• "Cotización {product} {size} con 20% glaseo"
• "{product} {size} glaseo 30%"

¿Qué porcentaje de glaseo necesitas? 🤔"""
                        
                        response.message(glaseo_message)
                        
                        # Guardar el estado para esperar la respuesta del glaseo
                        session_manager.set_session_state(user_id, 'waiting_for_glaseo', {
                            'ai_query': ai_query
                        })
                        
                        return PlainTextResponse(str(response), media_type="application/xml")
                    else:
                        logger.error(f"❌ Error validando datos de proforma: {ai_query}")
                        response.message("❌ Error procesando la solicitud. Intenta nuevamente.")
                        return PlainTextResponse(str(response), media_type="application/xml")
        
        # Comandos globales que funcionan desde cualquier estado
        message_lower = Body.lower().strip()
        
        # DETECTAR MODIFICACIÓN DE FLETE (debe ir antes de otros comandos)
        if ai_analysis and ai_analysis.get('intent') == 'modify_flete':
            # Usuario quiere modificar el flete de la última proforma
            last_quote = session_manager.get_last_quote(user_id)
            
            if last_quote:
                new_flete = ai_analysis.get('flete_custom')
                
                if new_flete is not None:
                    logger.info(f"🔄 Modificando flete de ${last_quote.get('flete', 0):.2f} a ${new_flete:.2f}")
                    
                    # Recalcular la proforma con el nuevo flete
                    # Obtener los datos originales de la consulta
                    product = last_quote.get('producto')
                    size = last_quote.get('talla')
                    glaseo_factor = last_quote.get('factor_glaseo')
                    glaseo_percentage = last_quote.get('glaseo_percentage')
                    cliente_nombre = last_quote.get('cliente_nombre')
                    destination = last_quote.get('destination')
                    usar_libras = last_quote.get('usar_libras', False)
                    
                    # Crear nueva consulta con el flete modificado
                    modified_query = {
                        'product': product,
                        'size': size,
                        'glaseo_factor': glaseo_factor,
                        'glaseo_percentage': glaseo_percentage,
                        'flete_custom': new_flete,
                        'flete_solicitado': True,
                        'cliente_nombre': cliente_nombre,
                        'destination': destination,
                        'usar_libras': usar_libras,
                        'custom_calculation': True
                    }
                    
                    # Recalcular precio con nuevo flete
                    # Si la última cotización es consolidada, recalcular todos los productos
                    if last_quote.get('consolidated') and last_quote.get('products_info'):
                        logger.info("🔄 Recalculando cotización consolidada con nuevo flete")
                        products = last_quote.get('products_info', [])
                        recalculated = []
                        failed = []
                        for p in products:
                            try:
                                query = {
                                    'product': p.get('producto') or p.get('product'),
                                    'size': p.get('talla') or p.get('size'),
                                    'glaseo_factor': p.get('factor_glaseo') or p.get('glaseo_factor'),
                                    'glaseo_percentage': p.get('glaseo_percentage'),
                                    'flete_custom': new_flete,
                                    'flete_solicitado': True,
                                    'custom_calculation': True
                                }
                                price = pricing_service.get_shrimp_price(query)
                                if price:
                                    recalculated.append(price)
                                else:
                                    failed.append(f"{p.get('product', p.get('producto'))} {p.get('size', p.get('talla'))}")
                            except Exception as e:
                                logger.error(f"❌ Error recalculando producto {p}: {e}")
                                failed.append(str(p))

                        if recalculated:
                            # Guardar la nueva cotización consolidada como last_quote
                            new_last = {
                                'consolidated': True,
                                'products_info': recalculated,
                                'glaseo_percentage': last_quote.get('glaseo_percentage'),
                                'failed_products': failed,
                                'flete': new_flete
                            }
                            session_manager.set_last_quote(user_id, new_last)

                            # Obtener idioma del usuario
                            user_language = session_manager.get_user_language(user_id)

                            # Generar PDF consolidado
                            logger.info(f"📄 Regenerando PDF consolidado con nuevo flete ${new_flete:.2f}")
                            pdf_path = pdf_generator.generate_consolidated_quote_pdf(
                                recalculated,
                                From,
                                user_language,
                                last_quote.get('glaseo_percentage')
                            )

                            if pdf_path:
                                response.message(f"✅ Cotización consolidada actualizada con nuevo flete ${new_flete:.2f} - Generando PDF...")
                                pdf_sent = whatsapp_sender.send_pdf_document(From, pdf_path, f"Cotización consolidada actualizada - flete ${new_flete:.2f}")
                                if not pdf_sent:
                                    filename = os.path.basename(pdf_path)
                                    base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                                    download_url = f"{base_url}/webhook/download-pdf/{filename}"
                                    pdf_message = response.message()
                                    pdf_message.body("📄 Cotización consolidada actualizada")
                                    pdf_message.media(download_url)

                                return PlainTextResponse(str(response), media_type="application/xml")
                            else:
                                response.message("❌ Error generando el PDF consolidado actualizado. Intenta nuevamente.")
                                return PlainTextResponse(str(response), media_type="application/xml")
                        else:
                            response.message("❌ No se pudieron recalcular precios para los productos con el nuevo flete.")
                            return PlainTextResponse(str(response), media_type="application/xml")

                    # Si no es consolidada, comportamiento por producto individual
                    new_price_info = pricing_service.get_shrimp_price(modified_query)

                    if new_price_info:
                        # Guardar la nueva cotización
                        session_manager.set_last_quote(user_id, new_price_info)
                        
                        # Obtener idioma del usuario
                        user_language = session_manager.get_user_language(user_id)
                        
                        # Generar nuevo PDF automáticamente
                        logger.info(f"📄 Regenerando PDF con nuevo flete ${new_flete:.2f}")
                        pdf_path = pdf_generator.generate_quote_pdf(new_price_info, From, user_language)
                        
                        if pdf_path:
                            # Enviar mensaje de confirmación
                            old_flete = last_quote.get('flete', 0)
                            confirmation_msg = f"✅ **Proforma actualizada**\n\n"
                            confirmation_msg += f"🔄 Flete modificado:\n"
                            confirmation_msg += f"   • Anterior: ${old_flete:.2f}\n"
                            confirmation_msg += f"   • Nuevo: ${new_flete:.2f}\n\n"
                            confirmation_msg += f"📄 Generando nueva proforma..."
                            
                            response.message(confirmation_msg)
                            
                            # Intentar enviar el PDF por WhatsApp
                            pdf_sent = whatsapp_sender.send_pdf_document(
                                From, 
                                pdf_path, 
                                f"📄 Proforma actualizada con flete de ${new_flete:.2f}\n\n💼 Documento válido para procesos comerciales."
                            )
                            
                            if pdf_sent:
                                logger.debug(f"✅ PDF actualizado enviado por WhatsApp: {pdf_path}")
                            else:
                                # Enviar via TwiML como respaldo
                                filename = os.path.basename(pdf_path)
                                base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                                download_url = f"{base_url}/webhook/download-pdf/{filename}"
                                
                                pdf_message = response.message()
                                pdf_message.body(f"📄 Proforma actualizada con flete de ${new_flete:.2f}")
                                pdf_message.media(download_url)
                            
                            return PlainTextResponse(str(response), media_type="application/xml")
                        else:
                            response.message("❌ Error generando el PDF actualizado. Intenta nuevamente.")
                            return PlainTextResponse(str(response), media_type="application/xml")
                    else:
                        response.message("❌ Error recalculando la proforma. Intenta nuevamente.")
                        return PlainTextResponse(str(response), media_type="application/xml")
                else:
                    response.message("🤔 Por favor especifica el nuevo valor del flete.\n\n💡 Ejemplo: 'modifica el flete a 0.30' o 'cambiar flete 0.25'")
                    return PlainTextResponse(str(response), media_type="application/xml")
            else:
                response.message("❌ No hay proforma previa para modificar.\n\n💡 Primero genera una proforma y luego podrás modificar el flete.")
                return PlainTextResponse(str(response), media_type="application/xml")
        
        # Comando para seleccionar idioma
        if message_lower in ['idioma', 'language', 'lang', 'cambiar idioma']:
            language_message = """🌐 **Selecciona el idioma para las proformas:**

1️⃣ Español 🇪🇸
2️⃣ English 🇺🇸

Responde con el número o escribe:
• "español" o "spanish"
• "inglés" o "english" """
            
            response.message(language_message)
            session_manager.set_session_state(user_id, 'waiting_for_language_selection', {})
            return PlainTextResponse(str(response), media_type="application/xml")
        
        if message_lower in ['precios', 'precio', 'prices', 'Precios']:
            size_message, available_sizes = interactive_service.create_size_selection_message()
            if size_message:
                response.message(size_message)
                session_manager.set_session_state(user_id, 'waiting_for_size_selection', {
                    'available_sizes': available_sizes
                })
            else:
                response.message("❌ No hay tallas disponibles en este momento.")
            response_xml = str(response)
           
            return PlainTextResponse(response_xml, media_type="application/xml")
        
        elif message_lower in ['confirmar', 'confirm', 'generar pdf', 'pdf']:
            # Verificar si hay cotización pendiente
            last_quote = session_manager.get_last_quote(user_id)
            if last_quote:
                # Mostrar opciones de idioma para el PDF
                language_options = pdf_generator.get_language_options()
                response.message(language_options)
                session_manager.set_session_state(user_id, 'selecting_language', {'quote_data': last_quote})
                return PlainTextResponse(str(response), media_type="application/xml")
            else:
                response.message("❌ No hay cotización pendiente para confirmar.\n\n💡 Primero solicita una cotización de precios y luego escribe 'confirmar'.")
            
            response_xml = str(response)
            logger.debug(f"Enviando respuesta XML: {response_xml}")
            return PlainTextResponse(response_xml, media_type="application/xml")
        
        elif session['state'] == 'selecting_language':
            # Usuario está seleccionando idioma para el PDF
            selected_language = pdf_generator.parse_language_selection(Body)
            quote_data = session['data'].get('quote_data')
            
            if selected_language and quote_data:
                # Generar PDF en el idioma seleccionado
                logger.info(f"Generando PDF en idioma {selected_language} para usuario {user_id}")
                pdf_path = pdf_generator.generate_quote_pdf(quote_data, From, selected_language)
                
                if pdf_path:
                    # Crear URL pública del PDF para envío
                    filename = os.path.basename(pdf_path)
                    base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                    download_url = f"{base_url}/webhook/download-pdf/{filename}"
                    
                    # Intentar enviar el PDF por WhatsApp usando el servicio
                    pdf_sent = whatsapp_sender.send_pdf_document(
                        From, 
                        pdf_path, 
                        "📄 Aquí tienes tu cotización oficial de BGR Export.\n\n💼 Documento válido para procesos comerciales.\n\n📞 Para cualquier consulta, contáctanos."
                    )
                    
                    if pdf_sent:
                        # Si se envió exitosamente por WhatsApp, solo confirmar
                        response.message("✅ ¡Cotización confirmada!\n\n📄 Tu PDF ha sido enviado por WhatsApp.")
                        logger.debug(f"✅ PDF enviado exitosamente por WhatsApp: {pdf_path}")
                        
                        # Mensaje adicional sobre el flete si es CFR
                        if quote_data.get('incluye_flete') and quote_data.get('flete'):
                            flete_value = quote_data['flete']
                            destination = quote_data.get('destination', '')
                            
                            flete_msg = f"💡 *Información del flete:*\n"
                            flete_msg += f"La cotización se basó con flete de ${flete_value:.2f}"
                            if destination:
                                flete_msg += f" hacia {destination}"
                            flete_msg += f"\n\n📋 Precio CFR incluye: Producto + Glaseo + Flete"
                            
                            response.message(flete_msg)
                    else:
                        # Si no se pudo enviar por WhatsApp, usar TwiML como respaldo
                        logger.info(f"⚠️ Enviando PDF via TwiML como respaldo: {download_url}")
                        
                        # Enviar mensaje con el PDF como archivo adjunto usando TwiML
                        pdf_message = response.message()
                        pdf_message.body("📄 Aquí tienes tu cotización oficial de BGR Export.\n\n💼 Documento válido para procesos comerciales.\n\n📞 Para cualquier consulta, contáctanos.")
                        pdf_message.media(download_url)
                    
                    # Limpiar la cotización después de confirmar
                    session_manager.clear_session(user_id)
                else:
                    response.message("❌ Error generando el PDF. Por favor intenta nuevamente o contacta soporte.")
            else:
                # Idioma no válido
                response.message("❌ Selección no válida.\n\n" + pdf_generator.get_language_options())
            
            response_xml = str(response)
            logger.debug(f"Enviando respuesta XML: {response_xml}")
            return PlainTextResponse(response_xml, media_type="application/xml")
                

        
        elif message_lower in ['menu', 'inicio', 'start', 'reiniciar', 'reset']:
            # Limpiar sesión y mostrar menú principal
            session_manager.clear_session(user_id)
            
            # Mensaje simple para probar
            simple_message = "🦐 Hola! Soy ShrimpBot de BGR Export\n\n¿En qué puedo ayudarte?\n\n1. Precios\n2. Productos\n3. Contacto"
            
            response.message(simple_message)
            session_manager.set_session_state(user_id, 'main_menu', {'options': ['Precios', 'Productos', 'Contacto']})
            response_xml = str(response)
            
            return PlainTextResponse(response_xml, media_type="application/xml")
        
        # Procesar según el estado de la sesión
        if session['state'] == 'main_menu':
            # Usuario está en el menú principal simplificado
            new_state, message, options = interactive_service.handle_menu_selection(Body, "main")
            
            if new_state != 'main_menu':  # Solo si cambió de estado
                response.message(message)
                
                if new_state == 'pricing':
                    # Si seleccionó precios, configurar para selección de tallas
                    session_manager.set_session_state(user_id, 'waiting_for_size_selection', {
                        'available_sizes': options
                    })
                else:
                    session_manager.set_session_state(user_id, new_state, {})
            else:
                error_msg = "🤔 Opción no válida. Por favor selecciona:\n\n1️⃣ Consultar Precios\n2️⃣ Información de Productos\n3️⃣ Contacto Comercial\n\n💡 O escribe 'menu' para reiniciar"
                response.message(error_msg)
            return PlainTextResponse(str(response), media_type="application/xml")
        
        elif session['state'] == 'waiting_for_multi_glaseo':
            # Usuario está respondiendo con el glaseo para múltiples productos
            try:
                products = session['data'].get('products', [])
                
                if not products:
                    response.message("❌ Error: No se encontraron productos. Intenta nuevamente.")
                    session_manager.clear_session(user_id)
                    return PlainTextResponse(str(response), media_type="application/xml")
                
                # Extraer glaseo del mensaje
                glaseo_percentage = None
                glaseo_factor = None
                
                glaseo_patterns = [
                    r'(\d+)\s*%',
                    r'(\d+)\s*porciento',
                    r'^(\d+)$'
                ]
                
                message_lower = Body.lower().strip()
                for pattern in glaseo_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        glaseo_percentage = int(match.group(1))
                        break
                
                # Convertir porcentaje a factor
                if glaseo_percentage == 10:
                    glaseo_factor = 0.90
                elif glaseo_percentage == 20:
                    glaseo_factor = 0.80
                elif glaseo_percentage == 30:
                    glaseo_factor = 0.70
                elif glaseo_percentage:
                    glaseo_factor = glaseo_percentage / 100
                
                if glaseo_factor:
                    logger.info(f"📊 Calculando precios para {len(products)} productos con glaseo {glaseo_percentage}%")
                    
                    # Calcular precios para todos los productos
                    products_info = []
                    failed_products = []
                    
                    for product_data in products:
                        try:
                            query = {
                                'product': product_data['product'],
                                'size': product_data['size'],
                                'glaseo_factor': glaseo_factor,
                                'glaseo_percentage': glaseo_percentage,
                                'flete_custom': 0.15,  # Flete por defecto
                                'flete_solicitado': True,
                                'custom_calculation': True
                            }
                            
                            price_info = pricing_service.get_shrimp_price(query)
                            
                            if price_info:
                                products_info.append(price_info)
                            else:
                                failed_products.append(f"{product_data['product']} {product_data['size']}")
                        except Exception as e:
                            logger.error(f"❌ Error calculando precio para {product_data['product']} {product_data['size']}: {str(e)}")
                            failed_products.append(f"{product_data['product']} {product_data['size']}")
                    
                    if products_info:
                        # Guardar para permitir modificaciones
                        session_manager.set_session_state(user_id, 'waiting_for_multi_language', {
                            'products_info': products_info,
                            'glaseo_percentage': glaseo_percentage,
                            'failed_products': failed_products
                        })
                        
                        # Mostrar resumen
                        success_count = len(products_info)
                        total_count = len(products)
                        
                        summary = f"✅ **Precios calculados para {success_count}/{total_count} productos**\n\n"
                        
                        if failed_products:
                            summary += f"⚠️ No se encontraron precios para:\n"
                            for fp in failed_products:
                                summary += f"   • {fp}\n"
                            summary += "\n"
                        
                        summary += f"🌐 **Selecciona el idioma para la cotización consolidada:**\n\n"
                        summary += f"1️⃣ Español 🇪🇸\n"
                        summary += f"2️⃣ English 🇺🇸\n\n"
                        summary += f"Responde con el número o escribe:\n"
                        summary += f"• \"español\" o \"spanish\"\n"
                        summary += f"• \"inglés\" o \"english\""
                        
                        response.message(summary)
                    else:
                        response.message("❌ No se pudieron calcular precios para ningún producto. Verifica los productos y tallas.")
                        session_manager.clear_session(user_id)
                    
                    return PlainTextResponse(str(response), media_type="application/xml")
                else:
                    response.message("🤔 Porcentaje no válido. Por favor responde con:\n\n• **10** para 10% glaseo\n• **20** para 20% glaseo\n• **30** para 30% glaseo")
                    return PlainTextResponse(str(response), media_type="application/xml")
            
            except Exception as e:
                logger.error(f"❌ Error procesando glaseo para múltiples productos: {str(e)}")
                import traceback
                traceback.print_exc()
                response.message("❌ Ocurrió un error procesando tu consulta. Intenta nuevamente.")
                session_manager.clear_session(user_id)
                return PlainTextResponse(str(response), media_type="application/xml")
        
        elif session['state'] == 'waiting_for_multi_language':
            # Usuario está seleccionando idioma para PDF consolidado
            message_lower = Body.lower().strip()
            
            selected_language = None
            if message_lower in ['1', 'español', 'spanish', 'es']:
                selected_language = 'es'
            elif message_lower in ['2', 'inglés', 'ingles', 'english', 'en']:
                selected_language = 'en'
            
            if selected_language:
                products_info = session['data'].get('products_info', [])
                glaseo_percentage = session['data'].get('glaseo_percentage', 20)
                failed_products = session['data'].get('failed_products', [])
                
                if products_info:
                    # Guardar idioma
                    session_manager.set_user_language(user_id, selected_language)
                    
                    # Generar PDF consolidado
                    logger.info(f"📄 Generando PDF consolidado con {len(products_info)} productos")
                    pdf_path = pdf_generator.generate_consolidated_quote_pdf(
                        products_info,
                        From,
                        selected_language,
                        glaseo_percentage,
                        destination=None
                    )
                    
                    if pdf_path:
                        # Enviar PDF
                        pdf_sent = whatsapp_sender.send_pdf_document(
                            From,
                            pdf_path,
                            f"Cotización Consolidada BGR Export - {len(products_info)} productos"
                        )
                        
                        if pdf_sent:
                            lang_name = "Español 🇪🇸" if selected_language == 'es' else "English 🇺🇸"
                            
                            confirmation = f"✅ **Cotización consolidada generada**\n\n"
                            confirmation += f"🌐 Idioma: {lang_name}\n"
                            confirmation += f"📦 Productos: {len(products_info)}\n"
                            confirmation += f"❄️ Glaseo: {glaseo_percentage}%\n"
                            
                            if failed_products:
                                confirmation += f"\n⚠️ {len(failed_products)} producto(s) sin precio disponible\n"
                            
                            confirmation += f"\n📄 **PDF enviado por WhatsApp**"
                            
                            response.message(confirmation)
                        else:
                            filename = os.path.basename(pdf_path)
                            base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                            download_url = f"{base_url}/webhook/download-pdf/{filename}"
                            response.message(f"✅ Cotización generada\n📄 Descarga: {download_url}")
                    else:
                        response.message("❌ Error generando PDF. Intenta nuevamente.")
                    
                    session_manager.clear_session(user_id)
                else:
                    response.message("❌ No hay productos para generar PDF.")
                    session_manager.clear_session(user_id)
            else:
                response.message("🤔 Selección inválida. Responde:\n\n1️⃣ Para Español\n2️⃣ Para English")
            
            return PlainTextResponse(str(response), media_type="application/xml")
        
        elif session['state'] == 'waiting_for_proforma_language':
            # Usuario está seleccionando idioma para la proforma
            message_lower = Body.lower().strip()
            
            selected_language = None
            if message_lower in ['1', 'español', 'spanish', 'es']:
                selected_language = 'es'
            elif message_lower in ['2', 'inglés', 'ingles', 'english', 'en']:
                selected_language = 'en'
            
            if selected_language:
                # Obtener datos de la proforma guardados
                price_info = session['data'].get('price_info')
                ai_query = session['data'].get('ai_query')
                
                # Verificar que price_info tenga glaseo antes de generar PDF
                if price_info:
                    glaseo_factor = price_info.get('factor_glaseo') or price_info.get('glaseo_factor')
                    if not glaseo_factor:
                        # Falta el glaseo - pedir al usuario que lo especifique
                        product = price_info.get('producto', 'producto')
                        size = price_info.get('talla', 'talla')
                        
                        glaseo_message = f"""❄️ **Para generar la proforma de {product} {size} necesito el glaseo:**

📋 **Opciones de glaseo disponibles:**
• **10%** glaseo (factor 0.90)
• **20%** glaseo (factor 0.80) 
• **30%** glaseo (factor 0.70)

💡 **Ejemplos:**
• "Proforma {product} {size} glaseo 10%"
• "Cotización {product} {size} con 20% glaseo"
• "{product} {size} glaseo 30%"

¿Qué porcentaje de glaseo necesitas? 🤔"""
                        
                        response.message(glaseo_message)
                        session_manager.clear_session(user_id)
                        return PlainTextResponse(str(response), media_type="application/xml")
                    
                    # Guardar la cotización para permitir modificaciones posteriores
                    session_manager.set_last_quote(user_id, price_info)
                    
                    # Guardar el idioma del usuario
                    session_manager.set_user_language(user_id, selected_language)
                    
                    # Debug: Verificar datos antes de generar PDF
                    logger.info(f"🔍 ROUTES - Datos antes de generar PDF:")
                    logger.info(f"   - Producto: {price_info.get('producto')}")
                    logger.info(f"   - Talla: {price_info.get('talla')}")
                    logger.info(f"   - Precio base: ${price_info.get('precio_kg', 0):.2f}")
                    logger.info(f"   - Precio FOB: ${price_info.get('precio_fob_kg', 0):.2f}")
                    logger.info(f"   - Precio glaseo: ${price_info.get('precio_glaseo_kg', 0):.2f}")
                    logger.info(f"   - Precio FOB+glaseo: ${price_info.get('precio_fob_con_glaseo_kg', 0):.2f}")
                    logger.info(f"   - Precio CFR final: ${price_info.get('precio_final_kg', 0):.2f}")
                    logger.info(f"   - Flete: ${price_info.get('flete', 0):.2f}")
                    logger.info(f"   - Factor glaseo: {price_info.get('factor_glaseo', 0)}")
                    
                    # Generar PDF en el idioma seleccionado
                    logger.info(f"📄 Generando PDF para usuario {user_id} en idioma {selected_language}")
                    pdf_path = pdf_generator.generate_quote_pdf(price_info, From, selected_language)
                    
                    if pdf_path:
                        # Crear URL pública del PDF para envío
                        filename = os.path.basename(pdf_path)
                        base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                        download_url = f"{base_url}/webhook/download-pdf/{filename}"
                        
                        # Intentar enviar el PDF por WhatsApp
                        pdf_sent = whatsapp_sender.send_pdf_document(
                            From, 
                            pdf_path, 
                            f"Cotización BGR Export - {price_info.get('producto', 'Camarón')} {price_info.get('talla', '')}"
                        )
                        
                        if pdf_sent:
                            lang_name = "Español 🇪🇸" if selected_language == 'es' else "English 🇺🇸"
                            
                            confirmation_msg = f"✅ **Proforma generada y enviada**\n\n"
                            confirmation_msg += f"🌐 Idioma: {lang_name}\n"
                            confirmation_msg += f"🦐 {price_info.get('producto', 'Producto')}: {price_info.get('talla', '')}\n"
                            
                            if price_info.get('cliente_nombre'):
                                confirmation_msg += f"👤 Cliente: {price_info['cliente_nombre'].title()}\n"
                            
                            if price_info.get('destination'):
                                confirmation_msg += f"🌍 Destino: {price_info['destination']}\n"
                            
                            # Línea del precio FOB eliminada según solicitud del usuario
                            # if price_info.get('precio_final_kg'):
                            #     confirmation_msg += f"💰 Precio FOB: ${price_info['precio_final_kg']:.2f}/kg - ${price_info.get('precio_final_lb', 0):.2f}/lb\n"
                            
                            confirmation_msg += f"\n📄 **PDF enviado por WhatsApp**"
                            
                            response.message(confirmation_msg)
                            
                            # Mensaje adicional sobre el flete si es CFR
                            if price_info.get('incluye_flete') and price_info.get('flete'):
                                flete_value = price_info['flete']
                                destination = price_info.get('destination', '')
                                
                                flete_msg = f"💡 *Información del flete:*\n"
                                flete_msg += f"La cotización se basó con flete de ${flete_value:.2f}"
                                if destination:
                                    flete_msg += f" hacia {destination}"
                                flete_msg += f"\n\n📋 Precio CFR incluye: Producto + Glaseo + Flete"
                                flete_msg += f"\n\n🔄 *¿Necesitas cambiar el flete?*"
                                flete_msg += f"\nEscribe: 'modifica el flete a [valor]'"
                                flete_msg += f"\nEjemplo: 'modifica el flete a 0.30'"
                                
                                response.message(flete_msg)
                        else:
                            logger.error(f"❌ Error enviando PDF por WhatsApp")
                            response.message(f"✅ Proforma generada\n📄 Descarga tu PDF: {download_url}")
                    else:
                        logger.error(f"❌ Error generando PDF")
                        response.message("❌ Error generando la proforma. Intenta nuevamente.")
                
                # Limpiar sesión
                session_manager.clear_session(user_id)
            else:
                response.message("🤔 Selección inválida. Por favor responde:\n\n1️⃣ Para Español\n2️⃣ Para English\n\nO escribe 'menu' para volver al inicio")
            
            return PlainTextResponse(str(response), media_type="application/xml")
        
        elif session['state'] == 'waiting_for_language_selection':
            # Usuario está seleccionando idioma
            message_lower = Body.lower().strip()
            
            selected_language = None
            if message_lower in ['1', 'español', 'spanish', 'es']:
                selected_language = 'es'
            elif message_lower in ['2', 'inglés', 'ingles', 'english', 'en']:
                selected_language = 'en'
            
            if selected_language:
                # Guardar idioma preferido en la sesión
                session_manager.set_user_language(user_id, selected_language)
                
                lang_name = "Español 🇪🇸" if selected_language == 'es' else "English 🇺🇸"
                response.message(f"✅ Idioma configurado: {lang_name}\n\nAhora puedes solicitar proformas y se generarán en tu idioma preferido.")
                session_manager.clear_session(user_id)
            else:
                response.message("🤔 Selección inválida. Por favor responde:\n\n1️⃣ Para Español\n2️⃣ Para English\n\nO escribe 'menu' para volver al inicio")
            
            return PlainTextResponse(str(response), media_type="application/xml")
        
        elif session['state'] == 'waiting_for_size_selection':
            # Usuario está seleccionando una talla
            available_sizes = session['data'].get('available_sizes', [])
            selected_size = interactive_service.parse_selection_response(Body, available_sizes)
            
            if selected_size:
                # Talla seleccionada, ahora mostrar productos
                product_message, available_products = interactive_service.create_product_selection_message(selected_size)
                
                if product_message:
                    response.message(product_message)
                    session_manager.set_session_state(user_id, 'waiting_for_product_selection', {
                        'selected_size': selected_size,
                        'available_products': available_products
                    })
                else:
                    response.message(f"❌ No hay productos disponibles para la talla {selected_size}")
                    session_manager.clear_session(user_id)
            else:
                response.message("🤔 Selección inválida. Por favor responde con:\n\n📝 El número de la opción (1-9)\n💡 O escribe 'menu' para volver al inicio")
            return PlainTextResponse(str(response), media_type="application/xml")
        
        elif session['state'] == 'waiting_for_product_selection':
            # Usuario está seleccionando un producto
            available_products = session['data'].get('available_products', [])
            selected_product = interactive_service.parse_selection_response(Body, available_products)
            
            if selected_product:
                # Producto seleccionado, obtener precio
                selected_size = session['data'].get('selected_size')
                
                user_input = {
                    'size': selected_size,
                    'product': selected_product
                }
                
                price_info = pricing_service.get_shrimp_price(user_input)
                
                if price_info:
                    formatted_response = format_price_response(price_info)
                    
                    # Agregar instrucción para confirmar
                    formatted_response += "\n\n✅ **Para generar PDF:** Escribe 'confirmar'"
                    
                    response.message(formatted_response)
                    
                    # Almacenar cotización para posible confirmación
                    session_manager.set_last_quote(user_id, price_info)
                    session_manager.set_session_state(user_id, 'quote_ready', {})
                else:
                    error_msg = f"❌ No encontré información para {selected_product} talla {selected_size}"
                    response.message(error_msg)
                    session_manager.clear_session(user_id)
            else:
                error_msg = "🤔 Selección inválida. Por favor responde con:\n\n📝 El número de la opción\n💡 O escribe 'menu' para volver al inicio"
                response.message(error_msg)
            return PlainTextResponse(str(response), media_type="application/xml")
        
        else:
            # Estado inicial - mostrar mensaje de bienvenida y menú principal
            message_lower = Body.lower().strip()
            
            # Otros comandos especiales
            if message_lower in ['tallas', 'sizes', 'opciones']:
                size_message, available_sizes = interactive_service.create_size_selection_message()
                if size_message:
                    response.message(size_message)
                    session_manager.set_session_state(user_id, 'waiting_for_size_selection', {
                        'available_sizes': available_sizes
                    })
                else:
                    response.message("❌ No hay tallas disponibles en este momento.")
                return PlainTextResponse(str(response), media_type="application/xml")
            
            elif message_lower in ['productos', 'products']:
                products = pricing_service.get_available_products()
                product_list = "\n".join([f"• {product}" for product in products])
                response.message(f"🏷️ Productos disponibles:\n\n{product_list}\n\n💡 Escribe 'tallas' para ver las tallas disponibles")
                return PlainTextResponse(str(response), media_type="application/xml")
            
            elif message_lower in ['ayuda', 'help', '?']:
                response.message("🦐 **ShrimpBot - BGR Export** 🤖\n\n"
                               "📋 **Comandos disponibles:**\n"
                               "• `menu` - 🏠 Mostrar menú principal\n"
                               "• `precios` - 💰 Consultar precios directamente\n"
                               "• `confirmar` - 📄 Generar PDF de cotización\n"
                               "• `tallas` - 📏 Ver tallas disponibles\n"
                               "• `productos` - 🏷️ Ver productos disponibles\n"
                               "• `precio HLSO 16/20` - 🔍 Consulta directa\n\n"
                               "💡 **Ejemplos de consultas:**\n"
                               "• Precio HLSO 16/20 para 15000 lb destino China\n"
                               "• P&D IQF 21/25\n"
                               "• EZ PEEL 26/30\n\n"
                               "📄 **Flujo completo:**\n"
                               "1. Solicita una cotización\n"
                               "2. Revisa los precios calculados\n"
                               "3. Escribe 'confirmar' para generar PDF\n\n"
                               "🌊 ¡Estoy aquí para ayudarte!")
                return PlainTextResponse(str(response), media_type="application/xml")
        
        # Para estados conversacionales o iniciales, procesar con respuesta inteligente
        if session['state'] in ['conversational', 'idle']:
            # Continuar con la lógica de respuesta inteligente abajo
            pass
            
        # Intentar parsear como consulta de precio directa
        user_input = parse_user_message(Body)
        logger.debug(f"🔍 Parse result para '{Body}': {user_input}")
        
        if user_input:
            # Obtener precio del camarón
            price_info = pricing_service.get_shrimp_price(user_input)
            
            if price_info:
                formatted_response = format_price_response(price_info)
                
                # Agregar instrucción para confirmar
                formatted_response += "\n\n✅ **Para generar PDF:** Escribe 'confirmar'"
                
                response.message(formatted_response)
                
                # Almacenar cotización para posible confirmación
                session_manager.set_last_quote(user_id, price_info)
                session_manager.set_session_state(user_id, 'quote_ready', {})
                return PlainTextResponse(str(response), media_type="application/xml")
        
        # Respuesta rápida para casos simples
        logger.debug(f"🔍 Procesando respuesta para mensaje: '{Body}'")
        
        smart_response = None
        
        # Para saludos y casos simples, usar respuesta rápida
        if ai_analysis and ai_analysis.get('intent') in ['greeting', 'menu_request']:
            smart_response = openai_service.get_smart_fallback_response(Body, ai_analysis)
            logger.debug(f"🧠 Respuesta rápida obtenida: {smart_response}")
        
        # Solo usar OpenAI para casos complejos
        elif openai_service.is_available() and ai_analysis and ai_analysis.get('confidence', 0) > 0.7:
            logger.debug(f"🤖 Intentando respuesta OpenAI para confianza: {ai_analysis.get('confidence', 0)}")
            smart_response = openai_service.generate_smart_response(Body, session)
            logger.debug(f"🤖 Respuesta OpenAI obtenida: {smart_response}")
        
        # Fallback para otros casos
        elif ai_analysis and ai_analysis.get('confidence', 0) > 0.5:
            smart_response = openai_service.get_smart_fallback_response(Body, ai_analysis)
            logger.debug(f"🧠 Respuesta fallback obtenida: {smart_response}")
        
        if smart_response:
            # Usar respuesta inteligente (IA o fallback)
            logger.debug(f"✅ Usando respuesta inteligente: {smart_response}")
            response.message(smart_response)
            logger.debug(f"📤 Respuesta configurada en objeto response")
            # Mantener en estado conversacional sin menú numerado
            session_manager.set_session_state(user_id, 'conversational', {})
            logger.debug(f"🔄 Estado actualizado a conversational")
        else:
            # Fallback final al menú de bienvenida tradicional
            logger.info("⚠️ No hay respuesta inteligente, usando menú tradicional")
            welcome_msg = interactive_service.create_welcome_message()
            menu_msg, options = interactive_service.create_main_menu()
            full_message = f"{welcome_msg}\n\n{menu_msg}"
            response.message(full_message)
            session_manager.set_session_state(user_id, 'main_menu', {'options': options})
        
        response_xml = str(response)
        logger.debug(f"Enviando respuesta XML: {response_xml}")
        
        # Validar que el XML sea válido
        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(response_xml)
            logger.debug("✅ XML válido")
        except Exception as xml_error:
            logger.error(f"❌ XML inválido: {xml_error}")
            # Crear respuesta de emergencia
            emergency_response = MessagingResponse()
            emergency_response.message("¡Hola! Soy ShrimpBot de BGR Export. ¿En qué puedo ayudarte?")
            response_xml = str(emergency_response)
            logger.info(f"🚨 Usando respuesta de emergencia: {response_xml}")
        
        # Agregar headers de seguridad
        response = PlainTextResponse(response_xml, media_type="application/xml")
        return add_security_headers(response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        response = MessagingResponse()
        response.message("❌ Ocurrió un error procesando tu consulta. Intenta nuevamente.")
        response_xml = str(response)
        logger.info(f"Enviando respuesta de error XML: {response_xml}")
        return add_security_headers(PlainTextResponse(response_xml, media_type="application/xml"))

@webhook_router.get("/whatsapp")
async def whatsapp_webhook_verification(request: Request):
    """
    Verificación del webhook de Twilio
    """
    return {"status": "webhook_ready"}

@webhook_router.post("/test")
async def test_webhook():
    """
    Endpoint de prueba para verificar respuestas XML
    """
    response = MessagingResponse()
    response.message("Mensaje de prueba desde ShrimpBot")
    response_xml = str(response)
    logger.info(f"Respuesta de prueba XML: {response_xml}")
    return PlainTextResponse(response_xml, media_type="application/xml")

@webhook_router.post("/simple")
async def simple_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    MessageSid: str = Form(...)
):
    """
    Webhook simplificado para debugging
    """
    logger.info(f"SIMPLE: Mensaje de {From}: {Body}")
    
    response = MessagingResponse()
    response.message("✅ Mensaje recibido correctamente!")
    
    response_xml = str(response)
    logger.info(f"SIMPLE: Enviando XML: {response_xml}")
    
    return PlainTextResponse(response_xml, media_type="application/xml")

@webhook_router.post("/test-response")
async def test_response():
    """
    Endpoint para probar respuestas TwiML
    """
    response = MessagingResponse()
    response.message("🦐 Mensaje de prueba desde BGR Export Bot")
    
    response_xml = str(response)
    logger.info(f"TEST: XML generado: {response_xml}")
    
    return PlainTextResponse(response_xml, media_type="application/xml")

@webhook_router.post("/reload-data")
async def reload_data(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Endpoint para recargar datos desde Google Sheets
    """
    # Verificar token de administrador
    if not verify_admin_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        # Reinicializar servicios con variables de entorno actuales
        global pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service
        
        # Forzar reinicialización
        pricing_service = None
        interactive_service = None
        pdf_generator = None
        whatsapp_sender = None
        openai_service = None
        
        # Inicializar servicios
        pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service = get_services()
        
        # Contar datos cargados
        total_prices = sum(len(product_data) for product_data in pricing_service.excel_service.prices_data.values())
        products = [p for p in pricing_service.excel_service.prices_data.keys() if pricing_service.excel_service.prices_data[p]]
        
        return {
            "status": "success", 
            "message": "Servicios reinicializados y datos recargados",
            "total_prices": total_prices,
            "products": products,
            "google_sheets_id": os.getenv('GOOGLE_SHEETS_ID', 'No configurado')[:20] + "..."
        }
    except Exception as e:
        logger.error(f"Error recargando datos: {str(e)}")
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

@webhook_router.get("/data-status")
async def data_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Endpoint para verificar el estado de los datos
    """
    # Verificar token de administrador
    if not verify_admin_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        # Inicializar servicios si no están inicializados
        pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service = get_services()
        
        # Verificar datos actuales
        total_prices = sum(len(product_data) for product_data in pricing_service.excel_service.prices_data.values())
        products = [p for p in pricing_service.excel_service.prices_data.keys() if pricing_service.excel_service.prices_data[p]]
        
        # Verificar configuración de Google Sheets
        sheets_id = os.getenv('GOOGLE_SHEETS_ID')
        sheets_credentials = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        
        # Verificar si el servicio de Google Sheets está funcionando
        sheets_service_status = "No inicializado"
        if hasattr(pricing_service.excel_service, 'google_sheets_service'):
            if pricing_service.excel_service.google_sheets_service.sheet:
                sheets_service_status = "Conectado"
            else:
                sheets_service_status = "Error de conexión"
        
        return {
            "status": "success",
            "data_source": "Google Sheets" if sheets_id and sheets_credentials else "Local Excel",
            "total_prices": total_prices,
            "products": products,
            "google_sheets_configured": bool(sheets_id and sheets_credentials),
            "google_sheets_id": sheets_id[:20] + "..." if sheets_id else None,
            "sheets_service_status": sheets_service_status,
            "env_loaded": bool(sheets_id)
        }
    except Exception as e:
        logger.error(f"Error verificando estado: {str(e)}")
        return {"status": "error", "message": str(e)}

@webhook_router.get("/test-twilio")
async def test_twilio(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Endpoint para probar las credenciales de Twilio
    """
    # Verificar token de administrador
    if not verify_admin_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        from twilio.rest import Client
        
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER
        
        if not all([account_sid, auth_token, whatsapp_number]):
            return {
                "status": "error", 
                "message": "Credenciales de Twilio no configuradas",
                "config": {
                    "account_sid": bool(account_sid),
                    "auth_token": bool(auth_token),
                    "whatsapp_number": bool(whatsapp_number)
                }
            }
        
        client = Client(account_sid, auth_token)
        
        # Probar conexión obteniendo información de la cuenta
        account = client.api.accounts(account_sid).fetch()
        
        return {
            "status": "success",
            "message": "Credenciales de Twilio válidas",
            "account_name": account.friendly_name,
            "account_status": account.status,
            "whatsapp_number": whatsapp_number
        }
        
    except Exception as e:
        logger.error(f"Error probando Twilio: {str(e)}")
        return {"status": "error", "message": str(e)}

@webhook_router.post("/test-pdf-send")
async def test_pdf_send(
    phone_number: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Endpoint para probar el envío de PDFs
    """
    # Verificar token de administrador
    if not verify_admin_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    # Validar número de teléfono
    if not phone_number.startswith("whatsapp:"):
        phone_number = f"whatsapp:{phone_number}"
    
    if not validate_phone_number(phone_number):
        raise HTTPException(status_code=400, detail="Invalid phone number format")
        
    try:
        # Crear una cotización de prueba
        test_quote = {
            'size': '16/20',
            'product': 'HLSO',
            'quantity': 15000,
            'destination': 'China',
            'fob_price': 5.50,
            'glaseo_price': 6.05,
            'final_price': 6.85,
            'freight_cost': 0.80,
            'total_value': 102750.00
        }
        
        # Inicializar servicios si no están inicializados
        pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service = get_services()
        
        # Generar PDF de prueba
        pdf_path = pdf_generator.generate_quote_pdf(test_quote, f"whatsapp:{phone_number}")
        
        if pdf_path:
            # Intentar enviar por WhatsApp
            pdf_sent = whatsapp_sender.send_pdf_document(
                f"whatsapp:{phone_number}",
                pdf_path,
                "📄 PDF de prueba - BGR Export"
            )
            
            filename = os.path.basename(pdf_path)
            download_url = f" https://e28980114917.ngrok-free.app/webhook/download-pdf/{filename}"
            
            return {
                "status": "success" if pdf_sent else "partial",
                "message": "PDF enviado por WhatsApp" if pdf_sent else "PDF generado, pero no enviado por WhatsApp",
                "pdf_generated": True,
                "pdf_sent_whatsapp": pdf_sent,
                "download_url": download_url
            }
        else:
            return {
                "status": "error",
                "message": "Error generando PDF de prueba"
            }
            
    except Exception as e:
        logger.error(f"Error en test de PDF: {str(e)}")
        return {"status": "error", "message": str(e)}

@webhook_router.get("/download-pdf/{filename}")
async def download_pdf(filename: str):
    """
    Endpoint para descargar PDFs generados
    """
    try:
        from fastapi.responses import FileResponse
        
        pdf_path = os.path.join("generated_pdfs", filename)
        logger.info(f"🔍 Buscando PDF en: {pdf_path}")
        logger.info(f"📁 Directorio actual: {os.getcwd()}")
        
        # Listar archivos en el directorio
        if os.path.exists("generated_pdfs"):
            files = os.listdir("generated_pdfs")
            logger.info(f"📄 Archivos en generated_pdfs: {files}")
        else:
            logger.error("❌ Directorio generated_pdfs no existe")
        
        if os.path.exists(pdf_path):
            logger.debug(f"✅ PDF encontrado: {pdf_path}")
            return FileResponse(
                path=pdf_path,
                filename=filename,
                media_type='application/pdf',
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Access-Control-Allow-Headers": "*"
                }
            )
        else:
            logger.error(f"❌ PDF no encontrado en: {pdf_path}")
            raise HTTPException(status_code=404, detail="PDF no encontrado")
            
    except Exception as e:
        logger.error(f"Error descargando PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")