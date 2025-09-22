from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from app.services.pricing import PricingService
from app.services.utils import parse_user_message, format_price_response
from app.services.interactive import InteractiveMessageService
from app.services.session import session_manager
import logging

logger = logging.getLogger(__name__)

webhook_router = APIRouter()
pricing_service = PricingService()
interactive_service = InteractiveMessageService()

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
            return PlainTextResponse(str(response), media_type="application/xml")
        
        elif message_lower in ['menu', 'inicio', 'start', 'hola', 'hello', 'reiniciar', 'reset']:
            # Limpiar sesión y mostrar menú principal
            session_manager.clear_session(user_id)
            welcome_msg = interactive_service.create_welcome_message()
            menu_msg, options = interactive_service.create_main_menu()
            full_message = f"{welcome_msg}\n\n{menu_msg}"
            response.message(full_message)
            session_manager.set_session_state(user_id, 'main_menu', {'options': options})
            return PlainTextResponse(str(response), media_type="application/xml")
        
        # Procesar según el estado de la sesión
        logger.info(f"Estado actual del usuario: {session['state']}")
        logger.info(f"Datos de sesión: {session['data']}")
        
        if session['state'] == 'main_menu':
            # Usuario está en el menú principal
            new_state, message, options = interactive_service.handle_menu_selection(Body, "main")
            logger.info(f"Transición de main_menu: {session['state']} -> {new_state}")
            
            if new_state != 'main_menu':  # Solo si cambió de estado
                response.message(message)
                session_manager.set_session_state(user_id, new_state, {'options': options})
                logger.info(f"Mensaje enviado: {message[:50]}...")
            else:
                error_msg = "🤔 Opción no válida. Por favor selecciona:\n\n1️⃣ Soy cliente\n2️⃣ No soy cliente\n\n💡 O escribe 'menu' para reiniciar"
                response.message(error_msg)
                logger.info(f"Opción inválida en main_menu: {Body}")
            return PlainTextResponse(str(response), media_type="application/xml")
        
        elif session['state'] == 'client_menu':
            # Usuario está en el menú de cliente
            new_state, message, options = interactive_service.handle_menu_selection(Body, "client_menu")
            
            if new_state != 'client_menu':  # Solo si cambió de estado
                response.message(message)
                session_manager.set_session_state(user_id, new_state, {})
            else:
                response.message("🤔 Opción no válida. Por favor selecciona:\n\n1️⃣ Consulta\n2️⃣ Pedidos\n3️⃣ Reclamación\n\n💡 O escribe 'menu' para volver al inicio")
            return PlainTextResponse(str(response), media_type="application/xml")
        
        elif session['state'] == 'non_client_menu':
            # Usuario está en el menú de no cliente
            new_state, message, options = interactive_service.handle_menu_selection(Body, "non_client_menu")
            
            if new_state != 'non_client_menu':  # Solo si cambió de estado
                response.message(message)
                
                if new_state == 'pricing':
                    # Si seleccionó precios, configurar para selección de tallas
                    session_manager.set_session_state(user_id, 'waiting_for_size_selection', {
                        'available_sizes': options
                    })
                else:
                    session_manager.set_session_state(user_id, new_state, {})
            else:
                response.message("🤔 Opción no válida. Por favor selecciona:\n\n1️⃣ Información de productos\n2️⃣ Precios\n3️⃣ Contacto comercial\n\n💡 O escribe 'menu' para volver al inicio")
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
                    response.message(formatted_response)
                    logger.info(f"Precio encontrado y enviado: {formatted_response[:100]}...")
                else:
                    error_msg = f"❌ No encontré información para {selected_product} talla {selected_size}"
                    response.message(error_msg)
                    logger.info(f"Precio no encontrado: {error_msg}")
                
                # Limpiar sesión
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
                               "• `tallas` - 📏 Ver tallas disponibles\n"
                               "• `productos` - 🏷️ Ver productos disponibles\n"
                               "• `precio HLSO 16/20` - 🔍 Consulta directa\n\n"
                               "💡 **Ejemplos de consultas:**\n"
                               "• Precio HLSO 16/20 para 15000 lb destino China\n"
                               "• P&D IQF 21/25\n"
                               "• EZ PEEL 26/30\n\n"
                               "🌊 ¡Estoy aquí para ayudarte!")
                return PlainTextResponse(str(response), media_type="application/xml")
            
            # Intentar parsear como consulta de precio directa
            user_input = parse_user_message(Body)
            
            if user_input:
                # Obtener precio del camarón
                price_info = pricing_service.get_shrimp_price(user_input)
                
                if price_info:
                    formatted_response = format_price_response(price_info)
                    response.message(formatted_response)
                    session_manager.clear_session(user_id)
                    return PlainTextResponse(str(response), media_type="application/xml")
            
            # Si no es una consulta válida, mostrar menú de bienvenida
            welcome_msg = interactive_service.create_welcome_message()
            menu_msg, options = interactive_service.create_main_menu()
            full_message = f"{welcome_msg}\n\n{menu_msg}"
            response.message(full_message)
            session_manager.set_session_state(user_id, 'main_menu', {'options': options})
        
        return PlainTextResponse(str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}")
        response = MessagingResponse()
        response.message("❌ Ocurrió un error procesando tu consulta. Intenta nuevamente.")
        return PlainTextResponse(str(response), media_type="application/xml")

@webhook_router.get("/whatsapp")
async def whatsapp_webhook_verification(request: Request):
    """
    Verificación del webhook de Twilio
    """
    return {"status": "webhook_ready"}