import pandas as pd
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ExcelService:
    def __init__(self, excel_path: str = "data/precios_fob.xlsx"):
        self.excel_path = excel_path
        self.prices_data = None
        self.load_excel_data()
    
    def load_excel_data(self) -> bool:
        """
        Carga los datos del archivo Excel (hoja PRECIOS FOB)
        """
        try:
            if not os.path.exists(self.excel_path):
                logger.warning(f"Archivo Excel no encontrado: {self.excel_path}")
                # Crear datos de ejemplo si no existe el archivo
                self.create_sample_data()
                return True
            
            # Leer la hoja PRECIOS FOB
            df = pd.read_excel(self.excel_path, sheet_name="PRECIOS FOB")
            
            # Convertir a diccionario para fácil acceso
            self.prices_data = {}
            
            for _, row in df.iterrows():
                size = str(row.get('TALLA', '')).strip()
                if size and size != 'nan':
                    self.prices_data[size] = {
                        'precio_base': float(row.get('PRECIO_BASE', 0)),
                        'producto': str(row.get('PRODUCTO', 'HLSO')),
                        'costo_fijo': float(row.get('COSTO_FIJO', 0.25)),
                        'factor_glaseo': float(row.get('FACTOR_GLASEO', 0.7)),
                        'flete': float(row.get('FLETE', 0.20))
                    }
            
            logger.info(f"Datos cargados exitosamente: {len(self.prices_data)} tallas")
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
            "8/12": {"precio_base": 12.50, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
            "13/15": {"precio_base": 10.80, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
            "16/20": {"precio_base": 8.55, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
            "21/25": {"precio_base": 7.90, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
            "26/30": {"precio_base": 7.20, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
            "31/35": {"precio_base": 6.80, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
            "36/40": {"precio_base": 6.40, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
            "41/50": {"precio_base": 5.90, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
            "51/60": {"precio_base": 5.40, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20},
            "61/70": {"precio_base": 4.90, "producto": "HLSO", "costo_fijo": 0.25, "factor_glaseo": 0.7, "flete": 0.20}
        }
    
    def get_price_data(self, size: str) -> Optional[Dict]:
        """
        Obtiene los datos de precio para una talla específica
        """
        if not self.prices_data:
            self.load_excel_data()
        
        return self.prices_data.get(size)
    
    def get_available_sizes(self) -> list:
        """
        Retorna las tallas disponibles
        """
        if not self.prices_data:
            self.load_excel_data()
        
        return list(self.prices_data.keys()) if self.prices_data else []
    
    def reload_data(self) -> bool:
        """
        Recarga los datos del Excel
        """
        return self.load_excel_data()