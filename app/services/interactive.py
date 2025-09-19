from app.services.excel import ExcelService
import logging

logger = logging.getLogger(__name__)

class InteractiveMessageService:
    def __init__(self):
        self.excel_service = ExcelService()
    
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