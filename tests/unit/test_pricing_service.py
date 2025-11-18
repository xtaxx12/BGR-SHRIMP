"""
Tests unitarios para PricingService

Cubre:
- Cálculo de precios con diferentes parámetros
- Conversión de glaseo a factor
- Manejo de errores y casos edge
- Validación de lógica de negocio
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from decimal import Decimal

from app.services.pricing import PricingService, precise_round


class TestPreciseRound:
    """Tests para la función de redondeo preciso"""

    def test_precise_round_basic(self):
        """Test redondeo básico a 2 decimales"""
        assert precise_round(8.555) == 8.56
        assert precise_round(8.554) == 8.55
        assert precise_round(8.545) == 8.55

    def test_precise_round_no_rounding_needed(self):
        """Test cuando no se necesita redondeo"""
        assert precise_round(8.50) == 8.50
        assert precise_round(10.00) == 10.00

    def test_precise_round_custom_decimals(self):
        """Test redondeo con diferentes decimales"""
        assert precise_round(8.5555, 3) == 8.556
        assert precise_round(8.5554, 3) == 8.555


class TestGlaseoFactor:
    """Tests para conversión de porcentaje de glaseo a factor"""

    @pytest.fixture
    def pricing_service(self):
        """Fixture que proporciona una instancia de PricingService"""
        with patch('app.services.pricing.get_google_sheets_service'), \
             patch('app.services.pricing.ExcelService'), \
             patch('app.services.pricing.ExcelLocalCalculatorService'):
            return PricingService()

    def test_glaseo_10_percent(self, pricing_service):
        """Test factor de glaseo 10% = 0.90"""
        factor = pricing_service.get_glaseo_factor(10)
        assert factor == 0.90

    def test_glaseo_20_percent(self, pricing_service):
        """Test factor de glaseo 20% = 0.80"""
        factor = pricing_service.get_glaseo_factor(20)
        assert factor == 0.80

    def test_glaseo_30_percent(self, pricing_service):
        """Test factor de glaseo 30% = 0.70"""
        factor = pricing_service.get_glaseo_factor(30)
        assert factor == 0.70

    def test_glaseo_invalid_percentage(self, pricing_service):
        """Test porcentaje inválido retorna None"""
        factor = pricing_service.get_glaseo_factor(15)
        assert factor is None

        factor = pricing_service.get_glaseo_factor(0)
        assert factor is None

        factor = pricing_service.get_glaseo_factor(50)
        assert factor is None


class TestCalculateFinalPrice:
    """Tests para cálculo de precio final"""

    @pytest.fixture
    def pricing_service(self):
        with patch('app.services.pricing.get_google_sheets_service'), \
             patch('app.services.pricing.ExcelService'), \
             patch('app.services.pricing.ExcelLocalCalculatorService'):
            return PricingService()

    def test_calculate_final_price_basic(self, pricing_service):
        """
        Test cálculo básico de precio final
        Fórmula: ((base - costo_fijo) * glaseo_factor) + costo_fijo + flete
        """
        base_price = 8.55
        fixed_cost = 1.50
        glaseo_factor = 0.80  # 20% glaseo
        freight = 0.35

        # Cálculo esperado:
        # (8.55 - 1.50) * 0.80 = 7.05 * 0.80 = 5.64
        # 5.64 + 1.50 + 0.35 = 7.49
        expected = 7.49

        result = pricing_service.calculate_final_price(
            base_price, fixed_cost, glaseo_factor, freight
        )

        assert result == expected

    def test_calculate_final_price_no_freight(self, pricing_service):
        """Test cálculo sin flete"""
        base_price = 8.55
        fixed_cost = 1.50
        glaseo_factor = 0.80
        freight = 0

        # (8.55 - 1.50) * 0.80 + 1.50 + 0 = 7.14
        expected = 7.14

        result = pricing_service.calculate_final_price(
            base_price, fixed_cost, glaseo_factor, freight
        )

        assert result == expected

    def test_calculate_final_price_30_percent_glaseo(self, pricing_service):
        """Test con 30% de glaseo (factor 0.70)"""
        base_price = 10.00
        fixed_cost = 1.50
        glaseo_factor = 0.70  # 30% glaseo
        freight = 0.40

        # (10.00 - 1.50) * 0.70 = 8.50 * 0.70 = 5.95
        # 5.95 + 1.50 + 0.40 = 7.85
        expected = 7.85

        result = pricing_service.calculate_final_price(
            base_price, fixed_cost, glaseo_factor, freight
        )

        assert result == expected


class TestGetShrimpPrice:
    """Tests para obtención de precio de camarón"""

    @pytest.fixture
    def pricing_service(self):
        with patch('app.services.pricing.ExcelService') as mock_excel, \
             patch('app.services.pricing.get_google_sheets_service') as mock_sheets, \
             patch('app.services.pricing.ExcelLocalCalculatorService') as mock_calc:

            service = PricingService()
            service.excel_service = mock_excel
            service.sheets_service = mock_sheets
            service.calculator_service = mock_calc

            yield service

    def test_get_price_with_custom_base_price(self, pricing_service):
        """Test con precio base personalizado del usuario"""
        # Mock del calculador
        pricing_service.calculator_service.calculate_prices.return_value = {
            'precio_fob_kg': 9.00,
            'precio_glaseo_kg': 6.00,
            'precio_fob_con_glaseo_kg': 7.50,
            'precio_final_kg': 7.85,
            'precio_neto_kg': 7.50,
            'precio_fob_lb': 4.08,
            'precio_glaseo_lb': 2.72,
            'precio_fob_con_glaseo_lb': 3.40,
            'precio_final_lb': 3.56,
            'precio_neto_lb': 3.40,
            'costo_fijo_used': 1.50,
            'glaseo_factor_used': 0.80,
            'flete_used': 0.35,
        }

        # Mock de Google Sheets
        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50

        user_input = {
            'size': '16/20',
            'product': 'HLSO',
            'precio_base_custom': 9.00,  # Usuario especifica precio
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_solicitado': True,
            'flete_custom': 0.35,
            'usar_libras': False,
        }

        result = pricing_service.get_shrimp_price(user_input)

        # Verificaciones
        assert result is not None
        assert result['precio_fob_kg'] == 9.00
        assert result['precio_final_kg'] == 7.85
        assert result['size'] == '16/20'
        assert result['product'] == 'HLSO'
        assert result['calculo_dinamico'] is True

        # No debería llamar a Excel si se especifica precio custom
        pricing_service.excel_service.get_price_data.assert_not_called()

    def test_get_price_from_excel_when_no_custom_price(self, pricing_service):
        """Test que obtiene precio de Excel cuando no se especifica precio custom"""
        # Mock Excel
        pricing_service.excel_service.get_price_data.return_value = {
            'precio_kg': 8.55,
            'talla': '16/20',
            'producto': 'HLSO'
        }

        # Mock del calculador
        pricing_service.calculator_service.calculate_prices.return_value = {
            'precio_fob_kg': 8.55,
            'precio_glaseo_kg': 5.64,
            'precio_fob_con_glaseo_kg': 7.14,
            'precio_final_kg': 7.49,
            'precio_neto_kg': 7.05,
            'precio_fob_lb': 3.88,
            'precio_glaseo_lb': 2.56,
            'precio_fob_con_glaseo_lb': 3.24,
            'precio_final_lb': 3.40,
            'precio_neto_lb': 3.20,
            'costo_fijo_used': 1.50,
            'glaseo_factor_used': 0.80,
            'flete_used': 0.35,
        }

        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50

        user_input = {
            'size': '16/20',
            'product': 'HLSO',
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_solicitado': True,
            'flete_custom': 0.35,
        }

        result = pricing_service.get_shrimp_price(user_input)

        # Verificaciones
        assert result is not None
        pricing_service.excel_service.get_price_data.assert_called_once_with('16/20', 'HLSO')

    def test_get_price_missing_size(self, pricing_service):
        """Test que retorna None si falta la talla"""
        user_input = {
            'product': 'HLSO',
            'glaseo_factor': 0.80,
        }

        result = pricing_service.get_shrimp_price(user_input)

        assert result is None

    def test_get_price_excel_not_found(self, pricing_service):
        """Test cuando Excel no encuentra el precio"""
        pricing_service.excel_service.get_price_data.return_value = None

        user_input = {
            'size': '99/99',  # Talla inexistente
            'product': 'HLSO',
            'glaseo_factor': 0.80,
        }

        result = pricing_service.get_shrimp_price(user_input)

        assert result is None


class TestCalculateDynamicPrices:
    """Tests para el método privado _calculate_dynamic_prices"""

    @pytest.fixture
    def pricing_service(self):
        with patch('app.services.pricing.ExcelService') as mock_excel, \
             patch('app.services.pricing.get_google_sheets_service') as mock_sheets, \
             patch('app.services.pricing.ExcelLocalCalculatorService') as mock_calc:

            service = PricingService()
            service.excel_service = mock_excel
            service.sheets_service = mock_sheets
            service.calculator_service = mock_calc

            yield service

    def test_dynamic_price_houston_destination(self, pricing_service):
        """Test con destino Houston (costo fijo sin modificar)"""
        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50

        pricing_service.calculator_service.calculate_prices.return_value = {
            'precio_fob_kg': 8.55,
            'precio_glaseo_kg': 5.64,
            'precio_fob_con_glaseo_kg': 7.14,
            'precio_final_kg': 7.49,
            'precio_neto_kg': 7.05,
            'precio_fob_lb': 3.88,
            'precio_glaseo_lb': 2.56,
            'precio_fob_con_glaseo_lb': 3.24,
            'precio_final_lb': 3.40,
            'precio_neto_lb': 3.20,
            'costo_fijo_used': 1.50,
            'glaseo_factor_used': 0.80,
            'flete_used': 0.35,
        }

        user_params = {
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_solicitado': True,
            'flete_custom': 0.35,
            'destination': 'Houston',
            'usar_libras': False,
        }

        result = pricing_service._calculate_dynamic_prices(
            base_price_kg=8.55,
            size='16/20',
            product='HLSO',
            user_params=user_params
        )

        assert result is not None
        assert result['destination'] == 'Houston'

    def test_dynamic_price_with_pounds(self, pricing_service):
        """Test con conversión a libras (costo fijo / 2.2)"""
        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50

        pricing_service.calculator_service.calculate_prices.return_value = {
            'precio_fob_kg': 8.55,
            'precio_glaseo_kg': 5.64,
            'precio_fob_con_glaseo_kg': 7.14,
            'precio_final_kg': 7.49,
            'precio_neto_kg': 7.05,
            'precio_fob_lb': 3.88,
            'precio_glaseo_lb': 2.56,
            'precio_fob_con_glaseo_lb': 3.24,
            'precio_final_lb': 3.40,
            'precio_neto_lb': 3.20,
            'costo_fijo_used': 1.50 / 2.2,
            'glaseo_factor_used': 0.80,
            'flete_used': 0.35,
        }

        user_params = {
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_solicitado': False,
            'usar_libras': True,
        }

        result = pricing_service._calculate_dynamic_prices(
            base_price_kg=8.55,
            size='16/20',
            product='HLSO',
            user_params=user_params
        )

        assert result is not None

    def test_dynamic_price_no_glaseo_returns_none(self, pricing_service):
        """Test que retorna None si no se especifica glaseo"""
        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50

        user_params = {
            'glaseo_factor': None,  # Sin glaseo
            'flete_solicitado': False,
        }

        result = pricing_service._calculate_dynamic_prices(
            base_price_kg=8.55,
            size='16/20',
            product='HLSO',
            user_params=user_params
        )

        assert result is None

    def test_dynamic_price_flete_from_sheets(self, pricing_service):
        """Test obtención de flete desde Google Sheets"""
        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50
        pricing_service.sheets_service.get_flete_value.return_value = 0.40

        pricing_service.calculator_service.calculate_prices.return_value = {
            'precio_fob_kg': 8.55,
            'precio_glaseo_kg': 5.64,
            'precio_fob_con_glaseo_kg': 7.14,
            'precio_final_kg': 7.54,
            'precio_neto_kg': 7.05,
            'precio_fob_lb': 3.88,
            'precio_glaseo_lb': 2.56,
            'precio_fob_con_glaseo_lb': 3.24,
            'precio_final_lb': 3.42,
            'precio_neto_lb': 3.20,
            'costo_fijo_used': 1.50,
            'glaseo_factor_used': 0.80,
            'flete_used': 0.40,
        }

        user_params = {
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_solicitado': True,
            'flete_custom': None,  # Sin flete custom, debe usar de Sheets
        }

        result = pricing_service._calculate_dynamic_prices(
            base_price_kg=8.55,
            size='16/20',
            product='HLSO',
            user_params=user_params
        )

        assert result is not None
        assert result['flete'] == 0.40
        pricing_service.sheets_service.get_flete_value.assert_called_once()

    def test_dynamic_price_no_flete_when_not_requested(self, pricing_service):
        """Test que flete = 0 cuando no se solicita"""
        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50

        pricing_service.calculator_service.calculate_prices.return_value = {
            'precio_fob_kg': 8.55,
            'precio_glaseo_kg': 5.64,
            'precio_fob_con_glaseo_kg': 7.14,
            'precio_final_kg': 7.14,  # Sin flete
            'precio_neto_kg': 7.05,
            'precio_fob_lb': 3.88,
            'precio_glaseo_lb': 2.56,
            'precio_fob_con_glaseo_lb': 3.24,
            'precio_final_lb': 3.24,
            'precio_neto_lb': 3.20,
            'costo_fijo_used': 1.50,
            'glaseo_factor_used': 0.80,
            'flete_used': 0,
        }

        user_params = {
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_solicitado': False,  # NO solicita flete
        }

        result = pricing_service._calculate_dynamic_prices(
            base_price_kg=8.55,
            size='16/20',
            product='HLSO',
            user_params=user_params
        )

        assert result is not None
        assert result['flete'] == 0
        assert result['incluye_flete'] is False

    def test_dynamic_price_incluye_flete_flag(self, pricing_service):
        """Test del flag incluye_flete"""
        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50

        pricing_service.calculator_service.calculate_prices.return_value = {
            'precio_fob_kg': 8.55,
            'precio_glaseo_kg': 5.64,
            'precio_fob_con_glaseo_kg': 7.14,
            'precio_final_kg': 7.49,
            'precio_neto_kg': 7.05,
            'precio_fob_lb': 3.88,
            'precio_glaseo_lb': 2.56,
            'precio_fob_con_glaseo_lb': 3.24,
            'precio_final_lb': 3.40,
            'precio_neto_lb': 3.20,
            'costo_fijo_used': 1.50,
            'glaseo_factor_used': 0.80,
            'flete_used': 0.35,
        }

        user_params = {
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_solicitado': True,
            'flete_custom': 0.35,
        }

        result = pricing_service._calculate_dynamic_prices(
            base_price_kg=8.55,
            size='16/20',
            product='HLSO',
            user_params=user_params
        )

        assert result is not None
        assert result['incluye_flete'] is True


class TestServiceMethods:
    """Tests para métodos de servicio auxiliares"""

    @pytest.fixture
    def pricing_service(self):
        with patch('app.services.pricing.ExcelService') as mock_excel, \
             patch('app.services.pricing.get_google_sheets_service'), \
             patch('app.services.pricing.ExcelLocalCalculatorService'):

            service = PricingService()
            service.excel_service = mock_excel
            yield service

    def test_get_available_sizes(self, pricing_service):
        """Test obtención de tallas disponibles"""
        pricing_service.excel_service.get_available_sizes.return_value = [
            '16/20', '21/25', '26/30', '31/35'
        ]

        sizes = pricing_service.get_available_sizes('HLSO')

        assert len(sizes) == 4
        assert '16/20' in sizes
        pricing_service.excel_service.get_available_sizes.assert_called_once_with('HLSO')

    def test_get_available_products(self, pricing_service):
        """Test obtención de productos disponibles"""
        pricing_service.excel_service.get_available_products.return_value = [
            'HLSO', 'HOSO', 'P&D IQF', 'P&D BLOQUE'
        ]

        products = pricing_service.get_available_products()

        assert len(products) == 4
        assert 'HLSO' in products
        assert 'P&D IQF' in products

    def test_reload_prices(self, pricing_service):
        """Test recarga de precios"""
        pricing_service.excel_service.reload_data.return_value = True

        result = pricing_service.reload_prices()

        assert result is True
        pricing_service.excel_service.reload_data.assert_called_once()


@pytest.mark.integration
class TestPricingIntegrationScenarios:
    """Tests de escenarios de integración completos"""

    @pytest.fixture
    def pricing_service(self):
        with patch('app.services.pricing.ExcelService') as mock_excel, \
             patch('app.services.pricing.get_google_sheets_service') as mock_sheets, \
             patch('app.services.pricing.ExcelLocalCalculatorService') as mock_calc:

            service = PricingService()
            service.excel_service = mock_excel
            service.sheets_service = mock_sheets
            service.calculator_service = mock_calc

            yield service

    def test_complete_pricing_flow_with_freight(self, pricing_service):
        """Test flujo completo: precio base + glaseo + flete = CFR"""
        # Setup mocks
        pricing_service.excel_service.get_price_data.return_value = {
            'precio_kg': 8.55,
            'talla': '16/20',
            'producto': 'HLSO'
        }

        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50

        pricing_service.calculator_service.calculate_prices.return_value = {
            'precio_fob_kg': 8.55,
            'precio_glaseo_kg': 5.64,
            'precio_fob_con_glaseo_kg': 7.14,
            'precio_final_kg': 7.49,  # CFR
            'precio_neto_kg': 7.05,
            'precio_fob_lb': 3.88,
            'precio_glaseo_lb': 2.56,
            'precio_fob_con_glaseo_lb': 3.24,
            'precio_final_lb': 3.40,
            'precio_neto_lb': 3.20,
            'costo_fijo_used': 1.50,
            'glaseo_factor_used': 0.80,
            'flete_used': 0.35,
        }

        # Simular request de usuario completo
        user_input = {
            'size': '16/20',
            'product': 'HLSO',
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_solicitado': True,
            'flete_custom': 0.35,
            'quantity': '15000',
            'cliente_nombre': 'Test Cliente',
            'destination': 'China',
        }

        result = pricing_service.get_shrimp_price(user_input)

        # Verificaciones completas
        assert result is not None
        assert result['precio_fob_kg'] == 8.55
        assert result['precio_final_kg'] == 7.49
        assert result['incluye_flete'] is True
        assert result['factor_glaseo'] == 0.80
        assert result['flete'] == 0.35
        assert result['quantity'] == '15000'
        assert result['cliente_nombre'] == 'Test Cliente'
        assert result['destination'] == 'China'

    def test_complete_pricing_flow_fob_only(self, pricing_service):
        """Test flujo completo: precio base + glaseo = FOB (sin flete)"""
        pricing_service.excel_service.get_price_data.return_value = {
            'precio_kg': 8.55,
            'talla': '16/20',
            'producto': 'HLSO'
        }

        pricing_service.sheets_service.get_costo_fijo_value.return_value = 1.50

        pricing_service.calculator_service.calculate_prices.return_value = {
            'precio_fob_kg': 8.55,
            'precio_glaseo_kg': 5.64,
            'precio_fob_con_glaseo_kg': 7.14,
            'precio_final_kg': 7.14,  # FOB (sin flete)
            'precio_neto_kg': 7.05,
            'precio_fob_lb': 3.88,
            'precio_glaseo_lb': 2.56,
            'precio_fob_con_glaseo_lb': 3.24,
            'precio_final_lb': 3.24,
            'precio_neto_lb': 3.20,
            'costo_fijo_used': 1.50,
            'glaseo_factor_used': 0.80,
            'flete_used': 0,
        }

        user_input = {
            'size': '16/20',
            'product': 'HLSO',
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_solicitado': False,  # Solo FOB
        }

        result = pricing_service.get_shrimp_price(user_input)

        assert result is not None
        assert result['precio_final_kg'] == 7.14
        assert result['incluye_flete'] is False
        assert result['flete'] == 0

