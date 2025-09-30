import pandas as pd
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ExcelLocalCalculatorService:
    def __init__(self, excel_path: str = "data/CALCULO_DE _PRECIOS-AGUAJE17.xlsx"):
        self.excel_path = excel_path
        self.df = None
        self.factores = {}
        self.load_excel_data()
    
    def load_excel_data(self):
        """
        Carga el Excel local y extrae los factores de cálculo
        """
        try:
            if not os.path.exists(self.excel_path):
                logger.warning(f"Archivo Excel no encontrado: {self.excel_path}")
                self.set_default_factors()
                return
            
            # Leer la hoja PRECIOS FOB
            self.df = pd.read_excel(self.excel_path, sheet_name="PRECIOS FOB")
            
            # Extraer factores desde el Excel (según tu imagen)
            # AA28: COSTO FIJO (0.29)
            # AC28: GLASEO (0.7) 
            # AE28: FLETE (0.2)
            
            try:
                # Intentar leer los factores desde las celdas específicas
                costo_fijo = self.df.iloc[27, 26] if len(self.df) > 27 and len(self.df.columns) > 26 else 0.29  # AA28
                factor_glaseo = self.df.iloc[27, 28] if len(self.df) > 27 and len(self.df.columns) > 28 else 0.7  # AC28
                flete = self.df.iloc[27, 30] if len(self.df) > 27 and len(self.df.columns) > 30 else 0.2  # AE28
                
                # Convertir a float si es posible
                self.factores = {
                    'costo_fijo': float(costo_fijo) if self._is_number(costo_fijo) else 0.29,
                    'factor_glaseo': float(factor_glaseo) if self._is_number(factor_glaseo) else 0.7,
                    'flete': float(flete) if self._is_number(flete) else 0.2
                }
                
                logger.debug(f"✅ Factores cargados desde Excel: {self.factores}")
                
            except Exception as e:
                logger.warning(f"Error leyendo factores del Excel, usando valores por defecto: {e}")
                self.set_default_factors()
                
        except Exception as e:
            logger.error(f"Error cargando Excel: {str(e)}")
            self.set_default_factors()
    
    def set_default_factors(self):
        """
        Establece factores por defecto basados en tu imagen
        """
        self.factores = {
            'costo_fijo': 0.29,
            'factor_glaseo': 0.7,
            'flete': 0.2
        }
        logger.info(f"📋 Usando factores por defecto: {self.factores}")
    
    def _is_number(self, value):
        """
        Verifica si un valor puede ser convertido a número
        """
        try:
            if value == '' or value is None or pd.isna(value):
                return False
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def calculate_prices(self, talla: str, precio_kg: float) -> Dict:
        """
        Calcula precios usando las fórmulas del Excel:
        - PRECIO FOB = Y33 - AA28 (precio_kg - costo_fijo)
        - PRECIO CON GLASEO = AA33 * AC28 (precio_fob * factor_glaseo)
        - PRECIO CON GLASEO Y FLETE = AC33 + AA28 + AE28 (precio_glaseo + costo_fijo + flete)
        """
        try:
            logger.info(f"🧮 Calculando precios para {talla} a ${precio_kg:.2f}/kg")
            
            # Obtener factores
            costo_fijo = self.factores['costo_fijo']
            factor_glaseo = self.factores['factor_glaseo']
            flete = self.factores['flete']
            
            # Aplicar fórmulas exactas de tu Excel
            # Fórmula 1: PRECIO FOB = Y33 - AA28
            precio_fob_kg = precio_kg - costo_fijo
            
            # Fórmula 2: PRECIO CON GLASEO = AA33 * AC28
            precio_glaseo_kg = precio_fob_kg * factor_glaseo
            
            # Fórmula 3: PRECIO CON GLASEO Y FLETE = AC33 + AA28 + AE28
            precio_flete_kg = precio_glaseo_kg + costo_fijo + flete
            
            # Convertir a libras (1 kg = 2.20462 lb)
            conversion_factor = 2.20462
            
            result = {
                'talla': talla,
                'precio_kg_original': precio_kg,
                'precio_lb_original': precio_kg / conversion_factor,
                'precio_fob_kg': precio_fob_kg,
                'precio_fob_lb': precio_fob_kg / conversion_factor,
                'precio_glaseo_kg': precio_glaseo_kg,
                'precio_glaseo_lb': precio_glaseo_kg / conversion_factor,
                'precio_flete_kg': precio_flete_kg,
                'precio_flete_lb': precio_flete_kg / conversion_factor,
                'factores': {
                    'costo_fijo': costo_fijo,
                    'factor_glaseo': factor_glaseo,
                    'flete': flete
                },
                'calculado_con': 'Excel Local (Fórmulas)'
            }
            
            logger.debug(f"✅ Cálculo completado:")
            logger.debug(f"   📊 Base: ${precio_kg:.2f}/kg")
            logger.debug(f"   🚢 FOB: ${precio_fob_kg:.2f}/kg")
            logger.info(f"   ❄️ Glaseo: ${precio_glaseo_kg:.2f}/kg")
            logger.info(f"   ✈️ Final: ${precio_flete_kg:.2f}/kg")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calculando precios: {str(e)}")
            # Retornar cálculo básico en caso de error
            return {
                'talla': talla,
                'precio_kg_original': precio_kg,
                'precio_lb_original': precio_kg / 2.20462,
                'precio_fob_kg': precio_kg,
                'precio_fob_lb': precio_kg / 2.20462,
                'precio_glaseo_kg': precio_kg,
                'precio_glaseo_lb': precio_kg / 2.20462,
                'precio_flete_kg': precio_kg,
                'precio_flete_lb': precio_kg / 2.20462,
                'factores': self.factores,
                'calculado_con': 'Fallback (Error en cálculo)'
            }
    
    def get_base_price_from_excel(self, talla: str, producto: str = 'HLSO') -> Optional[float]:
        """
        Obtiene el precio base desde el Excel local
        """
        try:
            if self.df is None:
                return None
            
            # Mapear productos a sus columnas (basado en tu Excel)
            product_columns = {
                'HOSO': {'talla_col': 1, 'precio_col': 2},
                'HLSO': {'talla_col': 5, 'precio_col': 6},
                'P&D IQF': {'talla_col': 9, 'precio_col': 10},
                'P&D BLOQUE': {'talla_col': 14, 'precio_col': 15},
                'PuD-EUROPA': {'talla_col': 18, 'precio_col': 19}
            }
            
            if producto not in product_columns:
                return None
            
            cols = product_columns[producto]
            
            # Buscar en las filas 13-23 (sección PRECIOS FOB)
            for i in range(13, min(24, len(self.df))):
                try:
                    if len(self.df.iloc[i]) <= max(cols['talla_col'], cols['precio_col']):
                        continue
                        
                    talla_value = str(self.df.iloc[i, cols['talla_col']]).strip()
                    precio_value = self.df.iloc[i, cols['precio_col']]
                    
                    if talla_value == talla and self._is_number(precio_value):
                        return float(precio_value)
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo precio base del Excel: {str(e)}")
            return None
    
    def reload_data(self):
        """
        Recarga los datos del Excel
        """
        self.load_excel_data()