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
        Crea el menú principal con las opciones iniciales
        """
        message = "🎯 Por favor, elige una opción:\n\n1️⃣ 👤 Soy cliente\n2️⃣ 🆕 No soy cliente"
        options = ["Soy cliente", "No soy cliente"]
        return message, options
    
    def create_client_menu(self):
        """
        Crea el menú para clientes existentes
        """
        message = "🤝 ¿En qué podemos ayudarte?\n\n1️⃣ 💬 Consulta\n2️⃣ 📦 Pedidos\n3️⃣ ⚠️ Reclamación"
        options = ["Consulta", "Pedidos", "Reclamación"]
        return message, options
    
    def create_non_client_menu(self):
        """
        Crea el menú para no clientes
        """
        message = "🌟 ¿En qué podemos ayudarte?\n\n1️⃣ 📋 Información de productos\n2️⃣ 💰 Precios\n3️⃣ 📞 Contacto comercial"
        options = ["Información de productos", "Precios", "Contacto comercial"]
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
        Maneja la selección del usuario en los diferentes menús
        """
        user_input = user_input.strip().lower()
        
        if current_state == "main":
            if "soy cliente" in user_input or user_input == "1":
                return "client_menu", *self.create_client_menu()
            elif "no soy cliente" in user_input or user_input == "2":
                return "non_client_menu", *self.create_non_client_menu()
        
        elif current_state == "client_menu":
            if "consulta" in user_input or user_input == "1":
                return "consultation", "💬 ¡Perfecto! ¿Qué consulta tienes?\n\n🔍 Puedes preguntarme sobre:\n• 💰 Precios actualizados\n• 🦐 Productos disponibles\n• 📦 Stock y disponibilidad\n• 🚚 Tiempos de entrega\n• 📋 Cualquier información que necesites\n\n✨ ¡Estoy aquí para ayudarte!", []
            elif "pedidos" in user_input or user_input == "2":
                return "orders", "📦 ¡Excelente! Para procesar tu pedido necesito:\n\n🦐 **Producto:** (HLSO, P&D, PDTO, etc.)\n📏 **Talla:** (16/20, 21/25, etc.)\n📊 **Cantidad:** (en libras o kilos)\n📅 **Fecha de entrega deseada**\n🌍 **Destino**\n\n💡 Ejemplo: *HLSO 16/20, 15,000 lb, entrega 15 enero, destino Miami*", []
            elif "reclamación" in user_input or user_input == "3":
                return "complaint", "⚠️ Lamento escuchar que tienes una reclamación.\n\n🤝 En BGR Export valoramos mucho tu satisfacción. Por favor describe detalladamente:\n\n📋 **El problema:**\n📅 **Fecha del pedido:**\n📦 **Número de orden (si lo tienes):**\n📸 **Fotos (si aplica):**\n\n🚀 Te ayudaremos a resolverlo lo más pronto posible.", []
        
        elif current_state == "non_client_menu":
            if "información" in user_input or "informacion" in user_input or user_input == "1":
                return "product_info", "🦐 **BGR Export - Productos Premium**\n\n🌟 Ofrecemos camarones de la más alta calidad en diferentes presentaciones:\n\n🔸 **HLSO** (Head Less Shell On) - Sin cabeza, con cáscara\n🔸 **P&D** (Peeled Deveined) - Pelado y desvenado\n🔸 **PDTO** (Peeled Deveined Tail On) - Pelado, desvenado, con cola\n🔸 **EZ PEEL** - Fácil pelado\n🔸 **IQF** - Congelado individualmente\n\n🌊 Todos nuestros productos cumplen con los más altos estándares de calidad internacional.\n\n💡 ¿Qué producto específico te interesa conocer más?", []
            elif "precios" in user_input or user_input == "2":
                return "pricing", *self.create_size_selection_message()
            elif "contacto" in user_input or user_input == "3":
                return "contact", "📞 **Contacto Comercial BGR Export**\n\n🏢 **Oficina Principal:**\nLima, Perú\n\n📧 **Email:**\nventas@bgrexport.com\n\n📱 **WhatsApp Comercial:**\n+51 999 999 999\n\n🌐 **Horarios de Atención:**\nLunes a Viernes: 8:00 AM - 6:00 PM (GMT-5)\nSábados: 9:00 AM - 1:00 PM\n\n🚀 ¡Nuestro equipo comercial está listo para atenderte!", []
        
        return current_state, "🤔 No entendí tu selección. Por favor elige una opción válida usando el número o escribiendo la opción completa.\n\n💡 Tip: Escribe 'menu' para volver al inicio.", []