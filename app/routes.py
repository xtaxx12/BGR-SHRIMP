from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from app.services.pricing import PricingService
from app.services.utils import parse_user_message, format_price_response
from app.services.interactive import InteractiveMessageService
from app.services.session import session_manager
from app.services.pdf_generator import PDFGenerator
import logging

logger = logging.getLogger(__name__)

webhook_router = APIRouter()
pricing_service = PricingService()
interactive_service = InteractiveMessageService()
pdf_generator = PDFGenerator()

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
        
        # Crear respuesta de Twilio
        response = MessagingResponse()
        
        # Obtener sesión del usuario
        user_id = From.replace("whatsapp:", "")
        session = session_manager.get_session(user_id)
        
        # Comandos globales que funcionan desde cualquier estado
        message_lower = Body.lower().strip()
        
        if message_lower in ['precios', 'precio', 'prices']:
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
            # Generar PDF con la última cotización
            last_quote = session_manager.get_last_quote(user_id)
            
            if last_quote:
                logger.info(f"Generando PDF para usuario {user_id}")
                pdf_path = pdf_generator.generate_quote_pdf(last_quote, From)
                
                if pdf_path:
                    response.message("✅ ¡Cotización confirmada!\n\n📄 Se ha generado tu cotización en PDF.\n\n📧 El documento será enviado a tu email registrado.\n\n💡 Escribe 'menu' para realizar otra consulta.")
                    
                    # Limpiar la cotización después de confirmar
                    session_manager.clear_session(user_id)
                    
                    logger.info(f"✅ PDF generado exitosamente: {pdf_path}")
                else:
                    response.message("❌ Error generando el PDF. Por favor intenta nuevamente o contacta soporte.")
            else:
                response.message("❌ No hay cotización pendiente para confirmar.\n\n💡 Primero solicita una cotización de precios y luego escribe 'confirmar'.")
            
            response_xml = str(response)
            logger.info(f"Enviando respuesta de confirmación XML: {response_xml}")
            return PlainTextResponse(response_xml, media_type="application/xml")
        
        elif message_lower in ['menu', 'inicio', 'start', 'hola', 'hello', 'reiniciar', 'reset']:
            # Limpiar sesión y mostrar menú principal
            session_manager.clear_session(user_id)
            welcome_msg = interactive_service.create_welcome_message()
            menu_msg, options = interactive_service.create_main_menu()
            full_message = f"{welcome_msg}\n\n{menu_msg}"
            response.message(full_message)
            session_manager.set_session_state(user_id, 'main_menu', {'options': options})
            response_xml = str(response)
            
            return PlainTextResponse(response_xml, media_type="application/xml")
        
        # Procesar según el estado de la sesión
        logger.info(f"Estado actual del usuario: {session['state']}")
        logger.info(f"Datos de sesión: {session['data']}")
        
        if session['state'] == 'main_menu':
            # Usuario está en el menú principal simplificado
            new_state, message, options = interactive_service.handle_menu_selection(Body, "main")
            logger.info(f"Transición de main_menu: {session['state']} -> {new_state}")
            
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
            logger.info(f"Productos disponibles: {available_products}")
            logger.info(f"Usuario seleccionó: {Body}")
            
            selected_product = interactive_service.parse_selection_response(Body, available_products)
            logger.info(f"Producto parseado: {selected_product}")
            
            if selected_product:
                # Producto seleccionado, obtener precio
                selected_size = session['data'].get('selected_size')
                logger.info(f"Consultando precio para {selected_product} talla {selected_size}")
                
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
                    logger.info(f"Precio encontrado y enviado: {formatted_response[:100]}...")
                    
                    # Almacenar cotización para posible confirmación
                    session_manager.set_last_quote(user_id, price_info)
                    session_manager.set_session_state(user_id, 'quote_ready', {})
                else:
                    error_msg = f"❌ No encontré información para {selected_product} talla {selected_size}"
                    response.message(error_msg)
                    logger.info(f"Precio no encontrado: {error_msg}")
                    session_manager.clear_session(user_id)
            else:
                error_msg = "🤔 Selección inválida. Por favor responde con:\n\n📝 El número de la opción\n💡 O escribe 'menu' para volver al inicio"
                response.message(error_msg)
                logger.info(f"Selección inválida, enviando: {error_msg}")
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
            
            # Si no es una consulta válida, mostrar menú de bienvenida
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
    response.message(f"Recibido: {Body}")
    
    response_xml = str(response)
    logger.info(f"SIMPLE: Enviando XML: {response_xml}")
    
    return PlainTextResponse(response_xml, media_type="application/xml")

@webhook_router.post("/reload-data")
async def reload_data():
    """
    Endpoint para recargar datos desde Google Sheets
    """
    try:
        success = pricing_service.excel_service.reload_data()
        if success:
            return {"status": "success", "message": "Datos recargados desde Google Sheets"}
        else:
            return {"status": "error", "message": "Error recargando datos"}
    except Exception as e:
        logger.error(f"Error recargando datos: {str(e)}")
        return {"status": "error", "message": str(e)}

@webhook_router.get("/download-pdf/{filename}")
async def download_pdf(filename: str):
    """
    Endpoint para descargar PDFs generados
    """
    try:
        import os
        from fastapi.responses import FileResponse
        
        pdf_path = os.path.join("generated_pdfs", filename)
        
        if os.path.exists(pdf_path):
            return FileResponse(
                path=pdf_path,
                filename=filename,
                media_type='application/pdf'
            )
        else:
            raise HTTPException(status_code=404, detail="PDF no encontrado")
            
    except Exception as e:
        logger.error(f"Error descargando PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")