from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from app.services.pricing import PricingService
from app.services.utils import parse_user_message, format_price_response
from app.services.interactive import InteractiveMessageService
from app.services.session import session_manager
from app.services.pdf_generator import PDFGenerator
from app.services.whatsapp_sender import WhatsAppSender
from app.services.openai_service import OpenAIService
import logging
import os

logger = logging.getLogger(__name__)

webhook_router = APIRouter()

# Servicios se inicializarán de manera lazy
pricing_service = None
interactive_service = None
pdf_generator = None
openai_service = None
whatsapp_sender = None

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
        logger.info("✅ Servicios inicializados")
    
    return pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service

@webhook_router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    MessageSid: str = Form(...)
):
    """
    Endpoint para recibir mensajes de WhatsApp desde Twilio
    """
    try:
        logger.info(f"Mensaje recibido de {From}: {Body}")
        
        # Inicializar servicios si no están inicializados
        pricing_service, interactive_service, pdf_generator, whatsapp_sender, openai_service = get_services()
        
        # Crear respuesta de Twilio
        response = MessagingResponse()
        
        # Obtener sesión del usuario
        user_id = From.replace("whatsapp:", "")
        session = session_manager.get_session(user_id)
        
        # Análisis de intención con OpenAI (si está disponible)
        ai_analysis = None
        if openai_service.is_available():
            ai_analysis = openai_service.analyze_user_intent(Body, session)
            logger.info(f"🤖 Análisis IA para {user_id}: {ai_analysis}")
        
        # Comandos globales que funcionan desde cualquier estado
        message_lower = Body.lower().strip()
        
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
            # Generar y enviar PDF con la última cotización
            last_quote = session_manager.get_last_quote(user_id)
            
            if last_quote:
                logger.info(f"Generando PDF para usuario {user_id}")
                pdf_path = pdf_generator.generate_quote_pdf(last_quote, From)
                
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
                        logger.info(f"✅ PDF enviado exitosamente por WhatsApp: {pdf_path}")
                    else:
                        # Si no se pudo enviar por WhatsApp, usar TwiML como respaldo
                        logger.info(f"⚠️ Enviando PDF via TwiML como respaldo: {download_url}")
                        
                        # Enviar mensaje con el PDF como archivo adjunto usando TwiML
                        pdf_message = response.message()
                        pdf_message.body("📄 Aquí tienes tu cotización oficial de BGR Export.\n\n💼 Documento válido para procesos comerciales.\n\n📞 Para cualquier consulta, contáctanos.")
                        pdf_message.media(download_url)
                        
                        # También enviar enlace de descarga como respaldo
                        #response.message(f"📎 También puedes descargar el PDF desde:\n{download_url}")
                    
                    # Limpiar la cotización después de confirmar
                    session_manager.clear_session(user_id)
                else:
                    response.message("❌ Error generando el PDF. Por favor intenta nuevamente o contacta soporte.")
            else:
                response.message("❌ No hay cotización pendiente para confirmar.\n\n💡 Primero solicita una cotización de precios y luego escribe 'confirmar'.")
            
            response_xml = str(response)
            logger.info(f"Enviando respuesta de confirmación XML: {response_xml}")
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
            
            # Intentar parsear como consulta de precio directa
            user_input = parse_user_message(Body)
            logger.info(f"🔍 Parse result para '{Body}': {user_input}")
            
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
            
            # Si no es una consulta válida, intentar respuesta inteligente
            logger.info(f"🔍 Llegando a lógica de respuesta inteligente para mensaje: '{Body}'")
            smart_response = None
            
            # Intentar respuesta con OpenAI primero
            if openai_service.is_available() and ai_analysis and ai_analysis.get('confidence', 0) > 0.7:
                logger.info(f"🤖 Intentando respuesta OpenAI para confianza: {ai_analysis.get('confidence', 0)}")
                smart_response = openai_service.generate_smart_response(Body, session)
                logger.info(f"🤖 Respuesta OpenAI obtenida: {smart_response}")
            
            # Si OpenAI no está disponible o falló, usar fallback inteligente
            if not smart_response and ai_analysis and ai_analysis.get('confidence', 0) > 0.5:
                logger.info(f"🧠 Usando fallback inteligente para confianza: {ai_analysis.get('confidence', 0)}")
                smart_response = openai_service.get_smart_fallback_response(Body, ai_analysis)
                logger.info(f"🧠 Respuesta fallback obtenida: {smart_response}")
            
            if smart_response:
                # Usar respuesta inteligente (IA o fallback)
                logger.info(f"✅ Usando respuesta inteligente: {smart_response}")
                response.message(smart_response)
                logger.info(f"📤 Respuesta configurada en objeto response")
                # Mantener en menú principal para seguir la conversación
                menu_msg, options = interactive_service.create_main_menu()
                session_manager.set_session_state(user_id, 'main_menu', {'options': options})
                logger.info(f"🔄 Estado actualizado a main_menu")
            else:
                # Fallback final al menú de bienvenida tradicional
                logger.info("⚠️ No hay respuesta inteligente, usando menú tradicional")
                welcome_msg = interactive_service.create_welcome_message()
                menu_msg, options = interactive_service.create_main_menu()
                full_message = f"{welcome_msg}\n\n{menu_msg}"
                response.message(full_message)
                session_manager.set_session_state(user_id, 'main_menu', {'options': options})
        
        response_xml = str(response)
        logger.info(f"Enviando respuesta XML: {response_xml}")
        return PlainTextResponse(response_xml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        response = MessagingResponse()
        response.message("❌ Ocurrió un error procesando tu consulta. Intenta nuevamente.")
        response_xml = str(response)
        logger.info(f"Enviando respuesta de error XML: {response_xml}")
        return PlainTextResponse(response_xml, media_type="application/xml")

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
async def reload_data():
    """
    Endpoint para recargar datos desde Google Sheets
    """
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
async def data_status():
    """
    Endpoint para verificar el estado de los datos
    """
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
async def test_twilio():
    """
    Endpoint para probar las credenciales de Twilio
    """
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
        
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
async def test_pdf_send(phone_number: str = Form(...)):
    """
    Endpoint para probar el envío de PDFs
    """
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
        
        if os.path.exists(pdf_path):
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
            raise HTTPException(status_code=404, detail="PDF no encontrado")
            
    except Exception as e:
        logger.error(f"Error descargando PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")