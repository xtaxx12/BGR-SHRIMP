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
            logger.debug("Parseando credenciales JSON...")
            credentials_dict = json.loads(credentials_json)
            logger.debug(f"Service account: {credentials_dict.get('client_email', 'N/A')}")
            
            # Configurar los scopes necesarios
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            logger.debug(f"Configurando scopes: {scopes}")
            
            # Crear credenciales
            logger.debug("Creando credenciales...")
            credentials = Credentials.from_service_account_info(
                credentials_dict, 
                scopes=scopes
            )
            
            # Conectar con Google Sheets
            logger.debug("Autorizando cliente gspread...")
            self.gc = gspread.authorize(credentials)
            
            logger.debug(f"Abriendo hoja con ID: {sheet_id}")
            self.sheet = self.gc.open_by_key(sheet_id)
            
            logger.debug("Conexión con Google Sheets establecida exitosamente")
            self.load_sheets_data()
            
        except Exception as e:
            logger.error(f"Error configurando Google Sheets: {str(e)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
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
            
            # Listar todas las hojas disponibles
            worksheets = self.sheet.worksheets()
            logger.debug(f"Hojas disponibles: {[ws.title for ws in worksheets]}")
            
            # Intentar encontrar la hoja correcta
            worksheet = None
            possible_names = ["PRECIOS FOB", "PRECIOS", "FOB", "Sheet1", "Hoja1"]
            
            for name in possible_names:
                try:
                    worksheet = self.sheet.worksheet(name)
                    logger.debug(f"Usando hoja: {name}")
                    break
                except:
                    continue
            
            if not worksheet:
                # Usar la primera hoja disponible
                worksheet = worksheets[0]
                logger.info(f"Usando primera hoja disponible: {worksheet.title}")
            
            # Obtener todos los valores
            all_values = worksheet.get_all_values()
            logger.debug(f"Datos leídos: {len(all_values)} filas")
            
            # Mostrar las primeras filas para debug
            if all_values:
                logger.debug(f"Primera fila: {all_values[0][:10]}...")
                if len(all_values) > 1:
                    logger.debug(f"Segunda fila: {all_values[1][:10]}...")
            
            # Convertir a DataFrame para facilitar el procesamiento
            df = pd.DataFrame(all_values)
            
            # Inicializar estructura de datos
            self.prices_data = {
                'HOSO': {},
                'HLSO': {},
                'P&D IQF': {},
                'P&D BLOQUE': {},
                'PuD-EUROPA': {},
                'EZ PEEL': {},
                'PuD-EEUU': {},
                'COOKED': {},
                'PRE-COCIDO': {},
                'COCIDO SIN TRATAR': {}
            }
            
            # Mapear las columnas según la estructura real de la hoja
            # Basado en las ubicaciones: B14:D14, F14:H14, J14:L14, O14:Q14, S14:U14 (fila 14)
            # y B27:D27, F27:H27, J27:L27, O27:Q27, S27:U27 (fila 27)
            
            # Sección superior (fila 14 - índice 13)
            fob_product_columns = {
                'HOSO': {'talla_col': 1, 'precio_kg_col': 2, 'precio_lb_col': 3},      # B14:D14
                'HLSO': {'talla_col': 5, 'precio_kg_col': 6, 'precio_lb_col': 7},      # F14:H14  
                'P&D IQF': {'talla_col': 9, 'precio_kg_col': 10, 'precio_lb_col': 11}, # J14:L14
                'P&D BLOQUE': {'talla_col': 14, 'precio_kg_col': 15, 'precio_lb_col': 16}, # O14:Q14
                'PuD-EUROPA': {'talla_col': 18, 'precio_kg_col': 19, 'precio_lb_col': 20}  # S14:U14
            }
            
            # Sección inferior (fila 27 - índice 26)  
            ez_peel_columns = {
                'EZ PEEL': {'talla_col': 1, 'precio_kg_col': 2, 'precio_lb_col': 3},    # B27:D27
                'PuD-EEUU': {'talla_col': 5, 'precio_kg_col': 6, 'precio_lb_col': 7},   # F27:H27
                'COOKED': {'talla_col': 9, 'precio_kg_col': 10, 'precio_lb_col': 11},   # J27:L27
                'PRE-COCIDO': {'talla_col': 14, 'precio_kg_col': 15, 'precio_lb_col': 16}, # O27:Q27
                'COCIDO SIN TRATAR': {'talla_col': 18, 'precio_kg_col': 19, 'precio_lb_col': 20} # S27:U27
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
            
            # Procesar sección superior (filas 15-25, índices 14-24)
            logger.debug("Procesando sección superior (filas 15-25)...")
            for i in range(14, min(25, len(df))):
                for product, cols in fob_product_columns.items():
                    try:
                        if len(df.iloc[i]) <= max(cols['talla_col'], cols['precio_kg_col'], cols['precio_lb_col']):
                            continue
                            
                        talla = str(df.iloc[i, cols['talla_col']]).strip()
                        precio_kg = df.iloc[i, cols['precio_kg_col']]
                        precio_lb = df.iloc[i, cols['precio_lb_col']]
                        
                        logger.debug(f"Leyendo {product} fila {i+1}: talla='{talla}', kg='{precio_kg}', lb='{precio_lb}'")
                        
                        # Verificar que la talla tenga formato válido (ej: 16/20)
                        if (('/' in talla or talla.startswith('U') or talla.endswith('/100')) and talla != 'nan' and talla and talla != '' and talla != 'TALLA'):
                            # Convertir precios a float si es posible
                            try:
                                precio_kg = self._clean_price(precio_kg)
                                precio_lb = self._clean_price(precio_lb)
                            except:
                                precio_kg = 0
                                precio_lb = 0
                            
                            # Agregar todas las tallas, incluso sin precio
                            self.prices_data[product][talla] = {
                                'precio_kg': precio_kg,
                                'precio_lb': precio_lb,
                                'producto': product,
                                'talla': talla,
                                'costo_fijo': costo_fijo,
                                'factor_glaseo': factor_glaseo,
                                'flete': flete,
                                'sin_precio': precio_kg == 0
                            }
                            
                            if precio_kg > 0:
                                logger.info(f"✅ Agregado {product} {talla}: ${precio_kg}/kg")
                            else:
                                logger.info(f"⚠️ Agregado {product} {talla}: Sin precio establecido")
                    except Exception as e:
                        logger.error(f"Error procesando {product} fila {i+1}: {e}")
                        continue
            
            # Procesar sección inferior (filas 28-38, índices 27-37)
            logger.debug("Procesando sección inferior (filas 28-38)...")
            for i in range(27, min(38, len(df))):
                for product, cols in ez_peel_columns.items():
                    try:
                        if len(df.iloc[i]) <= max(cols['talla_col'], cols['precio_kg_col'], cols['precio_lb_col']):
                            continue
                            
                        talla = str(df.iloc[i, cols['talla_col']]).strip()
                        precio_kg = df.iloc[i, cols['precio_kg_col']]
                        precio_lb = df.iloc[i, cols['precio_lb_col']]
                        
                        logger.debug(f"Leyendo {product} fila {i+1}: talla='{talla}', kg='{precio_kg}', lb='{precio_lb}'")
                        
                        # Verificar que la talla tenga formato válido (ej: 16/20)
                        if (('/' in talla or talla.startswith('U') or talla.endswith('/100')) and talla != 'nan' and talla and talla != '' and talla != 'TALLA'):
                            # Convertir precios a float si es posible
                            try:
                                precio_kg = self._clean_price(precio_kg)
                                precio_lb = self._clean_price(precio_lb)
                            except:
                                precio_kg = 0
                                precio_lb = 0
                            
                            # Agregar todas las tallas, incluso sin precio
                            self.prices_data[product][talla] = {
                                'precio_kg': precio_kg,
                                'precio_lb': precio_lb,
                                'producto': product,
                                'talla': talla,
                                'costo_fijo': costo_fijo,
                                'factor_glaseo': factor_glaseo,
                                'flete': flete,
                                'sin_precio': precio_kg == 0
                            }
                            
                            if precio_kg > 0:
                                logger.info(f"✅ Agregado {product} {talla}: ${precio_kg}/kg")
                            else:
                                logger.info(f"⚠️ Agregado {product} {talla}: Sin precio establecido")
                    except Exception as e:
                        logger.error(f"Error procesando {product} fila {i+1}: {e}")
                        continue
            
            # Contar total de tallas cargadas
            total_sizes = sum(len(product_data) for product_data in self.prices_data.values())
            logger.info(f"Datos cargados desde Google Sheets: {total_sizes} tallas en {len(self.prices_data)} productos")
            
            # Debug: mostrar algunos productos para verificar
            for product, tallas in self.prices_data.items():
                logger.debug(f"  {product}: {len(tallas)} tallas")
            
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
            # Limpiar el valor: remover espacios, $, y otros caracteres
            cleaned = str(value).strip().replace('$', '').replace(',', '').replace(' ', '')
            if cleaned and cleaned != '-' and cleaned != '':
                float(cleaned)
                return True
            return False
        except (ValueError, TypeError):
            return False
    
    def _clean_price(self, value):
        """
        Limpia y convierte un precio a float
        """
        try:
            # Limpiar el valor: remover espacios, $, y otros caracteres
            cleaned = str(value).strip().replace('$', '').replace(',', '').replace(' ', '')
            if cleaned and cleaned != '-' and cleaned != '':
                return float(cleaned)
            return 0.0
        except (ValueError, TypeError):
            return 0.0
    
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
            'HOSO': {
                "20/30": {"precio_kg": 6.42, "precio_lb": 2.91, "producto": "HOSO", "talla": "20/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "30/40": {"precio_kg": 5.52, "precio_lb": 2.51, "producto": "HOSO", "talla": "30/40", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "40/50": {"precio_kg": 5.12, "precio_lb": 2.32, "producto": "HOSO", "talla": "40/50", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "50/60": {"precio_kg": 4.82, "precio_lb": 2.19, "producto": "HOSO", "talla": "50/60", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "60/70": {"precio_kg": 4.62, "precio_lb": 2.10, "producto": "HOSO", "talla": "60/70", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "70/80": {"precio_kg": 4.42, "precio_lb": 2.01, "producto": "HOSO", "talla": "70/80", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'PuD-EEUU': {
                "U15": {"precio_kg": 11.85, "precio_lb": 5.38, "producto": "PuD-EEUU", "talla": "U15", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "16/20": {"precio_kg": 10.37, "precio_lb": 4.70, "producto": "PuD-EEUU", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 9.97, "precio_lb": 4.52, "producto": "PuD-EEUU", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "26/30": {"precio_kg": 9.56, "precio_lb": 4.34, "producto": "PuD-EEUU", "talla": "26/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "31/35": {"precio_kg": 9.56, "precio_lb": 4.34, "producto": "PuD-EEUU", "talla": "31/35", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'COOKED': {
                "U15": {"precio_kg": 14.02, "precio_lb": 6.36, "producto": "COOKED", "talla": "U15", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "16/20": {"precio_kg": 12.33, "precio_lb": 5.59, "producto": "COOKED", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 11.87, "precio_lb": 5.39, "producto": "COOKED", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "26/30": {"precio_kg": 11.41, "precio_lb": 5.18, "producto": "COOKED", "talla": "26/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "31/35": {"precio_kg": 11.41, "precio_lb": 5.18, "producto": "COOKED", "talla": "31/35", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'PRE-COCIDO': {
                "U15": {"precio_kg": 12.73, "precio_lb": 5.78, "producto": "PRE-COCIDO", "talla": "U15", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "16/20": {"precio_kg": 11.25, "precio_lb": 5.10, "producto": "PRE-COCIDO", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 10.85, "precio_lb": 4.92, "producto": "PRE-COCIDO", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "26/30": {"precio_kg": 10.45, "precio_lb": 4.74, "producto": "PRE-COCIDO", "talla": "26/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "31/35": {"precio_kg": 10.45, "precio_lb": 4.74, "producto": "PRE-COCIDO", "talla": "31/35", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            },
            'COCIDO SIN TRATAR': {
                "U15": {"precio_kg": 14.97, "precio_lb": 6.79, "producto": "COCIDO SIN TRATAR", "talla": "U15", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "16/20": {"precio_kg": 13.14, "precio_lb": 5.96, "producto": "COCIDO SIN TRATAR", "talla": "16/20", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "21/25": {"precio_kg": 12.64, "precio_lb": 5.73, "producto": "COCIDO SIN TRATAR", "talla": "21/25", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "26/30": {"precio_kg": 12.13, "precio_lb": 5.50, "producto": "COCIDO SIN TRATAR", "talla": "26/30", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
                "31/35": {"precio_kg": 12.13, "precio_lb": 5.50, "producto": "COCIDO SIN TRATAR", "talla": "31/35", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
            }
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
    
    def get_flete_value(self) -> Optional[float]:
        """
        Obtiene el valor del flete desde la celda AE28 de Google Sheets
        Retorna None si no hay valor válido (para que el sistema pida al usuario)
        """
        try:
            if not self.sheet:
                logger.warning("⚠️ Google Sheets no configurado, no hay valor de flete disponible")
                return None  # No hay valor disponible
            
            # Obtener la hoja de trabajo correcta
            worksheets = self.sheet.worksheets()
            worksheet = None
            
            # Buscar la hoja con datos de precios (no gráficos ni hojas pequeñas)
            for ws in worksheets:
                try:
                    # Verificar que la hoja tenga suficientes columnas
                    if ws.col_count >= 30 and 'gráfico' not in ws.title.lower():
                        worksheet = ws
                        break
                except:
                    continue
            
            if not worksheet:
                worksheet = worksheets[0]  # Fallback
            
            # Leer celda AE28 (columna 31, fila 28)
            flete_value = worksheet.cell(28, 31).value
            
            if flete_value and self._is_number(flete_value):
                flete = self._clean_price(flete_value)
                logger.info(f"✅ Flete obtenido de AE28: ${flete}")
                return flete
            else:
                logger.warning(f"⚠️ Valor de flete no encontrado o inválido en AE28: {flete_value}")
                return None  # No hay valor válido
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo flete de AE28: {str(e)}")
            return None  # No hay valor disponible
    
    def get_costo_fijo_value(self) -> float:
        """
        Obtiene el valor del costo fijo - usando valor fijo por ahora
        """
        try:
            # Por ahora usar valor fijo hasta que se configure correctamente la hoja
            logger.info("📊 Usando costo fijo por defecto: $0.29")
            return 0.29
            
            # TODO: Implementar lectura desde Google Sheets cuando esté configurado
            # if not self.sheet:
            #     return 0.29
            # 
            # # Código para leer desde Sheets...
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo costo fijo: {str(e)}")
            return 0.29
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo costo fijo de AA28: {str(e)}")
            return 0.29  # Valor por defecto
