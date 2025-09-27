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
        Obtiene el precio del camarón usando valores completamente dinámicos del usuario
        """
        try:
            # Obtener datos básicos
            size = user_input.get('size', '')
            product = user_input.get('product', 'HLSO')
            
            if not size:
                logger.warning("No se especificó talla")
                return None
            
            # Determinar precio base
            precio_base_kg = user_input.get('precio_base_custom')
            if precio_base_kg:
                logger.info(f"🎯 Usando precio base personalizado: ${precio_base_kg}/kg")
            else:
                # Solo si no especifica precio, buscar en Excel/Google Sheets
                price_data = self.excel_service.get_price_data(size, product)
                if not price_data:
                    logger.warning(f"No se encontró precio para {product} {size}")
                    return None
                precio_base_kg = price_data.get('precio_kg', 0)
                logger.info(f"📊 Usando precio base del Excel: ${precio_base_kg}/kg")
            
            # Usar valores dinámicos del usuario
            calculated_prices = self._calculate_dynamic_prices(
                base_price_kg=precio_base_kg,
                size=size,
                product=product,
                user_params=user_input
            )
            
            if calculated_prices:
                logger.info(f"✅ Precio calculado dinámicamente para {product} {size}: ${calculated_prices.get('precio_final_kg', 0):.2f}/kg")
                return calculated_prices
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculando precio: {str(e)}")
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
    
    def _calculate_dynamic_prices(self, base_price_kg: float, size: str, product: str, user_params: Dict) -> Optional[Dict]:
        """
        Calcula precios usando valores completamente dinámicos del usuario
        """
        try:
            # Extraer parámetros dinámicos del usuario
            glaseo_factor = user_params.get('glaseo_factor')
            flete_custom = user_params.get('flete_custom')
            usar_libras = user_params.get('usar_libras', False)
            destination = user_params.get('destination', '')
            
            # Determinar costo fijo según si usa libras o kilos
            if usar_libras:
                costo_fijo = 0.13  # 0.29 / 2.2 para destinos USA en libras
                logger.info(f"🇺🇸 Destino USA (libras) - Costo fijo: ${costo_fijo}")
            else:
                costo_fijo = 0.29  # Para destinos en kilos
                logger.info(f"🌍 Destino en kilos - Costo fijo: ${costo_fijo}")
            
            # Para el flete, usar valor personalizado del usuario o buscar en Google Sheets
            # NO cambiar automáticamente el flete por destino
            if flete_custom is not None:
                flete_value = flete_custom
                logger.info(f"💰 Usando flete personalizado: ${flete_value}")
            else:
                # TODO: Obtener flete desde Google Sheets según destino
                # Por ahora usar un valor por defecto
                flete_value = 0.20  # Valor por defecto
                logger.info(f"📊 Usando flete por defecto: ${flete_value} (debería venir de Sheets)")
            
            # Usar glaseo especificado o valor por defecto
            if glaseo_factor is None:
                glaseo_factor = 0.70  # Valor por defecto (70%)
                logger.info(f"📊 Usando glaseo por defecto: {glaseo_factor:.1%}")
            else:
                logger.info(f"🎯 Usando glaseo especificado: {glaseo_factor:.1%}")
            
            logger.info(f"🧮 Cálculo dinámico: glaseo={glaseo_factor}, flete={flete_value}, libras={usar_libras}")
            
            # Aplicar fórmulas según las reglas especificadas
            # 1. Precio FOB = Precio Base - Costo Fijo
            precio_fob_kg = max(0, base_price_kg - costo_fijo)
            
            # 2. Precio con Glaseo = Precio FOB × Factor Glaseo
            precio_glaseo_kg = precio_fob_kg * glaseo_factor
            
            # 3. Precio Final = Precio Glaseo + Flete
            precio_final_kg = precio_glaseo_kg + flete_value
            
            # Convertir a libras
            if usar_libras:
                precio_fob_lb = precio_fob_kg / 2.2
                precio_glaseo_lb = precio_glaseo_kg / 2.2
                precio_final_lb = precio_final_kg / 2.2
                base_price_lb = base_price_kg / 2.2
            else:
                precio_fob_lb = precio_fob_kg * 2.2
                precio_glaseo_lb = precio_glaseo_kg * 2.2
                precio_final_lb = precio_final_kg * 2.2
                base_price_lb = base_price_kg * 2.2
            
            result = {
                'size': size,
                'product': product,
                'talla': size,
                'producto': product,
                'precio_kg': base_price_kg,
                'precio_lb': base_price_lb,
                'precio_fob_kg': precio_fob_kg,
                'precio_fob_lb': precio_fob_lb,
                'precio_glaseo_kg': precio_glaseo_kg,
                'precio_glaseo_lb': precio_glaseo_lb,
                'precio_final_kg': precio_final_kg,
                'precio_final_lb': precio_final_lb,
                'costo_fijo': costo_fijo,
                'factor_glaseo': glaseo_factor,
                'flete': flete_value,
                'flete_base': 0.29 if not usar_libras else 0.13,
                'usar_libras': usar_libras,
                'destination': destination,
                'quantity': user_params.get('quantity', ''),
                'cliente_nombre': user_params.get('cliente_nombre', ''),
                'calculo_dinamico': True,
                'valores_usuario': {
                    'glaseo_especificado': glaseo_factor,
                    'flete_especificado': flete_custom,
                    'precio_base_especificado': user_params.get('precio_base_custom')
                }
            }
            
            logger.info(f"✅ Cálculo dinámico completado: Base=${base_price_kg:.2f} → Final=${precio_final_kg:.2f}/kg")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en cálculo dinámico: {str(e)}")
            return None