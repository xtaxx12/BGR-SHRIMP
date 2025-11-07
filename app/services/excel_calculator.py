import json
import logging
import os
import time

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

class ExcelCalculatorService:
    def __init__(self):
        self.gc = None
        self.sheet = None
        self.worksheet = None
        self.setup_google_sheets()

    def setup_google_sheets(self):
        """
        Configura la conexión con Google Sheets para escritura
        """
        try:
            # Obtener credenciales desde variables de entorno
            credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            sheet_id = os.getenv("GOOGLE_SHEETS_ID")

            if not credentials_json or not sheet_id:
                logger.warning("Credenciales de Google Sheets no configuradas para cálculos")
                return

            # Parsear las credenciales JSON
            credentials_dict = json.loads(credentials_json)

            # Configurar los scopes necesarios (incluyendo escritura)
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',  # Lectura y escritura
                'https://www.googleapis.com/auth/drive'
            ]

            # Crear credenciales
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=scopes
            )

            # Conectar con Google Sheets
            self.gc = gspread.authorize(credentials)
            self.sheet = self.gc.open_by_key(sheet_id)

            # Obtener la hoja de cálculo principal
            self.worksheet = self.sheet.worksheet("PRECIOS FOB")

            logger.info("✅ Conexión con Google Sheets para cálculos establecida")

        except Exception as e:
            logger.error(f"❌ Error configurando Google Sheets para cálculos: {str(e)}")
            self.gc = None

    def calculate_prices(self, talla: str, precio_kg: float) -> dict | None:
        """
        Calcula precios usando las fórmulas del Excel
        Escribe en X33 (talla) y Y33 (precio), luego lee los resultados calculados
        """
        try:
            if not self.worksheet:
                logger.warning("Google Sheets no disponible para cálculos")
                return self._calculate_manual(precio_kg)

            logger.info(f"🧮 Calculando precios para {talla} a ${precio_kg}/kg usando Excel")

            # Escribir la talla en X33 y el precio en Y33
            self.worksheet.update('X33', talla)
            self.worksheet.update('Y33', precio_kg)

            # Esperar un momento para que se actualicen las fórmulas
            time.sleep(1)

            # Leer los valores calculados
            # Según tu imagen:
            # AA33: PRECIO FOB (=Y33-AA28)
            # AC33: PRECIO CON GLASEO (=AA33*AC28)
            # AE33: PRECIO CON GLASEO Y FLETE (=AC33+AA28+AE28)

            precio_fob = self.worksheet.acell('AA33').value
            precio_glaseo = self.worksheet.acell('AC33').value
            precio_flete = self.worksheet.acell('AE33').value

            # También leer los factores para información
            costo_fijo = self.worksheet.acell('AA28').value  # COSTO FIJO
            factor_glaseo = self.worksheet.acell('AC28').value  # GLASEO
            flete = self.worksheet.acell('AE28').value  # FLETE

            # Convertir a números
            try:
                precio_fob_num = float(precio_fob) if precio_fob else 0
                precio_glaseo_num = float(precio_glaseo) if precio_glaseo else 0
                precio_flete_num = float(precio_flete) if precio_flete else 0
                costo_fijo_num = float(costo_fijo) if costo_fijo else 0.29
                factor_glaseo_num = float(factor_glaseo) if factor_glaseo else 0.7
                flete_num = float(flete) if flete else 0.2
            except (ValueError, TypeError):
                logger.error("Error convirtiendo valores calculados a números")
                return self._calculate_manual(precio_kg)

            result = {
                'talla': talla,
                'precio_kg_original': precio_kg,
                'precio_lb_original': precio_kg / 2.20462,  # Conversión kg a lb
                'precio_fob_kg': precio_fob_num,
                'precio_fob_lb': precio_fob_num / 2.20462,
                'precio_glaseo_kg': precio_glaseo_num,
                'precio_glaseo_lb': precio_glaseo_num / 2.20462,
                'precio_flete_kg': precio_flete_num,
                'precio_flete_lb': precio_flete_num / 2.20462,
                'factores': {
                    'costo_fijo': costo_fijo_num,
                    'factor_glaseo': factor_glaseo_num,
                    'flete': flete_num
                },
                'calculado_con': 'Google Sheets Excel'
            }

            logger.info(f"✅ Cálculo completado: FOB=${precio_fob_num:.2f}, Glaseo=${precio_glaseo_num:.2f}, Flete=${precio_flete_num:.2f}")
            return result

        except Exception as e:
            logger.error(f"❌ Error calculando precios con Excel: {str(e)}")
            return self._calculate_manual(precio_kg)

    def _calculate_manual(self, precio_kg: float) -> dict:
        """
        Cálculo manual usando las mismas fórmulas si Google Sheets no está disponible
        """
        logger.info("🔢 Usando cálculo manual (fórmulas locales)")

        # Valores por defecto basados en tu Excel
        costo_fijo = 0.29
        factor_glaseo = 0.7
        flete = 0.2

        # Aplicar las mismas fórmulas
        precio_fob = precio_kg - costo_fijo  # =Y33-AA28
        precio_glaseo = precio_fob * factor_glaseo  # =AA33*AC28
        precio_flete = precio_glaseo + costo_fijo + flete  # =AC33+AA28+AE28

        return {
            'precio_kg_original': precio_kg,
            'precio_lb_original': precio_kg / 2.20462,
            'precio_fob_kg': precio_fob,
            'precio_fob_lb': precio_fob / 2.20462,
            'precio_glaseo_kg': precio_glaseo,
            'precio_glaseo_lb': precio_glaseo / 2.20462,
            'precio_flete_kg': precio_flete,
            'precio_flete_lb': precio_flete / 2.20462,
            'factores': {
                'costo_fijo': costo_fijo,
                'factor_glaseo': factor_glaseo,
                'flete': flete
            },
            'calculado_con': 'Fórmulas locales'
        }

    def get_base_price(self, talla: str, producto: str = 'HLSO') -> float | None:
        """
        Obtiene el precio base por kilo desde la tabla de precios
        """
        try:
            if not self.worksheet:
                return None

            # Mapear productos a sus columnas en el Excel
            product_columns = {
                'HOSO': {'talla_col': 'B', 'precio_col': 'C'},
                'HLSO': {'talla_col': 'F', 'precio_col': 'G'},
                'P&D IQF': {'talla_col': 'J', 'precio_col': 'K'},
                'P&D BLOQUE': {'talla_col': 'O', 'precio_col': 'P'},
                'PuD-EUROPA': {'talla_col': 'S', 'precio_col': 'T'}
            }

            if producto not in product_columns:
                return None

            cols = product_columns[producto]

            # Buscar la talla en las filas 14-24 (sección PRECIOS FOB)
            for row in range(14, 25):
                talla_cell = f"{cols['talla_col']}{row}"
                precio_cell = f"{cols['precio_col']}{row}"

                talla_value = self.worksheet.acell(talla_cell).value
                if talla_value and str(talla_value).strip() == talla:
                    precio_value = self.worksheet.acell(precio_cell).value
                    if precio_value:
                        return float(precio_value)

            return None

        except Exception as e:
            logger.error(f"Error obteniendo precio base: {str(e)}")
            return None
