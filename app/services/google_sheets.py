import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
from typing import Dict, Optional
import logging
import json

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.gc = None
        self.sheet = None
        self.prices_data = None
        self.setup_google_sheets()
    
    def setup_google_sheets(self):
        """
        Configura la conexión con Google Sheets
        """
        try:
            # Obtener credenciales desde variables de entorno
            credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            sheet_id = os.getenv("GOOGLE_SHEETS_ID")
            
            if not credentials_json or not sheet_id:
                logger.warning("Credenciales de Google Sheets no configuradas, usando datos de ejemplo")
                self.create_sample_data()
                return
            
            # Parsear las credenciales JSON
            credentials_dict = json.loads(credentials_json)
            
            # Configurar los scopes necesarios
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            
            # Crear credenciales
            credentials = Credentials.from_service_account_info(
                credentials_dict, 
                scopes=scopes
            )
            
            # Conectar con Google Sheets
            self.gc = gspread.authorize(credentials)
            self.sheet = self.gc.open_by_key(sheet_id)
            
            logger.info("Conexión con Google Sheets establecida exitosamente")
            self.load_sheets_data()
            
        except Exception as e:
            logger.error(f"Error configurando Google Sheets: {str(e)}")
            self.create_sample_data()
    
    def load_sheets_data(self) -> bool:
        """
        Carga los datos desde Google Sheets (hoja PRECIOS FOB)
        """
        try:
            if not self.sheet:
                logger.warning("Google Sheets no configurado, usando datos de ejemplo")
                self.create_sample_data()
                return True
            
            # Obtener la hoja PRECIOS FOB
            worksheet = self.sheet.worksheet("PRECIOS FOB")
            
            # Obtener todos los valores
            all_values = worksheet.get_all_values()
            
            # Convertir a DataFrame para facilitar el procesamiento
            df = pd.DataFrame(all_values)
            
            # Inicializar estructura de datos
            self.prices_data = {
                'HOSO': {},
                'HLSO': {},
                'P&D IQF': {},
                'P&D BLOQUE': {},
                'PuD-EUROPA': {},
                'EZ PEEL': {}
            }
            
            # Mapear las columnas según la estructura del Excel original
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
            
            # Leer factores de costo, glaseo y flete
            costo_fijo = 0.25  # Default
            factor_glaseo = 0.7  # Default
            flete = 0.20  # Default
            
            try:
                # Intentar leer los valores reales del Google Sheets
                if len(df.columns) > 25 and len(df) > 15:
                    costo_val = df.iloc[15, 25] if len(df.iloc[15]) > 25 else None
                    if costo_val and self._is_number(costo_val):
                        costo_fijo = float(costo_val)
                    
                    glaseo_val = df.iloc[15, 27] if len(df.iloc[15]) > 27 else None
                    if glaseo_val and self._is_number(glaseo_val):
                        factor_glaseo = float(glaseo_val)
                    
                    flete_val = df.iloc[15, 29] if len(df.iloc[15]) > 29 else None
                    if flete_val and self._is_number(flete_val):
                        flete = float(flete_val)
            except:
                pass  # Usar valores por defecto
            
            # Procesar sección PRECIOS FOB (filas 13-23)
            for i in range(13, min(24, len(df))):
                for product, cols in fob_product_columns.items():
                    try:
                        if len(df.iloc[i]) <= max(cols['talla_col'], cols['precio_kg_col'], cols['precio_lb_col']):
                            continue
                            
                        talla = str(df.iloc[i, cols['talla_col']]).strip()
                        precio_kg = df.iloc[i, cols['precio_kg_col']]
                        precio_lb = df.iloc[i, cols['precio_lb_col']]
                        
                        # Verificar que la talla tenga formato válido (ej: 16/20)
                        if '/' in talla and talla != 'nan' and talla:
                            # Convertir precios a float si es posible
                            try:
                                precio_kg = float(precio_kg) if self._is_number(precio_kg) else 0
                                precio_lb = float(precio_lb) if self._is_number(precio_lb) else 0
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
            for i in range(27, min(39, len(df))):
                for product, cols in ez_peel_columns.items():
                    try:
                        if len(df.iloc[i]) <= max(cols['talla_col'], cols['precio_kg_col'], cols['precio_lb_col']):
                            continue
                            
                        talla = str(df.iloc[i, cols['talla_col']]).strip()
                        precio_kg = df.iloc[i, cols['precio_kg_col']]
                        precio_lb = df.iloc[i, cols['precio_lb_col']]
                        
                        # Verificar que la talla tenga formato válido (ej: 16/20)
                        if '/' in talla and talla != 'nan' and talla:
                            # Convertir precios a float si es posible
                            try:
                                precio_kg = float(precio_kg) if self._is_number(precio_kg) else 0
                                precio_lb = float(precio_lb) if self._is_number(precio_lb) else 0
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
            logger.info(f"Datos cargados desde Google Sheets: {total_sizes} tallas en {len(self.prices_data)} productos")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cargando datos de Google Sheets: {str(e)}")
            self.create_sample_data()
            return False
    
    def _is_number(self, value):
        """
        Verifica si un valor puede ser convertido a número
        """
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def create_sample_data(self):
        """
        Crea datos de ejemplo si no se puede conectar con Google Sheets
        """
        logger.info("Creando datos de ejemplo...")
        self.prices_data = {
            'HLSO': {
                "16/20": {"precio_kg": 8.55, "precio_lb": 3.88, "producto": "HLSO", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 7.89, "precio_lb": 3.58, "producto": "HLSO", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "26/30": {"precio_kg": 7.45, "precio_lb": 3.38, "producto": "HLSO", "talla": "26/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "31/35": {"precio_kg": 7.12, "precio_lb": 3.23, "producto": "HLSO", "talla": "31/35", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "36/40": {"precio_kg": 6.89, "precio_lb": 3.12, "producto": "HLSO", "talla": "36/40", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "41/50": {"precio_kg": 6.45, "precio_lb": 2.93, "producto": "HLSO", "talla": "41/50", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "51/60": {"precio_kg": 6.12, "precio_lb": 2.78, "producto": "HLSO", "talla": "51/60", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "61/70": {"precio_kg": 5.89, "precio_lb": 2.67, "producto": "HLSO", "talla": "61/70", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "71/90": {"precio_kg": 5.45, "precio_lb": 2.47, "producto": "HLSO", "talla": "71/90", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'P&D IQF': {
                "16/20": {"precio_kg": 10.55, "precio_lb": 4.78, "producto": "P&D IQF", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 9.89, "precio_lb": 4.48, "producto": "P&D IQF", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "26/30": {"precio_kg": 9.45, "precio_lb": 4.28, "producto": "P&D IQF", "talla": "26/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "31/35": {"precio_kg": 9.12, "precio_lb": 4.13, "producto": "P&D IQF", "talla": "31/35", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "36/40": {"precio_kg": 8.89, "precio_lb": 4.03, "producto": "P&D IQF", "talla": "36/40", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'P&D BLOQUE': {
                "16/20": {"precio_kg": 9.55, "precio_lb": 4.33, "producto": "P&D BLOQUE", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 8.89, "precio_lb": 4.03, "producto": "P&D BLOQUE", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "26/30": {"precio_kg": 8.45, "precio_lb": 3.83, "producto": "P&D BLOQUE", "talla": "26/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'PuD-EUROPA': {
                "16/20": {"precio_kg": 11.55, "precio_lb": 5.24, "producto": "PuD-EUROPA", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 10.89, "precio_lb": 4.94, "producto": "PuD-EUROPA", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'EZ PEEL': {
                "16/20": {"precio_kg": 9.25, "precio_lb": 4.19, "producto": "EZ PEEL", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 8.59, "precio_lb": 3.90, "producto": "EZ PEEL", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "26/30": {"precio_kg": 8.15, "precio_lb": 3.70, "producto": "EZ PEEL", "talla": "26/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'HOSO': {}
        }
    
    def get_price_data(self, size: str, product: str = 'HLSO') -> Optional[Dict]:
        """
        Obtiene los datos de precio para una talla específica y producto
        """
        if not self.prices_data:
            self.load_sheets_data()
        
        if product in self.prices_data:
            return self.prices_data[product].get(size)
        return None
    
    def get_available_sizes(self, product: str = 'HLSO') -> list:
        """
        Retorna las tallas disponibles para un producto específico
        """
        if not self.prices_data:
            self.load_sheets_data()
        
        if product in self.prices_data:
            return list(self.prices_data[product].keys())
        return []
    
    def get_available_products(self) -> list:
        """
        Retorna los productos disponibles
        """
        if not self.prices_data:
            self.load_sheets_data()
        
        return [product for product in self.prices_data.keys() if self.prices_data[product]]
    
    def get_all_prices(self) -> Dict:
        """
        Retorna todos los precios organizados por producto
        """
        if not self.prices_data:
            self.load_sheets_data()
        
        return self.prices_data
    
    def reload_data(self) -> bool:
        """
        Recarga los datos desde Google Sheets
        """
        return self.load_sheets_data()