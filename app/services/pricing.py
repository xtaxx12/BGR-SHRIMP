from app.services.excel import ExcelService
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PricingService:
    def __init__(self):
        self.excel_service = ExcelService()
    
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
        Obtiene el precio del camarón basado en la entrada del usuario
        """
        try:
            size = user_input.get('size')
            if not size:
                return None
            
            # Obtener datos del Excel
            price_data = self.excel_service.get_price_data(size)
            if not price_data:
                return None
            
            # Calcular precio final
            final_price = self.calculate_final_price(
                price_data['precio_base'],
                price_data['costo_fijo'],
                price_data['factor_glaseo'],
                price_data['flete']
            )
            
            # Preparar respuesta
            result = {
                'size': size,
                'producto': price_data['producto'],
                'precio_base': price_data['precio_base'],
                'costo_fijo': price_data['costo_fijo'],
                'factor_glaseo': price_data['factor_glaseo'],
                'flete': price_data['flete'],
                'precio_final': final_price,
                'quantity': user_input.get('quantity', ''),
                'destination': user_input.get('destination', '')
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo precio: {str(e)}")
            return None
    
    def get_available_sizes(self) -> list:
        """
        Retorna las tallas disponibles
        """
        return self.excel_service.get_available_sizes()
    
    def reload_prices(self) -> bool:
        """
        Recarga los precios del Excel
        """
        return self.excel_service.reload_data()