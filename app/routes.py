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
        
        # Procesar según el estado de la sesión
        if session['state'] == 'waiting_for_size_selection':
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
                response.message("❌ Selección inválida. Por favor, responde con el número de la opción deseada.")
        
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
                response.message("❌ Selección inválida. Por favor, responde con el número de la opción deseada.")
        
        else:
            # Estado normal - procesar mensaje nuevo
            message_lower = Body.lower().strip()
            
            # Comandos especiales
            if message_lower in ['tallas', 'sizes', 'opciones', 'menu']:
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
                response.message("🤖 **BGR Export - Bot de Precios**\n\n"
                               "**Comandos disponibles:**\n"
                               "• `tallas` - Ver tallas disponibles\n"
                               "• `productos` - Ver productos disponibles\n"
                               "• `precio HLSO 16/20` - Consulta directa\n"
                               "• `16/20` - Solo talla (te mostraré opciones)\n\n"
                               "**Ejemplos:**\n"
                               "• Precio HLSO 16/20 para 15000 lb destino China\n"
                               "• P&D IQF 21/25\n"
                               "• EZ PEEL 26/30")
                return PlainTextResponse(str(response), media_type="application/xml")
            
            user_input = parse_user_message(Body)
            
            if not user_input:
                response.message("¡Hola! 👋 Soy el bot de BGR Export.\n\n"
                               "Puedes consultarme precios de camarón enviando:\n"
                               "• Talla (ej: 16/20, 21/25)\n"
                               "• Producto y talla (ej: HLSO 16/20)\n"
                               "• Consulta completa (ej: Precio HLSO 16/20 para 15,000 lb destino China)\n\n"
                               "💡 Escribe 'ayuda' para ver todos los comandos disponibles")
            else:
                # Obtener precio del camarón
                price_info = pricing_service.get_shrimp_price(user_input)
                
                if price_info:
                    formatted_response = format_price_response(price_info)
                    response.message(formatted_response)
                    session_manager.clear_session(user_id)  # Limpiar sesión después de respuesta exitosa
                else:
                    # No se encontró la talla, mostrar opciones interactivas
                    size_message, available_sizes = interactive_service.create_size_selection_message()
                    
                    if size_message:
                        response.message(size_message)
                        session_manager.set_session_state(user_id, 'waiting_for_size_selection', {
                            'available_sizes': available_sizes
                        })
                    else:
                        response.message("❌ No hay tallas disponibles en este momento.")
        
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