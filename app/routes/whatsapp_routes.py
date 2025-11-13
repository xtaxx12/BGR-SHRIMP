import logging
import os
import re
import time

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

from app.config import settings
from app.security import (
    SecureTempFile,
    add_security_headers,
    rate_limit,
    sanitize_input,
    validate_phone_number,
)
from app.services.audio_handler import AudioHandler
from app.services.utils import format_price_response, parse_ai_analysis_to_query, parse_user_message
from app.services.utils_new import retry
from app.utils.language_utils import detect_language, glaseo_percentage_to_factor
from app.utils.message_utils import is_duplicate_message
from app.utils.service_utils import get_services
from app.services.session import session_manager

logger = logging.getLogger(__name__)

whatsapp_router = APIRouter()


@whatsapp_router.post("/whatsapp")
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
            logger.info("🎤 Procesando mensaje de audio...")
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
                    r'al\s*(\d+)',  # "al 20"
                    r'^(\d+)$',  # Solo el número "20"
                ]

                message_lower = Body.lower().strip()
                for pattern in glaseo_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        glaseo_percentage = int(match.group(1))
                        break

                # Convertir porcentaje a factor usando función helper
                if glaseo_percentage:
                    glaseo_factor = glaseo_percentage_to_factor(glaseo_percentage)

                if glaseo_factor:
                    # Actualizar ai_query con el glaseo
                    ai_query['glaseo_factor'] = glaseo_factor
                    ai_query['glaseo_percentage'] = glaseo_percentage

                    # Intentar calcular el precio con el glaseo
                    price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(ai_query,))

                    if price_info:
                        logger.debug(f"✅ Datos de proforma validados con glaseo {glaseo_percentage}%")

                        # Detectar idioma automáticamente y generar PDF
                        ai_analysis = {}
                        user_lang = detect_language(Body, ai_analysis)
                        session_manager.set_last_quote(user_id, price_info)
                        session_manager.set_user_language(user_id, user_lang)

                        # Mostrar resumen (generación automática en idioma detectado)
                        product_name = price_info.get('producto', 'Camarón')
                        size = price_info.get('talla', '')
                        client_name = price_info.get('cliente_nombre', '')

                        summary = "📋 **Proforma lista para generar:**\n"
                        summary += f"🦐 Producto: {product_name} {size}\n"
                        summary += f"❄️ Glaseo: {glaseo_percentage}%\n"
                        if client_name:
                            summary += f"👤 Cliente: {client_name.title()}\n"

                        # Generar PDF automáticamente
                        logger.info(f"📄 Generando PDF automáticamente en idioma {user_lang} para usuario {user_id}")
                        pdf_path = pdf_generator.generate_quote_pdf(price_info, From, user_lang)

                        if pdf_path:
                            pdf_sent = whatsapp_sender.send_pdf_document(
                                From,
                                pdf_path,
                                f"Cotización BGR Export - {product_name} {size}"
                            )
                            if pdf_sent:
                                response.message(f"✅ Proforma generada y enviada en {'Español' if user_lang == 'es' else 'English'} 🇪🇸🇺🇸")
                            else:
                                filename = os.path.basename(pdf_path)
                                base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                                download_url = f"{base_url}/webhook/download-pdf/{filename}"
                                pdf_message = response.message()
                                pdf_message.body(f"✅ Proforma generada. Descarga: {download_url}")
                        else:
                            response.message("❌ Error generando la proforma. Intenta nuevamente.")

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

                    response.message("🤔 Porcentaje no válido. Por favor responde con:\n\n• **10** para 10% glaseo\n• **20** para 20% glaseo\n• **30** para 30% glaseo\n\nO escribe 'menu' para volver al inicio")
                    return PlainTextResponse(str(response), media_type="application/xml")
            else:
                response.message("❌ Error: No se encontraron datos de la solicitud. Por favor intenta nuevamente.")
                session_manager.clear_session(user_id)
                return PlainTextResponse(str(response), media_type="application/xml")

        # Manejar respuesta de aclaración de productos (Inteiro vs Colas)
        if session['state'] == 'waiting_for_product_clarification':
            try:
                sizes_inteiro = session['data'].get('sizes_inteiro', [])
                sizes_colas = session['data'].get('sizes_colas', [])
                destination = session['data'].get('destination')
                glaseo_percentage = session['data'].get('glaseo_percentage')
                flete_solicitado = session['data'].get('flete_solicitado', False)
                
                # Parsear la respuesta del usuario para extraer productos
                message_upper = Body.upper()
                
                # Detectar productos mencionados
                product_inteiro = None
                product_colas = None
                
                # Patrones para detectar productos
                if 'HOSO' in message_upper and ('INTEIRO' in message_upper or 'ENTERO' in message_upper or 'PARA INTEIRO' in message_upper or 'INTEIRO' in message_upper):
                    product_inteiro = 'HOSO'
                elif 'HLSO' in message_upper and ('INTEIRO' in message_upper or 'ENTERO' in message_upper or 'PARA INTEIRO' in message_upper):
                    product_inteiro = 'HLSO'
                
                if 'COOKED' in message_upper and ('COLAS' in message_upper or 'PARA COLAS' in message_upper or 'COLA' in message_upper):
                    product_colas = 'COOKED'
                elif 'PRE-COCIDO' in message_upper or 'PRECOCIDO' in message_upper:
                    product_colas = 'PRE-COCIDO'
                elif 'COCIDO SIN TRATAR' in message_upper:
                    product_colas = 'COCIDO SIN TRATAR'
                
                # Si no detectó productos específicos, intentar detectar solo los nombres
                if not product_inteiro and sizes_inteiro:
                    if 'HOSO' in message_upper:
                        product_inteiro = 'HOSO'
                    elif 'HLSO' in message_upper:
                        product_inteiro = 'HLSO'
                
                if not product_colas and sizes_colas:
                    if 'COOKED' in message_upper:
                        product_colas = 'COOKED'
                    elif 'PRE-COCIDO' in message_upper or 'PRECOCIDO' in message_upper:
                        product_colas = 'PRE-COCIDO'
                
                # Construir lista de productos
                all_products = []
                if product_inteiro and sizes_inteiro:
                    for size in sizes_inteiro:
                        all_products.append({'product': product_inteiro, 'size': size})
                if product_colas and sizes_colas:
                    for size in sizes_colas:
                        all_products.append({'product': product_colas, 'size': size})
                
                if not all_products:
                    response.message("🤔 No pude identificar los productos. Por favor especifica claramente:\n\nEjemplo: 'HOSO para inteiro y COOKED para colas'")
                    return PlainTextResponse(str(response), media_type="application/xml")
                
                logger.info(f"📋 Productos identificados: {len(all_products)} productos")
                
                # Ahora solicitar el flete (ya que es CFR)
                products_list = "\n".join([f"   {i+1}. {p['product']} {p['size']}" for i, p in enumerate(all_products)])
                
                flete_message = f"""✅ **Productos confirmados: {len(all_products)} tallas**

{products_list}

🌍 **Destino:** {destination}
❄️ **Glaseo:** {glaseo_percentage}%

🚢 **Para calcular el precio CFR necesito el valor del flete a {destination}:**

💡 **Ejemplos:**
• "flete 0.20"
• "0.25 de flete"
• "con flete de 0.22"

¿Cuál es el valor del flete por kilo? 💰"""
                
                response.message(flete_message)
                
                # Guardar estado para esperar respuesta de flete
                session_manager.set_session_state(user_id, 'waiting_for_multi_flete', {
                    'products': all_products,
                    'glaseo_factor': glaseo_percentage_to_factor(glaseo_percentage) if glaseo_percentage and glaseo_percentage > 0 else None,
                    'glaseo_percentage': glaseo_percentage,
                    'destination': destination
                })
                
                return PlainTextResponse(str(response), media_type="application/xml")
                
            except Exception as e:
                logger.error(f"❌ Error procesando aclaración de productos: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                response.message("❌ Error procesando tu respuesta. Por favor intenta nuevamente.")
                session_manager.clear_session(user_id)
                return PlainTextResponse(str(response), media_type="application/xml")

        # Manejar respuesta de flete para múltiples productos
        if session['state'] == 'waiting_for_multi_flete':
            try:
                # Usuario está respondiendo con el valor del flete para múltiples productos
                products = session['data'].get('products')
                glaseo_factor = session['data'].get('glaseo_factor')
                glaseo_percentage = session['data'].get('glaseo_percentage')
                is_ddp = session['data'].get('is_ddp', False)

                if products and glaseo_factor:
                    # Intentar extraer el valor del flete del mensaje
                    flete_value = None

                    # Patrones para detectar valor de flete
                    flete_patterns = [
                        r'(\d+\.?\d*)\s*(?:centavos?|cents?)',
                        r'(?:flete\s*)?(\d+\.?\d*)(?:\s|$)',
                        r'(\d+\.?\d*)\s*(?:de\s*)?flete',
                        r'^\s*(\d+\.?\d*)\s*$',
                    ]

                    message_lower = Body.lower().strip()
                    for pattern in flete_patterns:
                        match = re.search(pattern, message_lower)
                        if match:
                            try:
                                flete_value = float(match.group(1))
                                if flete_value > 5:
                                    flete_value = flete_value / 100
                                break
                            except ValueError:
                                continue

                    if flete_value and flete_value > 0:
                        logger.info(f"🚢 Flete especificado para múltiples productos: ${flete_value:.2f}")

                        # Calcular precios para todos los productos con el flete
                        products_info = []
                        failed_products = []

                        for product_data in products:
                            try:
                                query = {
                                    'product': product_data['product'],
                                    'size': product_data['size'],
                                    'glaseo_factor': glaseo_factor,
                                    'glaseo_percentage': glaseo_percentage,
                                    'flete_custom': flete_value,
                                    'flete_solicitado': True,
                                    'custom_calculation': True
                                }

                                price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(query,))

                                if price_info:
                                    products_info.append(price_info)
                                else:
                                    failed_products.append(f"{product_data['product']} {product_data['size']}")
                            except Exception as e:
                                logger.error(f"❌ Error calculando precio para {product_data['product']} {product_data['size']}: {str(e)}")
                                failed_products.append(f"{product_data['product']} {product_data['size']}")

                        if products_info:
                            # Detectar idioma y generar PDF consolidado automáticamente
                            user_lang = session_manager.get_user_language(user_id) or 'es'

                            # Guardar como última cotización
                            session_manager.set_last_quote(user_id, {
                                'consolidated': True,
                                'products_info': products_info,
                                'glaseo_percentage': glaseo_percentage,
                                'failed_products': failed_products,
                                'flete': flete_value
                            })
                            session_manager.set_user_language(user_id, user_lang)

                            logger.info(f"📄 Generando PDF consolidado con flete ${flete_value:.2f}")
                            pdf_path = pdf_generator.generate_consolidated_quote_pdf(
                                products_info,
                                From,
                                user_lang,
                                glaseo_percentage
                            )

                            if pdf_path:
                                pdf_sent = whatsapp_sender.send_pdf_document(
                                    From,
                                    pdf_path,
                                    f"Cotización Consolidada BGR Export - {len(products_info)} productos"
                                )
                                if pdf_sent:
                                    response.message(f"✅ Cotización consolidada generada con flete ${flete_value:.2f} - {len(products_info)} productos 🚢")
                                else:
                                    filename = os.path.basename(pdf_path)
                                    base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                                    download_url = f"{base_url}/webhook/download-pdf/{filename}"
                                    response.message(f"✅ Cotización generada\n📄 Descarga: {download_url}")

                                # Limpiar sesión
                                session_manager.clear_session(user_id)
                            else:
                                response.message("❌ Error generando PDF consolidado. Intenta nuevamente.")
                                session_manager.clear_session(user_id)
                        else:
                            response.message("❌ No se pudieron calcular precios para ningún producto.")
                            session_manager.clear_session(user_id)

                        return PlainTextResponse(str(response), media_type="application/xml")
                    else:
                        # Flete no válido
                        response.message("🤔 Valor no válido. Por favor responde con el valor del flete:\n\n💡 **Ejemplos:**\n• **0.25** para $0.25/kg\n• **0.30** para $0.30/kg\n• **flete 0.22**\n\nO escribe 'menu' para volver al inicio")
                        return PlainTextResponse(str(response), media_type="application/xml")
                else:
                    response.message("❌ Error: No se encontraron datos de la solicitud. Por favor intenta nuevamente.")
                    session_manager.clear_session(user_id)
                    return PlainTextResponse(str(response), media_type="application/xml")

            except Exception as e:
                logger.error(f"❌ Error procesando respuesta de flete para múltiples productos: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                response.message("❌ Error procesando el valor del flete. Intenta nuevamente.")
                session_manager.clear_session(user_id)
                return PlainTextResponse(str(response), media_type="application/xml")

        # Manejar respuesta de flete
        if session['state'] == 'waiting_for_flete':
            try:
                # Usuario está respondiendo con el valor del flete
                ai_query = session['data'].get('ai_query')

                if ai_query:
                    # Intentar extraer el valor del flete del mensaje
                    flete_value = None

                    # Patrones para detectar valor de flete
                    flete_patterns = [
                        r'(\d+\.?\d*)\s*(?:centavos?|cents?)',  # "25 centavos", "0.25 cents"
                        r'(?:flete\s*)?(\d+\.?\d*)(?:\s|$)',  # "flete 0.25", "0.25"
                        r'(\d+\.?\d*)\s*(?:de\s*)?flete',  # "0.25 de flete"
                        r'^\s*(\d+\.?\d*)\s*$',  # Solo el número "0.25"
                    ]

                    message_lower = Body.lower().strip()
                    for pattern in flete_patterns:
                        match = re.search(pattern, message_lower)
                        if match:
                            try:
                                flete_value = float(match.group(1))
                                # Si el valor es mayor a 5, probablemente son centavos, convertir a dólares
                                if flete_value > 5:
                                    flete_value = flete_value / 100
                                break
                            except ValueError:
                                continue

                    if flete_value and flete_value > 0:
                        # Actualizar ai_query con el flete
                        ai_query['flete_custom'] = flete_value

                        logger.info(f"🚢 Flete especificado por usuario: ${flete_value:.2f}")
                        logger.info(f"🔍 ai_query actualizado: {ai_query}")

                        # Intentar calcular el precio con el flete
                        price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(ai_query,))
                        logger.info(f"🔍 price_info resultado: {price_info is not None}")

                        if price_info:
                            logger.debug(f"✅ Datos de proforma validados con flete ${flete_value:.2f}")

                            # Detectar idioma (usar el guardado en sesión o detectar del mensaje)
                            user_lang = session_manager.get_user_language(user_id) or 'es'
                            session_manager.set_last_quote(user_id, price_info)
                            session_manager.set_user_language(user_id, user_lang)

                            # Generar PDF automáticamente
                            product_name = price_info.get('producto', 'Camarón')
                            size = price_info.get('talla', '')
                            destination = price_info.get('destination', '')

                            logger.info(f"📄 Generando PDF automáticamente con flete ${flete_value:.2f} para usuario {user_id}")
                            pdf_path = pdf_generator.generate_quote_pdf(price_info, From, user_lang)

                            if pdf_path:
                                pdf_sent = whatsapp_sender.send_pdf_document(
                                    From,
                                    pdf_path,
                                    f"Cotización BGR Export - {product_name} {size}"
                                )
                                if pdf_sent:
                                    response.message(f"✅ Proforma generada con flete ${flete_value:.2f} a {destination} 🚢")
                                else:
                                    filename = os.path.basename(pdf_path)
                                    base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                                    download_url = f"{base_url}/webhook/download-pdf/{filename}"
                                    pdf_message = response.message()
                                    pdf_message.body(f"✅ Proforma generada. Descarga: {download_url}")

                                # Limpiar sesión después de generar exitosamente
                                session_manager.clear_session(user_id)
                            else:
                                response.message("❌ Error generando la proforma. Intenta nuevamente.")
                                session_manager.clear_session(user_id)

                            return PlainTextResponse(str(response), media_type="application/xml")
                        else:
                            logger.error(f"❌ Error calculando precio con flete ${flete_value:.2f}")
                            response.message("❌ Error procesando la solicitud. Intenta nuevamente.")
                            session_manager.clear_session(user_id)
                            return PlainTextResponse(str(response), media_type="application/xml")
                    else:
                        # Flete no válido
                        product = ai_query.get('product', 'producto')
                        size = ai_query.get('size', 'talla')
                        destination = ai_query.get('destination', 'destino')

                        response.message("🤔 Valor no válido. Por favor responde con el valor del flete:\n\n💡 **Ejemplos:**\n• **0.25** para $0.25/kg\n• **0.30** para $0.30/kg\n• **flete 0.22**\n\nO escribe 'menu' para volver al inicio")
                        return PlainTextResponse(str(response), media_type="application/xml")
                else:
                    response.message("❌ Error: No se encontraron datos de la solicitud. Por favor intenta nuevamente.")
                    session_manager.clear_session(user_id)
                    return PlainTextResponse(str(response), media_type="application/xml")

            except Exception as e:
                logger.error(f"❌ Error procesando respuesta de flete: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                response.message("❌ Error procesando el valor del flete. Intenta nuevamente.")
                session_manager.clear_session(user_id)
                return PlainTextResponse(str(response), media_type="application/xml")

        # Análisis rápido de intención
        ai_analysis = openai_service._basic_intent_analysis(Body)
        logger.info(f"🔍 Análisis básico para {user_id}: {ai_analysis}")
        logger.info(f"🔍 Intent: {ai_analysis.get('intent')}, Confidence: {ai_analysis.get('confidence')}, Product: {ai_analysis.get('product')}, Size: {ai_analysis.get('size')}")

        # Detectar si el mensaje tiene indicadores de cotización (tallas, términos específicos)
        has_size = bool(re.search(r'\b\d+/\d+\b', Body.lower()))
        quote_keywords = ['proforma', 'cotizacion', 'cotizar', 'precio', 'necesito', 'contenedor', 'cfr', 'cif', 'cocedero', 'lagostino', 'inteiro', 'colas']
        has_quote_keywords = any(keyword in Body.lower() for keyword in quote_keywords)
        is_complex_quote = has_size or has_quote_keywords

        # Usar OpenAI para:
        # 1. Casos complejos (baja confianza)
        # 2. Mensajes con tallas o términos de cotización (incluso si tienen saludo)
        # 3. Cualquier mensaje que no sea saludo simple o menú
        should_use_openai = (
            (ai_analysis.get('confidence', 0) < 0.7 or is_complex_quote) and
            ai_analysis.get('intent') not in ['menu_request'] and  # Removido 'greeting' de exclusiones
            openai_service.is_available()
        )

        if should_use_openai:
            logger.info(f"🤖 Usando OpenAI para análisis (complex_quote={is_complex_quote}, confidence={ai_analysis.get('confidence', 0)})")
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

        # Manejar modificación de flete con prioridad (antes de procesar múltiples productos)
        if ai_analysis and ai_analysis.get('intent') == 'modify_flete':
            # Usuario quiere modificar el flete de la última proforma
            last_quote = session_manager.get_last_quote(user_id)

            if last_quote:
                new_flete = ai_analysis.get('flete_custom')

                if new_flete is not None:
                    logger.info(f"🔄 Modificando flete de ${last_quote.get('flete', 0):.2f} a ${new_flete:.2f}")

                    # Recalcular la proforma con el nuevo flete
                    product = last_quote.get('producto')
                    size = last_quote.get('talla')
                    glaseo_factor = last_quote.get('factor_glaseo')
                    glaseo_percentage = last_quote.get('glaseo_percentage')
                    cliente_nombre = last_quote.get('cliente_nombre')
                    destination = last_quote.get('destination')
                    usar_libras = last_quote.get('usar_libras', False)

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
                                price = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(query,))
                                if price:
                                    recalculated.append(price)
                                else:
                                    failed.append(f"{p.get('product', p.get('producto'))} {p.get('size', p.get('talla'))}")
                            except Exception as e:
                                logger.error(f"❌ Error recalculando producto {p}: {e}")
                                failed.append(str(p))

                        if recalculated:
                            new_last = {
                                'consolidated': True,
                                'products_info': recalculated,
                                'glaseo_percentage': last_quote.get('glaseo_percentage'),
                                'failed_products': failed,
                                'flete': new_flete
                            }
                            session_manager.set_last_quote(user_id, new_last)

                            user_language = session_manager.get_user_language(user_id)
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

                    new_price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(modified_query,))

                    if new_price_info:
                        session_manager.set_last_quote(user_id, new_price_info)
                        user_language = session_manager.get_user_language(user_id)
                        logger.info(f"📄 Regenerando PDF con nuevo flete ${new_flete:.2f}")
                        pdf_path = pdf_generator.generate_quote_pdf(new_price_info, From, user_language)

                        if pdf_path:
                            old_flete = last_quote.get('flete', 0)
                            confirmation_msg = "✅ **Proforma actualizada**\n\n"
                            confirmation_msg += "🔄 Flete modificado:\n"
                            confirmation_msg += f"   • Anterior: ${old_flete:.2f}\n"
                            confirmation_msg += f"   • Nuevo: ${new_flete:.2f}\n\n"
                            confirmation_msg += "📄 Generando nueva proforma..."
                            response.message(confirmation_msg)
                            pdf_sent = whatsapp_sender.send_pdf_document(From, pdf_path, f"📄 Proforma actualizada con flete de ${new_flete:.2f}\n\n💼 Documento válido para procesos comerciales.")
                            if pdf_sent:
                                logger.debug(f"✅ PDF actualizado enviado por WhatsApp: {pdf_path}")
                            else:
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

        # DETECTAR MÚLTIPLES TALLAS PRIMERO (simplificado)
        # Si hay 2 o más tallas en el mensaje, generar cotización consolidada
        all_sizes_in_message = re.findall(r'(\d+)/(\d+)', Body)
        
        if len(all_sizes_in_message) >= 2:
            logger.info(f"📋 Detectadas {len(all_sizes_in_message)} tallas en el mensaje → Cotización consolidada")
            
            # Construir lista de tallas
            sizes_list = [f"{s[0]}/{s[1]}" for s in all_sizes_in_message]
            
            # Verificar si el usuario ya especificó el glaseo en el mensaje
            glaseo_factor = ai_analysis.get('glaseo_factor') if ai_analysis else None
            glaseo_percentage = ai_analysis.get('glaseo_percentage') if ai_analysis else None

            logger.info(f"🔍 Glaseo detectado en análisis: factor={glaseo_factor}, percentage={glaseo_percentage}")

            # Detectar glaseo manualmente si no se detectó
            if glaseo_percentage is None or (glaseo_percentage not in [0, 10, 20, 30] and not glaseo_factor):
                message_lower = Body.lower()
                glaseo_patterns = [
                    r'(?:inteiro|entero|colas?|tails?)\s+(\d+)\s*%',  # "Inteiro 0%"
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
                        if glaseo_percentage == 0:
                            glaseo_factor = None  # Sin glaseo
                            logger.info(f"✅ Glaseo 0% detectado manualmente → Sin glaseo")
                        else:
                            glaseo_factor = glaseo_percentage_to_factor(glaseo_percentage)
                            logger.info(f"✅ Glaseo detectado manualmente: {glaseo_percentage}% (factor {glaseo_factor})")
                        break

            # Verificar si el glaseo fue especificado (incluyendo 0%)
            if glaseo_percentage is not None:
                # El usuario ya especificó el glaseo (puede ser 0%, 10%, 20%, 30%)
                logger.info(f"✅ Glaseo detectado en mensaje: {glaseo_percentage}%")
                
                # Detectar producto y destino del mensaje
                destination = ai_analysis.get('destination') if ai_analysis else None
                product = ai_analysis.get('product') if ai_analysis else None
                
                # PRIMERO: Verificar si menciona Inteiro/Colas (tiene prioridad sobre producto detectado)
                message_upper = Body.upper()
                has_inteiro = any(term in message_upper for term in ['INTEIRO', 'ENTERO'])
                has_colas = any(term in message_upper for term in ['COLAS', 'COLA', 'TAILS'])
                
                # Si menciona Inteiro O Colas, solicitar aclaración (ignorar producto detectado)
                if has_inteiro or has_colas:
                    # Ignorar producto detectado, necesita aclaración
                    product = None
                    logger.info("🔍 Detectado Inteiro/Colas → Solicitar aclaración (ignorar producto detectado)")
                    message_upper = Body.upper()
                    has_inteiro = any(term in message_upper for term in ['INTEIRO', 'ENTERO'])
                    has_colas = any(term in message_upper for term in ['COLAS', 'COLA', 'TAILS'])
                    
                    if has_inteiro or has_colas:
                        # Necesita aclaración de productos
                        # Separar tallas por contexto
                        sizes_inteiro = []
                        sizes_colas = []
                        
                        # Buscar tallas cerca de "Inteiro"
                        inteiro_section = re.search(r'(?:inteiro|entero)[^a-z]*?((?:\d+/\d+[^\d]*?)+)', message_upper, re.IGNORECASE)
                        if inteiro_section:
                            sizes_inteiro = re.findall(r'(\d+)/(\d+)', inteiro_section.group(1))
                            sizes_inteiro = [f"{s[0]}/{s[1]}" for s in sizes_inteiro]
                        
                        # Buscar tallas cerca de "Colas"
                        colas_section = re.search(r'(?:colas?|tails?)[^a-z]*?((?:\d+/\d+[^\d]*?)+)', message_upper, re.IGNORECASE)
                        if colas_section:
                            sizes_colas = re.findall(r'(\d+)/(\d+)', colas_section.group(1))
                            sizes_colas = [f"{s[0]}/{s[1]}" for s in sizes_colas]
                        
                        # Si no se pudieron separar, usar todas las tallas
                        if not sizes_inteiro and not sizes_colas:
                            sizes_inteiro = sizes_list[:len(sizes_list)//2] if len(sizes_list) > 1 else []
                            sizes_colas = sizes_list[len(sizes_list)//2:] if len(sizes_list) > 1 else sizes_list
                        
                        logger.info(f"📏 Tallas Inteiro: {sizes_inteiro}")
                        logger.info(f"📏 Tallas Colas: {sizes_colas}")
                        
                        # Solicitar aclaración
                        clarification_message = "🦐 **Solicitud detectada:**\n\n"
                        if sizes_inteiro:
                            clarification_message += f"📏 **Inteiro (Entero):** {', '.join(sizes_inteiro)}\n"
                        if sizes_colas:
                            clarification_message += f"📏 **Colas:** {', '.join(sizes_colas)}\n"
                        if destination:
                            clarification_message += f"🌍 **Destino:** {destination}\n"
                        if glaseo_percentage is not None:
                            clarification_message += f"❄️ **Glaseo:** {glaseo_percentage}%\n"
                        
                        clarification_message += "\n💡 **¿Qué productos necesitas?**\n\n"
                        if sizes_inteiro:
                            clarification_message += "**Para Inteiro (Entero):**\n• HOSO - Camarón entero (con cabeza)\n• HLSO - Sin cabeza\n\n"
                        if sizes_colas:
                            clarification_message += "**Para Colas:**\n• COOKED - Colas cocidas\n• P&D IQF - Colas peladas crudas\n\n"
                        clarification_message += "📝 **Ejemplo:** 'HOSO para inteiro y COOKED para colas'"
                        
                        response.message(clarification_message)
                        
                        # Guardar estado
                        session_manager.set_session_state(user_id, 'waiting_for_product_clarification', {
                            'sizes_inteiro': sizes_inteiro,
                            'sizes_colas': sizes_colas,
                            'destination': destination,
                            'glaseo_percentage': glaseo_percentage,
                            'flete_solicitado': True
                        })
                        
                        return PlainTextResponse(str(response), media_type="application/xml")
                
                # Si hay producto, construir lista de productos y solicitar flete directamente
                if product:
                    multiple_products = [{'product': product, 'size': size} for size in sizes_list]
                    logger.info(f"📋 Construidos {len(multiple_products)} productos con {product}")
                    
                    # SOLICITAR FLETE DIRECTAMENTE (sin calcular precios aún)
                    destination = ai_analysis.get('destination') if ai_analysis else None
                    
                    products_list = "\n".join([f"   {i+1}. {product} {size}" for i, size in enumerate(sizes_list, 1)])
                    
                    flete_message = f"""✅ **Productos confirmados: {len(multiple_products)} tallas**

{products_list}

🌍 **Destino:** {destination}
❄️ **Glaseo:** {glaseo_percentage}%

🚢 **Para calcular el precio CFR necesito el valor del flete a {destination}:**

💡 **Ejemplos:**
• "flete 0.20"
• "0.25 de flete"
• "con flete de 0.22"

¿Cuál es el valor del flete por kilo? 💰"""
                    
                    response.message(flete_message)
                    
                    # Guardar estado para esperar respuesta de flete
                    session_manager.set_session_state(user_id, 'waiting_for_multi_flete', {
                        'products': multiple_products,
                        'glaseo_factor': glaseo_factor,
                        'glaseo_percentage': glaseo_percentage,
                        'destination': destination
                    })
                    
                    return PlainTextResponse(str(response), media_type="application/xml")
                else:
                    # Solicitar producto
                    response.message(f"🦐 Detecté {len(sizes_list)} tallas: {', '.join(sizes_list)}\n\n¿Qué producto necesitas?\n\nEjemplo: 'HLSO' o 'HOSO' o 'COOKED'")
                    return PlainTextResponse(str(response), media_type="application/xml")
            else:
                # No especificó glaseo, pedirlo
                response.message(f"🦐 Detecté {len(sizes_list)} tallas: {', '.join(sizes_list)}\n\n❄️ ¿Qué glaseo necesitas?\n• 0% (sin glaseo)\n• 10%\n• 20%\n• 30%")
                return PlainTextResponse(str(response), media_type="application/xml")
        
        # Si no hay múltiples tallas, intentar detección normal
        multiple_products = openai_service.detect_multiple_products(Body)

        if multiple_products and len(multiple_products) > 1:
            logger.info(f"📋 Detectados {len(multiple_products)} productos en el mensaje")

            # Verificar si el usuario ya especificó el glaseo en el mensaje
            glaseo_factor = ai_analysis.get('glaseo_factor') if ai_analysis else None
            glaseo_percentage = ai_analysis.get('glaseo_percentage') if ai_analysis else None

            logger.info(f"🔍 Glaseo detectado en análisis: factor={glaseo_factor}, percentage={glaseo_percentage}")
            logger.info(f"🔍 Mensaje completo: {Body}")

            # Si no se detectó glaseo en el análisis, o si el glaseo detectado no es válido (0, 10, 20, 30), intentar detectarlo manualmente
            # IMPORTANTE: 0% es válido (sin glaseo)
            if glaseo_percentage is None or (glaseo_percentage not in [0, 10, 20, 30] and not glaseo_factor):
                message_lower = Body.lower()
                glaseo_patterns = [
                    r'(?:inteiro|entero|colas?|tails?)\s+(\d+)\s*%',  # "Inteiro 0%"
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
                        if glaseo_percentage == 0:
                            glaseo_factor = None  # Sin glaseo
                            logger.info(f"✅ Glaseo 0% detectado manualmente → Sin glaseo")
                        else:
                            glaseo_factor = glaseo_percentage_to_factor(glaseo_percentage)
                            logger.info(f"✅ Glaseo detectado manualmente: {glaseo_percentage}% (factor {glaseo_factor})")
                        break

            # Verificar si el glaseo fue especificado (incluyendo 0%)
            if glaseo_percentage is not None:
                # El usuario ya especificó el glaseo (puede ser 0%, 10%, 20%, 30%)
                logger.info(f"✅ Glaseo detectado en mensaje: {glaseo_percentage}%")

                # Verificar si menciona DDP y si especificó el flete
                is_ddp = ai_analysis.get('is_ddp', False) if ai_analysis else False
                flete_custom = ai_analysis.get('flete_custom') if ai_analysis else None

                # Si es DDP sin flete, pedir el flete antes de continuar
                if is_ddp and flete_custom is None:
                    logger.info(f"📦 DDP detectado sin flete - pidiendo valor de flete para {len(multiple_products)} productos")

                    # Mostrar lista de productos detectados
                    products_list = "\n".join([f"   {i+1}. {p['product']} {p['size']}"
                                              for i, p in enumerate(multiple_products)])

                    ddp_flete_message = f"""📦 **Detecté precio DDP para {len(multiple_products)} productos:**

{products_list}

❄️ Glaseo: {glaseo_percentage}%

🚢 **Para calcular el precio DDP necesito el valor del flete:**

💡 **Ejemplos:**
• "flete 0.25"
• "0.30 de flete"
• "con flete de 0.22"

¿Cuál es el valor del flete por kilo? 💰"""

                    response.message(ddp_flete_message)

                    # Guardar estado para esperar respuesta de flete
                    session_manager.set_session_state(user_id, 'waiting_for_multi_flete', {
                        'products': multiple_products,
                        'glaseo_factor': glaseo_factor,
                        'glaseo_percentage': glaseo_percentage,
                        'is_ddp': is_ddp
                    })

                    return PlainTextResponse(str(response), media_type="application/xml")

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
                            # Incluir flete si se especificó
                            'flete_custom': flete_custom,
                            'flete_solicitado': True if flete_custom is not None else False,
                            'custom_calculation': True
                        }

                        price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(query,))

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
                        summary += "⚠️ No se encontraron precios para:\n"
                        for fp in failed_products:
                            summary += f"   • {fp}\n"
                        summary += "\n"

                    summary += "🌐 **Selecciona el idioma para la cotización consolidada:**\n\n"
                    summary += "1️⃣ Español 🇪🇸\n"
                    summary += "2️⃣ English 🇺🇸\n\n"
                    summary += "Responde con el número o escribe:\n"
                    summary += "• \"español\" o \"spanish\"\n"
                    summary += "• \"inglés\" o \"english\""

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

            # PRIMERO: Verificar si necesita aclaración sobre tipo de producto (Cocedero + Inteiro/Colas)
            if ai_analysis.get('needs_product_type') or ai_analysis.get('multiple_presentations'):
                clarification = ai_analysis.get('clarification_needed', '')
                sizes_inteiro = ai_analysis.get('sizes_inteiro', [])
                sizes_colas = ai_analysis.get('sizes_colas', [])
                destination = ai_analysis.get('destination', '')
                glaseo_percentage = ai_analysis.get('glaseo_percentage')
                
                clarification_message = "🦐 **Solicitud detectada:**\n\n"
                
                if sizes_inteiro:
                    clarification_message += f"📏 **Inteiro (Entero):** {', '.join(sizes_inteiro)}\n"
                if sizes_colas:
                    clarification_message += f"📏 **Colas:** {', '.join(sizes_colas)}\n"
                if destination:
                    clarification_message += f"🌍 **Destino:** {destination}\n"
                if glaseo_percentage is not None:
                    clarification_message += f"❄️ **Glaseo:** {glaseo_percentage}%\n"
                
                clarification_message += "\n⚠️ **Necesito aclaración:**\n"
                clarification_message += "Mencionas 'Cocedero' (cocido) pero también 'Inteiro' (entero).\n\n"
                clarification_message += "💡 **¿Qué productos necesitas?**\n\n"
                clarification_message += "**Para Inteiro (Entero):**\n"
                clarification_message += "• HOSO - Camarón entero crudo (con cabeza)\n"
                clarification_message += "• HLSO - Sin cabeza crudo\n\n"
                clarification_message += "**Para Colas (Cocidas):**\n"
                clarification_message += "• COOKED - Colas cocidas\n"
                clarification_message += "• PRE-COCIDO - Pre-cocidas\n"
                clarification_message += "• COCIDO SIN TRATAR - Cocidas sin tratamiento\n\n"
                clarification_message += "📝 **Por favor especifica:**\n"
                clarification_message += "Ejemplo: 'HOSO para inteiro y COOKED para colas'"
                
                # Guardar estado para procesar la respuesta del usuario
                session_manager.set_session_state(user_id, 'waiting_for_product_clarification', {
                    'sizes_inteiro': sizes_inteiro,
                    'sizes_colas': sizes_colas,
                    'destination': destination,
                    'glaseo_percentage': glaseo_percentage,
                    'flete_solicitado': True  # CFR siempre solicita flete
                })
                
                response.message(clarification_message)
                return PlainTextResponse(str(response), media_type="application/xml")
            
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
                price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(ai_query,))

                if price_info:
                    logger.debug(f"✅ Datos de proforma validados para: {ai_query}")

                    # Detectar idioma automáticamente y generar PDF
                    user_lang = detect_language(Body, ai_analysis)
                    session_manager.set_last_quote(user_id, price_info)
                    session_manager.set_user_language(user_id, user_lang)

                    product_name = price_info.get('producto', 'Camarón')
                    size = price_info.get('talla', '')

                    logger.info(f"📄 Generando PDF automáticamente en idioma {user_lang} para usuario {user_id}")
                    pdf_path = pdf_generator.generate_quote_pdf(price_info, From, user_lang)

                    if pdf_path:
                        pdf_sent = whatsapp_sender.send_pdf_document(
                            From,
                            pdf_path,
                            f"Cotización BGR Export - {product_name} {size}"
                        )
                        if pdf_sent:
                            response.message(f"✅ Proforma generada y enviada en {'Español' if user_lang == 'es' else 'English'} 🇪🇸🇺🇸")
                        else:
                            filename = os.path.basename(pdf_path)
                            base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                            download_url = f"{base_url}/webhook/download-pdf/{filename}"
                            pdf_message = response.message()
                            pdf_message.body(f"✅ Proforma generada. Descarga: {download_url}")
                    else:
                        response.message("❌ Error generando la proforma. Intenta nuevamente.")

                    return PlainTextResponse(str(response), media_type="application/xml")
                else:
                    # Verificar qué información falta específicamente
                    glaseo_factor = ai_query.get('glaseo_factor') if ai_query else None
                    glaseo_percentage = ai_query.get('glaseo_percentage') if ai_query else None
                    flete_solicitado = ai_query.get('flete_solicitado', False) if ai_query else False
                    flete_custom = ai_query.get('flete_custom') if ai_query else None
                    destination = ai_query.get('destination') if ai_query else None

                    logger.info(f"🔍 Verificando datos faltantes: glaseo_factor={glaseo_factor}, glaseo_percentage={glaseo_percentage}, flete_solicitado={flete_solicitado}, flete_custom={flete_custom}, destination={destination}")

                    # IMPORTANTE: Si glaseo_percentage es 0, significa "sin glaseo" (ya especificado)
                    # No pedir glaseo en este caso
                    if glaseo_factor is None and glaseo_percentage != 0:
                        # Falta el glaseo - pedir al usuario que lo especifique
                        product = ai_query.get('product', 'producto') if ai_query else 'producto'
                        size = ai_query.get('size', 'talla') if ai_query else 'talla'

                        logger.info(f"❄️ Pidiendo glaseo para {product} {size}")

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
                        logger.info("✅ Mensaje de glaseo agregado a la respuesta")

                        # Guardar el estado para esperar la respuesta del glaseo
                        session_manager.set_session_state(user_id, 'waiting_for_glaseo', {
                            'ai_query': ai_query
                        })

                        return PlainTextResponse(str(response), media_type="application/xml")
                    elif flete_solicitado and flete_custom is None:
                        # Usuario solicitó flete pero no especificó valor y tampoco está en Sheets
                        product = ai_query.get('product', 'producto') if ai_query else 'producto'
                        size = ai_query.get('size', 'talla') if ai_query else 'talla'

                        logger.info(f"🚢 Pidiendo valor de flete para {product} {size} con destino {destination}")

                        flete_message = f"""🚢 **Para calcular el precio con flete a {destination or 'destino'} necesito el valor del flete:**

💡 **Ejemplos:**
• "flete 0.25"
• "0.30 de flete"
• "con flete de 0.22"

¿Cuál es el valor del flete por kilo? 💰"""

                        response.message(flete_message)
                        logger.info("✅ Mensaje de flete agregado a la respuesta")

                        # Guardar el estado para esperar la respuesta del flete
                        session_manager.set_session_state(user_id, 'waiting_for_flete', {
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
                                price = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(query,))
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
                    new_price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(modified_query,))

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
                            confirmation_msg = "✅ **Proforma actualizada**\n\n"
                            confirmation_msg += "🔄 Flete modificado:\n"
                            confirmation_msg += f"   • Anterior: ${old_flete:.2f}\n"
                            confirmation_msg += f"   • Nuevo: ${new_flete:.2f}\n\n"
                            confirmation_msg += "📄 Generando nueva proforma..."

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

                            flete_msg = "💡 *Información del flete:*\n"
                            flete_msg += f"La cotización se basó con flete de ${flete_value:.2f}"
                            if destination:
                                flete_msg += f" hacia {destination}"
                            flete_msg += "\n\n📋 Precio CFR incluye: Producto + Glaseo + Flete"

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

                # Convertir porcentaje a factor usando función helper
                if glaseo_percentage:
                    glaseo_factor = glaseo_percentage_to_factor(glaseo_percentage)

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
                                # NO aplicar flete por defecto - solo si el usuario lo especifica
                                'custom_calculation': True
                            }

                            price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(query,))

                            if price_info:
                                products_info.append(price_info)
                            else:
                                failed_products.append(f"{product_data['product']} {product_data['size']}")
                        except Exception as e:
                            logger.error(f"❌ Error calculando precio para {product_data['product']} {product_data['size']}: {str(e)}")
                            failed_products.append(f"{product_data['product']} {product_data['size']}")

                    if products_info:
                        # Guardar como última cotización consolidada y generar PDF automáticamente
                        user_lang = detect_language(Body, ai_analysis)
                        last = {
                            'consolidated': True,
                            'products_info': products_info,
                            'glaseo_percentage': glaseo_percentage,
                            'failed_products': failed_products
                            # NO incluir flete por defecto
                        }
                        session_manager.set_last_quote(user_id, last)
                        session_manager.set_user_language(user_id, user_lang)

                        logger.info(f"📄 Generando PDF consolidado automáticamente en idioma {user_lang} para usuario {user_id}")
                        pdf_path = pdf_generator.generate_consolidated_quote_pdf(
                            products_info,
                            From,
                            user_lang,
                            glaseo_percentage,
                            destination=None
                        )

                        if pdf_path:
                            pdf_sent = whatsapp_sender.send_pdf_document(
                                From,
                                pdf_path,
                                f"Cotización Consolidada BGR Export - {len(products_info)} productos"
                            )
                            if pdf_sent:
                                response.message(f"✅ Cotización consolidada generada y enviada en {'Español' if user_lang == 'es' else 'English'} - {len(products_info)} productos")
                            else:
                                filename = os.path.basename(pdf_path)
                                base_url = os.getenv('BASE_URL', 'https://bgr-shrimp.onrender.com')
                                download_url = f"{base_url}/webhook/download-pdf/{filename}"
                                response.message(f"✅ Cotización generada\n📄 Descarga: {download_url}")
                        else:
                            response.message("❌ Error generando PDF consolidado. Intenta nuevamente.")
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

                            confirmation = "✅ **Cotización consolidada generada**\n\n"
                            confirmation += f"🌐 Idioma: {lang_name}\n"
                            confirmation += f"📦 Productos: {len(products_info)}\n"
                            confirmation += f"❄️ Glaseo: {glaseo_percentage}%\n"

                            if failed_products:
                                confirmation += f"\n⚠️ {len(failed_products)} producto(s) sin precio disponible\n"

                            confirmation += "\n📄 **PDF enviado por WhatsApp**"

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
                    glaseo_percentage = price_info.get('glaseo_percentage')
                    
                    # IMPORTANTE: Si glaseo_percentage es 0, significa "sin glaseo" (ya especificado)
                    # No pedir glaseo en este caso
                    if not glaseo_factor and glaseo_percentage != 0:
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
                    logger.info("🔍 ROUTES - Datos antes de generar PDF:")
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

                            confirmation_msg = "✅ **Proforma generada y enviada**\n\n"
                            confirmation_msg += f"🌐 Idioma: {lang_name}\n"
                            confirmation_msg += f"🦐 {price_info.get('producto', 'Producto')}: {price_info.get('talla', '')}\n"

                            if price_info.get('cliente_nombre'):
                                confirmation_msg += f"👤 Cliente: {price_info['cliente_nombre'].title()}\n"

                            if price_info.get('destination'):
                                confirmation_msg += f"🌍 Destino: {price_info['destination']}\n"

                            # Línea del precio FOB eliminada según solicitud del usuario
                            # if price_info.get('precio_final_kg'):
                            #     confirmation_msg += f"💰 Precio FOB: ${price_info['precio_final_kg']:.2f}/kg - ${price_info.get('precio_final_lb', 0):.2f}/lb\n"

                            confirmation_msg += "\n📄 **PDF enviado por WhatsApp**"

                            response.message(confirmation_msg)

                            # Mensaje adicional sobre el flete si es CFR
                            if price_info.get('incluye_flete') and price_info.get('flete'):
                                flete_value = price_info['flete']
                                destination = price_info.get('destination', '')

                                flete_msg = "💡 *Información del flete:*\n"
                                flete_msg += f"La cotización se basó con flete de ${flete_value:.2f}"
                                if destination:
                                    flete_msg += f" hacia {destination}"
                                flete_msg += "\n\n📋 Precio CFR incluye: Producto + Glaseo + Flete"
                                flete_msg += "\n\n🔄 *¿Necesitas cambiar el flete?*"
                                flete_msg += "\nEscribe: 'modifica el flete a [valor]'"
                                flete_msg += "\nEjemplo: 'modifica el flete a 0.30'"

                                response.message(flete_msg)
                        else:
                            logger.error("❌ Error enviando PDF por WhatsApp")
                            response.message(f"✅ Proforma generada\n📄 Descarga tu PDF: {download_url}")
                    else:
                        logger.error("❌ Error generando PDF")
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

                price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(user_input,))

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
            price_info = retry(pricing_service.get_shrimp_price, retries=3, delay=0.5, args=(user_input,))

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
            logger.debug("📤 Respuesta configurada en objeto response")
            # Mantener en estado conversacional sin menú numerado
            session_manager.set_session_state(user_id, 'conversational', {})
            logger.debug("🔄 Estado actualizado a conversational")
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


@whatsapp_router.get("/whatsapp")
async def whatsapp_webhook_verification(request: Request):
    """
    Verificación del webhook de Twilio
    """
    return {"status": "webhook_ready"}