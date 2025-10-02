from app.services.excel import ExcelService
from app.services.excel_local_calculator import ExcelLocalCalculatorService
from app.services.google_sheets import GoogleSheetsService
from typing import Dict, Optional
import logging
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

def precise_round(value: float, decimals: int = 2) -> float:
    """
    Redondeo preciso usando Decimal para evitar problemas de punto flotante
    """
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

class PricingService:
    def __init__(self):
        self.excel_service = ExcelService()
        self.sheets_service = GoogleSheetsService()
        self.calculator_service = ExcelLocalCalculatorService()
    
    def calculate_final_price(self, base_price: float, fixed_cost: float, 
                            glaseo_factor: float, freight: float) -> float:
        """
        Calcula el precio final aplicando la lógica de la calculadora Excel:
        Precio con glaseo = (precio_base - costo_fijo) × glaseo_factor
        CFR = Precio con glaseo + Costo fijo + Flete
        """
        try:
            # Calcular precio con glaseo según imagen
            price_fob_minus_fixed = base_price - fixed_cost
            price_with_glaseo = price_fob_minus_fixed * glaseo_factor
            
            # Precio final CFR
            final_price = price_with_glaseo + fixed_cost + freight
            
            return round(final_price, 2)
            
        except Exception as e:
            logger.error(f"Error calculando precio: {str(e)}")
            return 0.0
    
    def get_glaseo_factor(self, glaseo_percentage: int) -> float:
        """
        Convierte porcentaje de glaseo a factor según las reglas del negocio:
        - 10% glaseo → Factor = 0.90
        - 20% glaseo → Factor = 0.80  
        - 30% glaseo → Factor = 0.70
        """
        glaseo_factors = {
            10: 0.90,
            20: 0.80,
            30: 0.70
        }
        return glaseo_factors.get(glaseo_percentage, 0.70)  # Default 30%
    
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
                logger.debug(f"✅ Precio calculado dinámicamente para {product} {size}: ${calculated_prices.get('precio_final_kg', 0):.2f}/kg")
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
            glaseo_percentage = user_params.get('glaseo_percentage')  # Porcentaje original
            flete_custom = user_params.get('flete_custom')
            flete_solicitado = user_params.get('flete_solicitado', False)
            usar_libras = user_params.get('usar_libras', False)
            destination = user_params.get('destination', '')
            
            # Obtener costo fijo desde Google Sheets
            costo_fijo_sheets = self.sheets_service.get_costo_fijo_value()
            
            # Determinar costo fijo según destino
            if destination and destination.lower() == 'houston':
                costo_fijo = costo_fijo_sheets
            elif usar_libras:
                costo_fijo = costo_fijo_sheets / 2.2
            else:
                costo_fijo = costo_fijo_sheets
            
            # Para el flete, usar valor personalizado del usuario o desde Google Sheets
            # Solo si se solicitó flete explícitamente
            if flete_solicitado:
                if flete_custom is not None:
                    flete_value = flete_custom
                else:
                    flete_value = self.sheets_service.get_flete_value()
            else:
                flete_value = 0  # No aplicar flete si no se solicitó
            
            # Usar glaseo especificado o valor por defecto
            if glaseo_factor is None:
                glaseo_factor = 0.70
            
            # Usar el calculador corregido con máxima precisión
            # El precio base que recibimos es en realidad el precio FOB
            calculated_result = self.calculator_service.calculate_prices(
                precio_fob_kg=base_price_kg,
                glaseo_factor=glaseo_factor,
                flete=flete_value
            )
            
            if not calculated_result:
                logger.error("Error en calculador de precisión")
                return None
            
            # Extraer valores calculados con precisión
            precio_fob_kg = calculated_result.get('precio_fob_kg')
            precio_glaseo_kg = calculated_result.get('precio_glaseo_kg')
            precio_final_kg = calculated_result.get('precio_final_kg')
            precio_neto_kg = calculated_result.get('precio_neto_kg')  # FOB - costo fijo
            
            # Obtener precios en libras del calculador (ya calculados con precisión)
            precio_fob_lb = calculated_result.get('precio_fob_lb')
            precio_glaseo_lb = calculated_result.get('precio_glaseo_lb')
            precio_final_lb = calculated_result.get('precio_final_lb')
            precio_neto_lb = calculated_result.get('precio_neto_lb')
            base_price_lb = precise_round(base_price_kg / 2.20462262185)
            
            # Determinar si se debe mostrar precio CFR o precio con glaseo
            # Solo incluir flete si el usuario EXPLÍCITAMENTE lo menciona
            flete_solicitado = user_params.get('flete_solicitado', False)
            incluye_flete = flete_solicitado or flete_custom is not None
            
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
                'glaseo_percentage': glaseo_percentage,  # Porcentaje original solicitado
                'flete': flete_value,
                'flete_base': 0.29 if not usar_libras else 0.13,
                'usar_libras': usar_libras,
                'destination': destination,
                'quantity': user_params.get('quantity', ''),
                'cliente_nombre': user_params.get('cliente_nombre', ''),
                'calculo_dinamico': True,
                'incluye_flete': incluye_flete,  # Flag para determinar qué precio mostrar
                'valores_usuario': {
                    'glaseo_especificado': glaseo_factor,
                    'flete_especificado': flete_custom,
                    'precio_base_especificado': user_params.get('precio_base_custom')
                }
            }
            
            logger.debug(f"✅ Cálculo dinámico completado: Base=${base_price_kg:.2f} → Final=${precio_final_kg:.2f}/kg")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en cálculo dinámico: {str(e)}")
            return None