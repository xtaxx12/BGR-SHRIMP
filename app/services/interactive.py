from app.services.excel import ExcelService
import logging

logger = logging.getLogger(__name__)

class InteractiveMessageService:
    def __init__(self):
        self.excel_service = ExcelService()
    
    def create_welcome_message(self):
        """
        Crea el mensaje de bienvenida inicial
        """
        return "🦐 ¡Hola! Bienvenido a *ShrimpBot* 🤖\n\n✨ Tu asistente virtual especializado en precios de camarón de BGR Export\n\n🌊 Estoy aquí para ayudarte con consultas de precios, productos y más información sobre nuestros camarones de alta calidad."
    

    
    def create_main_menu(self):
        """
        Crea el menú principal simplificado
        """
        message = "🦐 ¿En qué podemos ayudarte?\n\n1️⃣ 💰 Consultar Precios\n2️⃣ 📋 Información de Productos\n3️⃣ 📞 Contacto Comercial"
        options = ["Consultar Precios", "Información de Productos", "Contacto Comercial"]
        return message, options
    
    def create_size_selection_message(self, product: str = None):
        """
        Crea un mensaje con opciones de tallas
        """
        try:
            if product:
                sizes = self.excel_service.get_available_sizes(product)
                title = f"🦐 Selecciona la talla para {product}:\n\n"
            else:
                # Usar HLSO como default para mostrar tallas comunes
                sizes = self.excel_service.get_available_sizes('HLSO')
                title = "🦐 Selecciona la talla del camarón:\n\n"
            
            # Crear mensaje con opciones numeradas
            message = title
            for i, size in enumerate(sizes, 1):
                message += f"{i}. {size}\n"
            
            message += f"\n📝 Responde con el número de tu opción (1-{len(sizes)})"
            message += f"\n💡 O escribe directamente: 'precio [producto] [talla]'"
            
            return message, sizes
            
        except Exception as e:
            logger.error(f"Error creando mensaje de tallas: {str(e)}")
            return None, []
    
    def create_product_selection_message(self, size: str):
        """
        Crea un mensaje con opciones de productos para una talla específica
        """
        try:
            # Obtener productos disponibles para esta talla
            products = self.excel_service.get_available_products()
            available_products = []
            
            for product in products:
                if size in self.excel_service.get_available_sizes(product):
                    available_products.append(product)
            
            if not available_products:
                return None, []
            
            # Crear mensaje con opciones numeradas
            message = f"🏷️ Selecciona el producto para talla {size}:\n\n"
            
            for i, product in enumerate(available_products, 1):
                message += f"{i}. {product}\n"
            
            message += f"\n📝 Responde con el número de tu opción (1-{len(available_products)})"
            
            return message, available_products
            
        except Exception as e:
            logger.error(f"Error creando mensaje de productos: {str(e)}")
            return None, []
    
    def parse_selection_response(self, message: str, options: list):
        """
        Parsea la respuesta del usuario para una selección numerada
        """
        try:
            message = message.strip()
            
            # Intentar parsear como número
            if message.isdigit():
                index = int(message) - 1
                if 0 <= index < len(options):
                    return options[index]
            
            # Intentar buscar coincidencia exacta
            message_upper = message.upper()
            for option in options:
                if option.upper() == message_upper:
                    return option
            
            return None
            
        except Exception as e:
            logger.error(f"Error parseando selección: {str(e)}")
            return None
    
    def handle_menu_selection(self, user_input: str, current_state: str = "main"):
        """
        Maneja la selección del usuario en el menú principal simplificado
        """
        user_input = user_input.strip().lower()
        
        if current_state == "main":
            if "consultar precios" in user_input or "precios" in user_input or user_input == "1":
                return "pricing", *self.create_size_selection_message()
            elif "información" in user_input or "informacion" in user_input or "productos" in user_input or user_input == "2":
                return "product_info", "🦐 **BGR Export - Productos Premium**\n\n🌟 Ofrecemos camarones de la más alta calidad en diferentes presentaciones:\n\n🔸 **HLSO** (Head Less Shell On) - Sin cabeza, con cáscara\n🔸 **P&D IQF** (Peeled Deveined) - Pelado y desvenado\n🔸 **P&D BLOQUE** (Peeled Deveined Block) - Pelado, desvenado, en bloque\n🔸 **PuD-EUROPA** - Pelado, desvenado, calidad europea\n🔸 **EZ PEEL** - Fácil pelado\n\n🌊 Todos nuestros productos cumplen con los más altos estándares de calidad internacional.\n\n💡 Escribe 'precios' para consultar cotizaciones o 'menu' para volver al inicio.", []
            elif "contacto" in user_input or user_input == "3":
                return "contact", "📞 **Contacto Comercial BGR Export**\n\n🏢 **Oficina Principal:**\nLima, Perú\n\n📧 **Email:**\nventas@bgrexport.com\n\n📱 **WhatsApp Comercial:**\n+51 999 999 999\n\n🌐 **Horarios de Atención:**\nLunes a Viernes: 8:00 AM - 6:00 PM (GMT-5)\nSábados: 9:00 AM - 1:00 PM\n\n🚀 ¡Nuestro equipo comercial está listo para atenderte!\n\n💡 Escribe 'precios' para consultar cotizaciones o 'menu' para volver al inicio.", []
        
        return current_state, "🤔 No entendí tu selección. Por favor elige una opción válida:\n\n1️⃣ Consultar Precios\n2️⃣ Información de Productos\n3️⃣ Contacto Comercial\n\n💡 O escribe 'menu' para volver al inicio.", []