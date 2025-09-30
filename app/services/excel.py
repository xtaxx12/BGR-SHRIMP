import pandas as pd
import os
from typing import Dict, Optional
import logging
from app.services.google_sheets import GoogleSheetsService

logger = logging.getLogger(__name__)

class ExcelService:
    def __init__(self, excel_path: str = "data/CALCULO_DE _PRECIOS-AGUAJE17.xlsx"):
        self.excel_path = excel_path
        self.prices_data = None
        # Usar Google Sheets como fuente principal
        self.google_sheets_service = GoogleSheetsService()
        self.load_data()
    
    def load_data(self) -> bool:
        """
        Carga los datos desde Google Sheets (preferido) o Excel local (fallback)
        """
        try:
            # Verificar si Google Sheets está configurado
            google_sheets_id = os.getenv("GOOGLE_SHEETS_ID")
            google_credentials = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            
            if google_sheets_id and google_credentials:
                # Intentar cargar desde Google Sheets
                if self.google_sheets_service.prices_data:
                    self.prices_data = self.google_sheets_service.prices_data
                    logger.debug("✅ Datos cargados desde Google Sheets")
                    return True
                else:
                    logger.warning("⚠️ Google Sheets configurado pero sin datos, usando Excel local...")
                    return self.load_excel_data()
            else:
                # Usar Excel local directamente
                logger.info("📁 Google Sheets no configurado, usando Excel local...")
                return self.load_excel_data()
        except Exception as e:
            logger.error(f"❌ Error cargando datos: {str(e)}")
            return self.load_excel_data()
    
    def load_excel_data(self) -> bool:
        """
        Carga los datos del archivo Excel (hoja PRECIOS FOB)
        """
        try:
            if not os.path.exists(self.excel_path):
                logger.warning(f"Archivo Excel no encontrado: {self.excel_path}")
                self.create_sample_data()
                return True
            
            # Leer la hoja PRECIOS FOB
            df = pd.read_excel(self.excel_path, sheet_name="PRECIOS FOB")
            
            # Inicializar estructura de datos
            self.prices_data = {
                'HOSO': {},
                'HLSO': {},
                'P&D IQF': {},
                'P&D BLOQUE': {},
                'PuD-EUROPA': {}
            }
            
            # Agregar EZ PEEL a los productos
            self.prices_data['EZ PEEL'] = {}
            
            # Mapear las columnas según la estructura encontrada
            # Sección PRECIOS FOB (filas 13-23)
            fob_product_columns = {
                'HOSO': {'talla_col': 1, 'precio_kg_col': 2, 'precio_lb_col': 3},
                'HLSO': {'talla_col': 5, 'precio_kg_col': 6, 'precio_lb_col': 7},
                'P&D IQF': {'talla_col': 9, 'precio_kg_col': 10, 'precio_lb_col': 11},
                'P&D BLOQUE': {'talla_col': 14, 'precio_kg_col': 15, 'precio_lb_col': 16},
                'PuD-EUROPA': {'talla_col': 18, 'precio_kg_col': 19, 'precio_lb_col': 20}
            }
            
            # Sección EZ PEEL (filas 27-38)
            ez_peel_columns = {
                'EZ PEEL': {'talla_col': 1, 'precio_kg_col': 2, 'precio_lb_col': 3}
            }
            
            # Leer factores de costo, glaseo y flete (columnas de la derecha)
            costo_fijo = 0.25  # Default
            factor_glaseo = 0.7  # Default
            flete = 0.20  # Default
            
            try:
                # Intentar leer los valores reales del Excel
                if len(df.columns) > 25:  # Si hay suficientes columnas
                    costo_val = df.iloc[15, 25]  # Aproximadamente donde está COSTO FIJO
                    if pd.notna(costo_val) and isinstance(costo_val, (int, float)):
                        costo_fijo = float(costo_val)
                    
                    glaseo_val = df.iloc[15, 27]  # Aproximadamente donde está GLASEO
                    if pd.notna(glaseo_val) and isinstance(glaseo_val, (int, float)):
                        factor_glaseo = float(glaseo_val)
                    
                    flete_val = df.iloc[15, 29]  # Aproximadamente donde está FLETE
                    if pd.notna(flete_val) and isinstance(flete_val, (int, float)):
                        flete = float(flete_val)
            except:
                pass  # Usar valores por defecto
            
            # Procesar sección PRECIOS FOB (filas 13-23)
            for i in range(13, 24):
                if i >= len(df):
                    break
                for product, cols in fob_product_columns.items():
                    try:
                        talla = str(df.iloc[i, cols['talla_col']]).strip()
                        precio_kg = df.iloc[i, cols['precio_kg_col']]
                        precio_lb = df.iloc[i, cols['precio_lb_col']]
                        
                        # Verificar que la talla tenga formato válido (ej: 16/20)
                        if '/' in talla and talla != 'nan':
                            # Convertir precios a float si es posible
                            try:
                                precio_kg = float(precio_kg) if pd.notna(precio_kg) else 0
                                precio_lb = float(precio_lb) if pd.notna(precio_lb) else 0
                            except:
                                precio_kg = 0
                                precio_lb = 0
                            
                            if precio_kg > 0:  # Solo agregar si tiene precio válido
                                self.prices_data[product][talla] = {
                                    'precio_kg': precio_kg,
                                    'precio_lb': precio_lb,
                                    'producto': product,
                                    'talla': talla,
                                    'costo_fijo': costo_fijo,
                                    'factor_glaseo': factor_glaseo,
                                    'flete': flete
                                }
                    except Exception as e:
                        continue  # Saltar errores en filas individuales
            
            # Procesar sección EZ PEEL (filas 27-38)
            for i in range(27, 39):
                if i >= len(df):
                    break
                for product, cols in ez_peel_columns.items():
                    try:
                        talla = str(df.iloc[i, cols['talla_col']]).strip()
                        precio_kg = df.iloc[i, cols['precio_kg_col']]
                        precio_lb = df.iloc[i, cols['precio_lb_col']]
                        
                        # Verificar que la talla tenga formato válido (ej: 16/20)
                        if '/' in talla and talla != 'nan':
                            # Convertir precios a float si es posible
                            try:
                                precio_kg = float(precio_kg) if pd.notna(precio_kg) else 0
                                precio_lb = float(precio_lb) if pd.notna(precio_lb) else 0
                            except:
                                precio_kg = 0
                                precio_lb = 0
                            
                            if precio_kg > 0:  # Solo agregar si tiene precio válido
                                self.prices_data[product][talla] = {
                                    'precio_kg': precio_kg,
                                    'precio_lb': precio_lb,
                                    'producto': product,
                                    'talla': talla,
                                    'costo_fijo': costo_fijo,
                                    'factor_glaseo': factor_glaseo,
                                    'flete': flete
                                }
                    except Exception as e:
                        continue  # Saltar errores en filas individuales
            
            # Contar total de tallas cargadas
            total_sizes = sum(len(product_data) for product_data in self.prices_data.values())
            logger.info(f"Datos cargados exitosamente: {total_sizes} tallas en {len(self.prices_data)} productos")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cargando Excel: {str(e)}")
            self.create_sample_data()
            return False
    
    def create_sample_data(self):
        """
        Crea datos de ejemplo si no existe el archivo Excel
        """
        logger.info("Creando datos de ejemplo...")
        self.prices_data = {
            'HLSO': {
                "16/20": {"precio_kg": 11.45, "precio_lb": 5.19, "producto": "HLSO", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 10.24, "precio_lb": 4.64, "producto": "HLSO", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "26/30": {"precio_kg": 9.83, "precio_lb": 4.46, "producto": "HLSO", "talla": "26/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'P&D IQF': {
                "16/20": {"precio_kg": 13.56, "precio_lb": 6.15, "producto": "P&D IQF", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'HOSO': {},
            'P&D BLOQUE': {},
            'PuD-EUROPA': {},
            'EZ PEEL': {}
        }
    
    def get_price_data(self, size: str, product: str = 'HLSO') -> Optional[Dict]:
        """
        Obtiene los datos de precio para una talla específica y producto
        """
        # Primero intentar con datos locales
        if not self.prices_data:
            self.load_data()
        
        # Si aún no hay datos locales, verificar Google Sheets directamente
        if not self.prices_data and self.google_sheets_service.prices_data:
            self.prices_data = self.google_sheets_service.prices_data
            logger.info("✅ Datos sincronizados desde Google Sheets")
        
        if self.prices_data and product in self.prices_data:
            return self.prices_data[product].get(size)
        return None
    
    def get_available_sizes(self, product: str = 'HLSO') -> list:
        """
        Retorna las tallas disponibles para un producto específico
        """
        # Primero intentar con datos locales
        if not self.prices_data:
            self.load_data()
        
        # Si aún no hay datos locales, verificar Google Sheets directamente
        if not self.prices_data and self.google_sheets_service.prices_data:
            self.prices_data = self.google_sheets_service.prices_data
            logger.info("✅ Datos sincronizados desde Google Sheets")
        
        if self.prices_data and product in self.prices_data:
            sizes = list(self.prices_data[product].keys())
            logger.info(f"Tallas encontradas para {product}: {sizes}")
            return sizes
        
        logger.warning(f"No se encontraron tallas para {product}")
        return []
    
    def get_available_products(self) -> list:
        """
        Retorna los productos disponibles
        """
        if not self.prices_data:
            self.load_data()
        
        return [product for product in self.prices_data.keys() if self.prices_data[product]]
    
    def get_all_prices(self) -> Dict:
        """
        Retorna todos los precios organizados por producto
        """
        if not self.prices_data:
            self.load_data()
        
        return self.prices_data
    
    def reload_data(self) -> bool:
        """
        Recarga los datos desde Google Sheets o Excel
        """
        # Recargar desde Google Sheets primero
        if self.google_sheets_service.reload_data():
            self.prices_data = self.google_sheets_service.prices_data
            return True
        else:
            # Fallback a Excel local
            return self.load_excel_data()
