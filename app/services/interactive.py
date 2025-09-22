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
        return "Hola"
    
    def create_main_menu(self):
        """
        Crea el menú principal con las opciones iniciales
        """
        message = "Por favor, elige una opción:"
        options = ["Soy cliente", "No soy cliente"]
        return message, options
    
    def create_client_menu(self):
        """
        Crea el menú para clientes existentes
        """
        message = "¿En qué podemos ayudarte?"
        options = ["Consulta", "Pedidos", "Reclamación"]
        return message, options
    
    def create_non_client_menu(self):
        """
        Crea el menú para no clientes
        """
        message = "¿En qué podemos ayudarte?"
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
            message += f"\n� O sescribe directamente: 'precio [producto] [talla]'"
            
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
                return "consultation", "¿Qué consulta tienes? Puedes preguntarme sobre precios, productos o cualquier información que necesites.", []
            elif "pedidos" in user_input or user_input == "2":
                return "orders", "Para realizar un pedido, por favor proporciona:\n• Producto\n• Talla\n• Cantidad\n• Fecha de entrega deseada", []
            elif "reclamación" in user_input or user_input == "3":
                return "complaint", "Lamento escuchar que tienes una reclamación. Por favor describe el problema y te ayudaremos a resolverlo.", []
        
        elif current_state == "non_client_menu":
            if "información" in user_input or "informacion" in user_input or user_input == "1":
                return "product_info", "Ofrecemos camarones de alta calidad en diferentes presentaciones:\n• HLSO (Head Less Shell On)\n• PD (Peeled Deveined)\n• PDTO (Peeled Deveined Tail On)\n\n¿Qué producto te interesa?", []
            elif "precios" in user_input or user_input == "2":
                return "pricing", *self.create_size_selection_message()
            elif "contacto" in user_input or user_input == "3":
                return "contact", "Para contacto comercial:\n📧 Email: ventas@empresa.com\n📱 WhatsApp: +51 999 999 999\n🏢 Oficina: Lima, Perú", []
        
        return current_state, "No entendí tu selección. Por favor elige una opción válida.", []