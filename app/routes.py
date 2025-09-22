from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from twilio.twiml.messaging_response import MessagingResponse
from app.services.pricing import PricingService
from app.services.utils import parse_user_message, format_price_response
from app.services.interactive import InteractiveMessageService
from app.services.session import session_manager
import logging
import json
import requests
import os

logger = logging.getLogger(__name__)

webhook_router = APIRouter()
pricing_service = PricingService()
interactive_service = InteractiveMessageService()

def send_interactive_message(to_number: str, interactive_data: dict):
    """
    Envía un mensaje interactivo usando la API de WhatsApp Business
    """
    try:
        # Configuración de WhatsApp Business API (necesitarás configurar estas variables)
        access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        
        if not access_token or not phone_number_id:
            logger.warning("WhatsApp Business API no configurada, enviando mensaje de texto simple")
            return False
        
        url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number.replace("whatsapp:", ""),
            **interactive_data
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info(f"Mensaje interactivo enviado exitosamente a {to_number}")
            return True
        else:
            logger.error(f"Error enviando mensaje interactivo: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error en send_interactive_message: {str(e)}")
        return False

@webhook_router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(None),
    From: str = Form(None),
    To: str = Form(None),
    MessageSid: str = Form(None),
    ButtonPayload: str = Form(None)
):
    """
    Endpoint para recibir mensajes de WhatsApp desde Twilio
    """
    try:
        # Manejar tanto mensajes de texto como respuestas de botones
        if ButtonPayload:
            # Es una respuesta de botón interactivo
            logger.info(f"Botón presionado de {From}: {ButtonPayload}")
            button_id = ButtonPayload
            user_message = f"button:{button_id}"
        else:
            # Es un mensaje de texto normal
            logger.info(f"Mensaje recibido de {From}: {Body}")
            user_message = Body
        
        # Crear respuesta de Twilio
        response = MessagingResponse()
        
        # Obtener sesión del usuario
        user_id = From.replace("whatsapp:", "") if From else ""
        session = session_manager.get_session(user_id)
        
        # Manejar respuestas de botones interactivos
        if user_message.startswith("button:"):
            button_id = user_message.replace("button:", "")
            action, value = interactive_service.parse_interactive_response(button_id)
            
            if action == "client_menu":
                # Enviar menú de cliente con botones
                interactive_menu = interactive_service.create_interactive_client_menu()
                if send_interactive_message(From, interactive_menu):
                    session_manager.set_session_state(user_id, 'client_menu', {})
                    return PlainTextResponse("", media_type="application/xml")
                else:
                    # Fallback a mensaje de texto
                    menu_msg, options = interactive_service.create_client_menu()
                    response.message(menu_msg)
                    session_manager.set_session_state(user_id, 'client_menu', {'options': options})
            
            elif action == "non_client_menu":
                # Enviar menú de no cliente con botones
                interactive_menu = interactive_service.create_interactive_non_client_menu()
                if send_interactive_message(From, interactive_menu):
                    session_manager.set_session_state(user_id, 'non_client_menu', {})
                    return PlainTextResponse("", media_type="application/xml")
                else:
                    # Fallback a mensaje de texto
                    menu_msg, options = interactive_service.create_non_client_menu()
                    response.message(menu_msg)
                    session_manager.set_session_state(user_id, 'non_client_menu', {'options': options})
            
            elif action == "pricing":
                # Mostrar opciones de tallas
                size_message, available_sizes = interactive_service.create_size_selection_message()
                if size_message:
                    response.message(size_message)
                    session_manager.set_session_state(user_id, 'waiting_for_size_selection', {
                        'available_sizes': available_sizes
                    })
                else:
                    response.message("❌ No hay tallas disponibles en este momento.")
            
            # Manejar otras acciones de botones...
            elif action in ["consultation", "orders", "complaint", "product_info", "contact"]:
                # Usar las respuestas existentes del sistema
                new_state, message, options = interactive_service.handle_menu_selection(value, 
                    "client_menu" if action in ["consultation", "orders", "complaint"] else "non_client_menu")
                response.message(message)
                session_manager.set_session_state(user_id, new_state, {})
            
            return PlainTextResponse(str(response), media_type="application/xml")
        
        # Comandos globales que funcionan desde cualquier estado (excepto cuando está esperando selección)
        message_lower = user_message.lower().strip()
        
        # Solo procesar comandos globales si NO está en un estado de selección
        if session['state'] not in ['waiting_for_size_selection', 'waiting_for_product_selection']:
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
        
        # Comando menu siempre funciona
        if message_lower in ['menu', 'inicio', 'start', 'hola', 'hello', 'reiniciar', 'reset']:
            # Limpiar sesión y mostrar menú principal con botones interactivos
            session_manager.clear_session(user_id)
            
            # Intentar enviar menú interactivo
            interactive_menu = interactive_service.create_interactive_main_menu()
            if send_interactive_message(From, interactive_menu):
                session_manager.set_session_state(user_id, 'main_menu', {})
                return PlainTextResponse("", media_type="application/xml")
            else:
                # Fallback a mensaje de texto tradicional
                welcome_msg = interactive_service.create_welcome_message()
                menu_msg, options = interactive_service.create_main_menu()
                full_message = f"{welcome_msg}\n\n{menu_msg}"
                response.message(full_message)
                session_manager.set_session_state(user_id, 'main_menu', {'options': options})
                return PlainTextResponse(str(response), media_type="application/xml")
        
        # Procesar según el estado de la sesión
        if session['state'] == 'main_menu':
            # Usuario está en el menú principal
            new_state, message, options = interactive_service.handle_menu_selection(Body, "main")
            
            if new_state != 'main_menu':  # Solo si cambió de estado
                response.message(message)
                session_manager.set_session_state(user_id, new_state, {'options': options})
            else:
                response.message("🤔 Opción no válida. Por favor selecciona:\n\n1️⃣ Soy cliente\n2️⃣ No soy cliente\n\n💡 O escribe 'menu' para reiniciar")
        
        elif session['state'] == 'client_menu':
            # Usuario está en el menú de cliente
            new_state, message, options = interactive_service.handle_menu_selection(Body, "client_menu")
            
            if new_state != 'client_menu':  # Solo si cambió de estado
                response.message(message)
                session_manager.set_session_state(user_id, new_state, {})
            else:
                response.message("🤔 Opción no válida. Por favor selecciona:\n\n1️⃣ Consulta\n2️⃣ Pedidos\n3️⃣ Reclamación\n\n💡 O escribe 'menu' para volver al inicio")
        
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
                    response.message(formatted_response)
                else:
                    response.message(f"❌ No encontré información para {selected_product} talla {selected_size}")
                
                # Limpiar sesión
                session_manager.clear_session(user_id)
            else:
                response.message("🤔 Selección inválida. Por favor responde con:\n\n📝 El número de la opción\n💡 O escribe 'menu' para volver al inicio")
        
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
            
            # Si no es una consulta válida, mostrar menú de bienvenida con botones interactivos
            interactive_menu = interactive_service.create_interactive_main_menu()
            if send_interactive_message(From, interactive_menu):
                session_manager.set_session_state(user_id, 'main_menu', {})
            else:
                # Fallback a mensaje de texto tradicional
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