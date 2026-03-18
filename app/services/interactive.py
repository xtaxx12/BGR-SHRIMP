import logging

from app.services.excel import ExcelService

logger = logging.getLogger(__name__)

class InteractiveMessageService:
    def __init__(self, excel_service=None):
        if excel_service:
            self.excel_service = excel_service
        else:
            self.excel_service = ExcelService()

    def create_welcome_message(self):
        """
        Crea el mensaje de bienvenida inicial
        """
        return "👋 Bienvenido a BGR Export.\n\nSoy tu asistente de cotizaciones de camarón. Escribe producto + talla para cotizar.\n\nEjemplo: \"HLSO 16/20\""

    def create_main_menu(self):
        """
        Crea el menú principal simplificado
        """
        message = "¿En qué puedo ayudarte?\n\n1. Consultar precios\n2. Productos disponibles\n3. Contacto comercial"
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
                # Obtener TODAS las tallas únicas de todos los productos
                all_sizes = set()

                # Obtener productos disponibles
                products = self.excel_service.get_available_products()

                # Recopilar todas las tallas de todos los productos
                for prod in products:
                    prod_sizes = self.excel_service.get_available_sizes(prod)
                    all_sizes.update(prod_sizes)

                # Si no hay tallas, intentar directamente desde Google Sheets
                if not all_sizes and hasattr(self.excel_service, 'google_sheets_service'):
                    gs_service = self.excel_service.google_sheets_service
                    if gs_service and gs_service.prices_data:
                        for prod in gs_service.prices_data.keys():
                            prod_sizes = gs_service.get_available_sizes(prod)
                            all_sizes.update(prod_sizes)
                        logger.info(f"Tallas obtenidas directamente de Google Sheets: {all_sizes}")

                # Convertir a lista y ordenar las tallas
                sizes = self._sort_sizes(list(all_sizes))
                title = "🦐 Selecciona la talla del camarón:\n\n"

            logger.info(f"Tallas obtenidas para {product or 'HLSO'}: {sizes}")

            if not sizes:
                logger.warning("No se encontraron tallas disponibles")
                return "❌ No hay tallas disponibles en este momento.", []

            # Crear mensaje con opciones numeradas
            message = title
            for i, size in enumerate(sizes, 1):
                message += f"{i}. {size}\n"

            message += f"\n📝 Responde con el número de tu opción (1-{len(sizes)})"
            message += "\n💡 O escribe directamente: 'precio [producto] [talla]'"

            return message, sizes

        except Exception as e:
            logger.error(f"Error creando mensaje de tallas: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return "❌ Error obteniendo tallas disponibles.", []

    def _sort_sizes(self, sizes):
        """
        Ordena las tallas de camarón de mayor a menor (más pequeño a más grande)
        """
        def size_key(size):
            try:
                if size.startswith('U'):
                    # Para tallas como U15, usar el número después de U
                    return (0, int(size[1:]))
                elif '/' in size:
                    # Para tallas como 16/20, usar el primer número
                    return (1, int(size.split('/')[0]))
                elif size.endswith('/100'):
                    # Para tallas como 91/100
                    return (1, int(size.split('/')[0]))
                else:
                    # Para otros casos, intentar convertir a número
                    return (2, int(size))
            except:
                # Si no se puede parsear, poner al final
                return (3, 999)

        return sorted(sizes, key=size_key)

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
                return "product_info", "Productos disponibles:\n\n• HLSO - Sin cabeza, con cáscara\n• HOSO - Entero (con cabeza)\n• P&D IQF - Pelado y desvenado\n• P&D Bloque - Pelado en bloque\n• PuD-Europa - Calidad europea\n• EZ Peel - Fácil pelado\n\nEscribe producto + talla para cotizar.\nEjemplo: \"HLSO 16/20\"", []
            elif "contacto" in user_input or user_input == "3":
                return "contact", "Contacto BGR Export\n\nOficina: Puerto Jeli, Santa Rosa\nEmail: amerino@bgrexport.com\nWhatsApp: +593 98-805-7425\n\nHorario: Lun-Vie 8:00-18:00 | Sab 9:00-13:00 (GMT-5)\n\nEscribe 'precios' para cotizar.", []

        return current_state, "No entendí tu selección. Elige una opción:\n\n1. Consultar precios\n2. Productos disponibles\n3. Contacto comercial\n\nO escribe 'menu' para reiniciar.", []
