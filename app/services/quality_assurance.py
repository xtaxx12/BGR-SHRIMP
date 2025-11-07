"""
Sistema de Aseguramiento de Calidad para BGR Shrimp Bot
Valida datos, precios, y respuestas antes de enviarlas al cliente
"""
import logging

logger = logging.getLogger(__name__)

class QualityAssuranceService:
    """
    Servicio de QA que valida todos los datos antes de enviarlos al cliente
    """

    def __init__(self):
        # Rangos válidos de precios por producto (USD/kg)
        self.price_ranges = {
            'HOSO': {'min': 3.00, 'max': 8.00},
            'HLSO': {'min': 4.00, 'max': 12.00},
            'P&D IQF': {'min': 6.00, 'max': 15.00},
            'P&D BLOQUE': {'min': 6.00, 'max': 15.00},
            'EZ PEEL': {'min': 7.00, 'max': 16.00},
            'PuD-EUROPA': {'min': 8.00, 'max': 18.00},
            'PuD-EEUU': {'min': 8.00, 'max': 18.00},
            'COOKED': {'min': 7.00, 'max': 16.00},
        }

        # Tallas válidas
        self.valid_sizes = [
            'U15', '16/20', '20/30', '21/25', '26/30', '30/40',
            '31/35', '36/40', '40/50', '41/50', '50/60', '51/60',
            '60/70', '61/70', '70/80', '71/90'
        ]

        # Productos válidos
        self.valid_products = [
            'HOSO', 'HLSO', 'P&D IQF', 'P&D BLOQUE', 'EZ PEEL',
            'PuD-EUROPA', 'PuD-EEUU', 'COOKED', 'PRE-COCIDO', 'COCIDO SIN TRATAR'
        ]

        # Rangos válidos de glaseo
        self.glaseo_range = {'min': 0, 'max': 50}  # 0% a 50%

        # Rangos válidos de flete
        self.flete_range = {'min': 0.05, 'max': 2.00}  # $0.05 a $2.00 por kg

    def validate_product(self, product: str) -> tuple[bool, str | None]:
        """
        Valida que el producto sea válido
        
        Returns:
            (is_valid, error_message)
        """
        if not product:
            return False, "Producto no especificado"

        if product not in self.valid_products:
            return False, f"Producto '{product}' no es válido. Productos válidos: {', '.join(self.valid_products)}"

        return True, None

    def validate_size(self, size: str) -> tuple[bool, str | None]:
        """
        Valida que la talla sea válida
        
        Returns:
            (is_valid, error_message)
        """
        if not size:
            return False, "Talla no especificada"

        if size not in self.valid_sizes:
            return False, f"Talla '{size}' no es válida. Tallas válidas: {', '.join(self.valid_sizes)}"

        return True, None

    def validate_glaseo(self, glaseo_percentage: int) -> tuple[bool, str | None]:
        """
        Valida que el glaseo esté en rango válido
        
        Returns:
            (is_valid, error_message)
        """
        if glaseo_percentage is None:
            return False, "Glaseo no especificado"

        if glaseo_percentage < self.glaseo_range['min'] or glaseo_percentage > self.glaseo_range['max']:
            return False, f"Glaseo {glaseo_percentage}% fuera de rango válido ({self.glaseo_range['min']}% - {self.glaseo_range['max']}%)"

        return True, None

    def validate_flete(self, flete: float) -> tuple[bool, str | None]:
        """
        Valida que el flete esté en rango válido
        
        Returns:
            (is_valid, error_message)
        """
        if flete is None:
            return True, None  # Flete es opcional

        if flete < self.flete_range['min'] or flete > self.flete_range['max']:
            return False, f"Flete ${flete:.2f} fuera de rango válido (${self.flete_range['min']:.2f} - ${self.flete_range['max']:.2f})"

        return True, None

    def validate_price(self, product: str, price_kg: float) -> tuple[bool, str | None]:
        """
        Valida que el precio esté en rango esperado para el producto
        
        Returns:
            (is_valid, error_message)
        """
        if price_kg is None or price_kg <= 0:
            return False, "Precio inválido o no especificado"

        if product not in self.price_ranges:
            # Si no tenemos rango para este producto, aceptar cualquier precio razonable
            if price_kg < 1.00 or price_kg > 30.00:
                return False, f"Precio ${price_kg:.2f}/kg parece fuera de rango razonable ($1.00 - $30.00)"
            return True, None

        price_range = self.price_ranges[product]

        if price_kg < price_range['min'] or price_kg > price_range['max']:
            logger.warning(f"⚠️ Precio ${price_kg:.2f}/kg para {product} fuera de rango esperado (${price_range['min']:.2f} - ${price_range['max']:.2f})")
            return False, f"Precio ${price_kg:.2f}/kg para {product} fuera de rango esperado (${price_range['min']:.2f} - ${price_range['max']:.2f})"

        return True, None

    def validate_price_calculation(self, price_info: dict) -> tuple[bool, list[str]]:
        """
        Valida que los cálculos de precio sean correctos
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Validar que existan los campos necesarios
        required_fields = ['producto', 'talla', 'precio_kg', 'factor_glaseo']
        for field in required_fields:
            if field not in price_info or price_info[field] is None:
                errors.append(f"Campo requerido '{field}' faltante")

        if errors:
            return False, errors

        # Validar producto
        is_valid, error = self.validate_product(price_info['producto'])
        if not is_valid:
            errors.append(error)

        # Validar talla
        is_valid, error = self.validate_size(price_info['talla'])
        if not is_valid:
            errors.append(error)

        # Validar glaseo
        if 'glaseo_percentage' in price_info:
            is_valid, error = self.validate_glaseo(price_info['glaseo_percentage'])
            if not is_valid:
                errors.append(error)

        # Validar flete
        if 'flete' in price_info:
            is_valid, error = self.validate_flete(price_info['flete'])
            if not is_valid:
                errors.append(error)

        # Validar precio base
        is_valid, error = self.validate_price(price_info['producto'], price_info['precio_kg'])
        if not is_valid:
            errors.append(error)

        # Validar cálculos matemáticos
        try:
            precio_base = price_info['precio_kg']
            factor_glaseo = price_info['factor_glaseo']
            costo_fijo = price_info.get('costo_fijo', 0.29)

            # Verificar que el factor de glaseo sea razonable
            if factor_glaseo < 0.5 or factor_glaseo > 1.0:
                errors.append(f"Factor de glaseo {factor_glaseo} fuera de rango razonable (0.5 - 1.0)")

            # Verificar cálculo de precio con glaseo
            if 'precio_glaseo_kg' in price_info:
                precio_neto = precio_base - costo_fijo
                precio_glaseo_esperado = precio_neto * factor_glaseo
                precio_glaseo_calculado = price_info['precio_glaseo_kg']

                # Tolerancia de 0.01 para errores de redondeo
                if abs(precio_glaseo_calculado - precio_glaseo_esperado) > 0.01:
                    errors.append(f"Error en cálculo de glaseo: esperado ${precio_glaseo_esperado:.2f}, calculado ${precio_glaseo_calculado:.2f}")

            # Verificar cálculo de precio CFR
            if 'precio_final_kg' in price_info and 'precio_fob_con_glaseo_kg' in price_info and 'flete' in price_info:
                precio_cfr_esperado = price_info['precio_fob_con_glaseo_kg'] + price_info['flete']
                precio_cfr_calculado = price_info['precio_final_kg']

                if abs(precio_cfr_calculado - precio_cfr_esperado) > 0.01:
                    errors.append(f"Error en cálculo CFR: esperado ${precio_cfr_esperado:.2f}, calculado ${precio_cfr_calculado:.2f}")

        except Exception as e:
            errors.append(f"Error validando cálculos: {str(e)}")

        return len(errors) == 0, errors

    def validate_multiple_products(self, products_info: list[dict]) -> tuple[bool, dict]:
        """
        Valida múltiples productos
        
        Returns:
            (is_valid, validation_report)
        """
        report = {
            'total_products': len(products_info),
            'valid_products': 0,
            'invalid_products': 0,
            'errors': [],
            'warnings': []
        }

        for i, product_info in enumerate(products_info, 1):
            is_valid, errors = self.validate_price_calculation(product_info)

            if is_valid:
                report['valid_products'] += 1
            else:
                report['invalid_products'] += 1
                product_name = f"{product_info.get('producto', 'Unknown')} {product_info.get('talla', 'Unknown')}"
                report['errors'].append({
                    'product': product_name,
                    'index': i,
                    'errors': errors
                })

        return report['invalid_products'] == 0, report

    def generate_validation_report(self, validation_result: tuple[bool, dict]) -> str:
        """
        Genera un reporte legible de validación
        """
        is_valid, report = validation_result

        if isinstance(report, list):
            # Es una lista de errores
            if not report:
                return "✅ Validación exitosa"
            else:
                return "❌ Errores encontrados:\n" + "\n".join([f"  • {error}" for error in report])

        # Es un reporte de múltiples productos
        lines = []
        lines.append("📊 Reporte de Validación:")
        lines.append(f"  Total productos: {report['total_products']}")
        lines.append(f"  ✅ Válidos: {report['valid_products']}")
        lines.append(f"  ❌ Inválidos: {report['invalid_products']}")

        if report['errors']:
            lines.append("\n❌ Errores encontrados:")
            for error_info in report['errors']:
                lines.append(f"\n  Producto: {error_info['product']}")
                for error in error_info['errors']:
                    lines.append(f"    • {error}")

        if report['warnings']:
            lines.append("\n⚠️ Advertencias:")
            for warning in report['warnings']:
                lines.append(f"  • {warning}")

        return "\n".join(lines)

    def log_validation(self, validation_result: tuple[bool, any], context: str = ""):
        """
        Registra el resultado de validación en los logs
        """
        is_valid, details = validation_result

        if is_valid:
            logger.info(f"✅ QA: Validación exitosa {context}")
        else:
            logger.warning(f"⚠️ QA: Validación fallida {context}")
            logger.warning(f"Detalles: {details}")

# Instancia global del servicio de QA
qa_service = QualityAssuranceService()
