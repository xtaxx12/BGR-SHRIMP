from app.services.excel import ExcelService
from app.services.excel_local_calculator import ExcelLocalCalculatorService
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PricingService:
    def __init__(self):
        self.excel_service = ExcelService()
        self.calculator_service = ExcelLocalCalculatorService()
    
    def calculate_final_price(self, base_price: float, fixed_cost: float, 
                            glaseo_factor: float, freight: float) -> float:
        """
        Calcula el precio final aplicando la lógica de la calculadora Excel:
        Precio final = (Precio base + Costo fijo) / Factor glaseo + Flete
        """
        try:
            # Aplicar costo fijo
            price_with_fixed = base_price + fixed_cost
            
            # Aplicar factor de glaseo (rendimiento)
            price_with_glaseo = price_with_fixed / glaseo_factor
            
            # Agregar flete
            final_price = price_with_glaseo + freight
            
            return round(final_price, 2)
            
        except Exception as e:
            logger.error(f"Error calculando precio: {str(e)}")
            return 0.0
    
    def get_shrimp_price(self, user_input: Dict) -> Optional[Dict]:
        """
        Obtiene el precio del camarón usando las fórmulas del Excel
        """
        try:
            size = user_input.get('size')
            product = user_input.get('product', 'HLSO')  # Default a HLSO
            
            if not size:
                return None
            
            # Primero obtener el precio base desde la tabla
            price_data = self.excel_service.get_price_data(size, product)
            if not price_data:
                return None
            
            # Obtener el precio base por kilo
            precio_base_kg = price_data['precio_kg']
            
            # Usar el calculador de Excel para obtener precios FOB, glaseo y flete
            calculated_prices = self.calculator_service.calculate_prices(size, precio_base_kg)
            
            if not calculated_prices:
                # Fallback a los datos originales si el cálculo falla
                logger.warning("Usando precios originales como fallback")
                result = {
                    'size': size,
                    'producto': price_data['producto'],
                    'precio_kg': precio_base_kg,
                    'precio_lb': price_data['precio_lb'],
                    'talla': price_data['talla'],
                    'quantity': user_input.get('quantity', ''),
                    'destination': user_input.get('destination', ''),
                    'unit': user_input.get('unit', 'lb'),
                    'calculado_con': 'Datos originales'
                }
            else:
                # Usar los precios calculados con las fórmulas del Excel
                result = {
                    'size': size,
                    'producto': product,
                    'talla': calculated_prices['talla'],
                    'precio_base_kg': calculated_prices['precio_kg_original'],
                    'precio_base_lb': calculated_prices['precio_lb_original'],
                    'precio_fob_kg': calculated_prices['precio_fob_kg'],
                    'precio_fob_lb': calculated_prices['precio_fob_lb'],
                    'precio_glaseo_kg': calculated_prices['precio_glaseo_kg'],
                    'precio_glaseo_lb': calculated_prices['precio_glaseo_lb'],
                    'precio_flete_kg': calculated_prices['precio_flete_kg'],
                    'precio_flete_lb': calculated_prices['precio_flete_lb'],
                    'factores': calculated_prices['factores'],
                    'quantity': user_input.get('quantity', ''),
                    'destination': user_input.get('destination', ''),
                    'unit': user_input.get('unit', 'lb'),
                    'calculado_con': calculated_prices['calculado_con']
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo precio: {str(e)}")
            return None
    
    def get_available_sizes(self, product: str = 'HLSO') -> list:
        """
        Retorna las tallas disponibles para un producto
        """
        return self.excel_service.get_available_sizes(product)
    
    def get_available_products(self) -> list:
        """
        Retorna los productos disponibles
        """
        return self.excel_service.get_available_products()
    
    def reload_prices(self) -> bool:
        """
        Recarga los precios del Excel
        """
        return self.excel_service.reload_data()