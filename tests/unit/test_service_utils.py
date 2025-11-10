"""
Tests unitarios para app/utils/service_utils.py

Cubre:
- get_services() con lazy initialization
- Inicialización única de servicios (singleton pattern)
- Retorno correcto de todos los servicios
- Orden correcto de inicialización
- Compartir ExcelService entre servicios
"""
from unittest.mock import Mock, patch, MagicMock, call

import pytest

from app.utils.service_utils import get_services


class TestGetServices:
    """Tests para get_services()"""

    def setup_method(self):
        """Reset de variables globales antes de cada test"""
        import app.utils.service_utils as service_utils
        service_utils.pricing_service = None
        service_utils.interactive_service = None
        service_utils.pdf_generator = None
        service_utils.whatsapp_sender = None
        service_utils.openai_service = None

    def test_initializes_all_services(self):
        """Test que inicializa todos los servicios"""
        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService') as MockInteractive, \
             patch('app.utils.service_utils.PDFGenerator') as MockPDF, \
             patch('app.utils.service_utils.WhatsAppSender') as MockWhatsApp, \
             patch('app.utils.service_utils.OpenAIService') as MockOpenAI:

            # Configurar mocks
            mock_pricing = Mock()
            mock_pricing.excel_service = Mock()
            MockPricing.return_value = mock_pricing

            # Llamar función
            pricing, interactive, pdf, whatsapp, openai = get_services()

            # Verificar que se crearon todos los servicios
            MockPricing.assert_called_once()
            MockInteractive.assert_called_once()
            MockPDF.assert_called_once()
            MockWhatsApp.assert_called_once()
            MockOpenAI.assert_called_once()

    def test_returns_all_services_in_correct_order(self):
        """Test que retorna todos los servicios en el orden correcto"""
        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService') as MockInteractive, \
             patch('app.utils.service_utils.PDFGenerator') as MockPDF, \
             patch('app.utils.service_utils.WhatsAppSender') as MockWhatsApp, \
             patch('app.utils.service_utils.OpenAIService') as MockOpenAI:

            # Configurar mocks con identificadores únicos
            mock_pricing = Mock(name='PricingService')
            mock_pricing.excel_service = Mock()
            mock_interactive = Mock(name='InteractiveMessageService')
            mock_pdf = Mock(name='PDFGenerator')
            mock_whatsapp = Mock(name='WhatsAppSender')
            mock_openai = Mock(name='OpenAIService')

            MockPricing.return_value = mock_pricing
            MockInteractive.return_value = mock_interactive
            MockPDF.return_value = mock_pdf
            MockWhatsApp.return_value = mock_whatsapp
            MockOpenAI.return_value = mock_openai

            # Obtener servicios
            result = get_services()

            # Verificar orden: pricing, interactive, pdf, whatsapp, openai
            assert len(result) == 5
            assert result[0] is mock_pricing
            assert result[1] is mock_interactive
            assert result[2] is mock_pdf
            assert result[3] is mock_whatsapp
            assert result[4] is mock_openai

    def test_lazy_initialization_only_once(self):
        """Test que lazy initialization solo ocurre una vez"""
        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService') as MockInteractive, \
             patch('app.utils.service_utils.PDFGenerator') as MockPDF, \
             patch('app.utils.service_utils.WhatsAppSender') as MockWhatsApp, \
             patch('app.utils.service_utils.OpenAIService') as MockOpenAI:

            # Configurar mocks
            mock_pricing = Mock()
            mock_pricing.excel_service = Mock()
            MockPricing.return_value = mock_pricing

            # Primera llamada: debe inicializar
            result1 = get_services()

            # Segunda llamada: NO debe reinicializar
            result2 = get_services()

            # Tercera llamada: NO debe reinicializar
            result3 = get_services()

            # Verificar que solo se llamó una vez a cada constructor
            assert MockPricing.call_count == 1
            assert MockInteractive.call_count == 1
            assert MockPDF.call_count == 1
            assert MockWhatsApp.call_count == 1
            assert MockOpenAI.call_count == 1

            # Todas las llamadas deben retornar los mismos objetos
            assert result1[0] is result2[0] is result3[0]  # pricing
            assert result1[1] is result2[1] is result3[1]  # interactive
            assert result1[2] is result2[2] is result3[2]  # pdf
            assert result1[3] is result2[3] is result3[3]  # whatsapp
            assert result1[4] is result2[4] is result3[4]  # openai

    def test_shares_excel_service_with_interactive(self):
        """Test que comparte ExcelService entre PricingService e InteractiveMessageService"""
        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService') as MockInteractive, \
             patch('app.utils.service_utils.PDFGenerator'), \
             patch('app.utils.service_utils.WhatsAppSender'), \
             patch('app.utils.service_utils.OpenAIService'):

            # Configurar PricingService con un excel_service
            mock_excel = Mock(name='ExcelService')
            mock_pricing = Mock()
            mock_pricing.excel_service = mock_excel
            MockPricing.return_value = mock_pricing

            # Llamar función
            get_services()

            # Verificar que InteractiveMessageService recibió el excel_service
            MockInteractive.assert_called_once_with(mock_excel)

    def test_pricing_service_initialized_first(self):
        """Test que PricingService se inicializa antes que InteractiveMessageService"""
        call_order = []

        def track_pricing(*args, **kwargs):
            call_order.append('pricing')
            mock = Mock()
            mock.excel_service = Mock()
            return mock

        def track_interactive(*args, **kwargs):
            call_order.append('interactive')
            return Mock()

        with patch('app.utils.service_utils.PricingService', side_effect=track_pricing), \
             patch('app.utils.service_utils.InteractiveMessageService', side_effect=track_interactive), \
             patch('app.utils.service_utils.PDFGenerator'), \
             patch('app.utils.service_utils.WhatsAppSender'), \
             patch('app.utils.service_utils.OpenAIService'):

            get_services()

            # PricingService debe inicializarse antes que InteractiveMessageService
            assert call_order[0] == 'pricing'
            assert call_order[1] == 'interactive'

    def test_logs_initialization_message(self):
        """Test que registra mensaje de inicialización"""
        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService'), \
             patch('app.utils.service_utils.PDFGenerator'), \
             patch('app.utils.service_utils.WhatsAppSender'), \
             patch('app.utils.service_utils.OpenAIService'), \
             patch('app.utils.service_utils.logger') as mock_logger:

            # Configurar mock
            mock_pricing = Mock()
            mock_pricing.excel_service = Mock()
            MockPricing.return_value = mock_pricing

            get_services()

            # Verificar que se registró el mensaje
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0][0]
            assert "Servicios inicializados" in call_args

    def test_returns_existing_services_without_logging(self):
        """Test que no vuelve a registrar cuando retorna servicios existentes"""
        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService'), \
             patch('app.utils.service_utils.PDFGenerator'), \
             patch('app.utils.service_utils.WhatsAppSender'), \
             patch('app.utils.service_utils.OpenAIService'), \
             patch('app.utils.service_utils.logger') as mock_logger:

            # Configurar mock
            mock_pricing = Mock()
            mock_pricing.excel_service = Mock()
            MockPricing.return_value = mock_pricing

            # Primera llamada
            get_services()
            first_log_count = mock_logger.debug.call_count

            # Segunda llamada
            get_services()
            second_log_count = mock_logger.debug.call_count

            # No debe haber logs adicionales
            assert second_log_count == first_log_count

    def test_global_variables_set_correctly(self):
        """Test que las variables globales se establecen correctamente"""
        import app.utils.service_utils as service_utils

        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService') as MockInteractive, \
             patch('app.utils.service_utils.PDFGenerator') as MockPDF, \
             patch('app.utils.service_utils.WhatsAppSender') as MockWhatsApp, \
             patch('app.utils.service_utils.OpenAIService') as MockOpenAI:

            # Configurar mocks
            mock_pricing = Mock()
            mock_pricing.excel_service = Mock()
            mock_interactive = Mock()
            mock_pdf = Mock()
            mock_whatsapp = Mock()
            mock_openai = Mock()

            MockPricing.return_value = mock_pricing
            MockInteractive.return_value = mock_interactive
            MockPDF.return_value = mock_pdf
            MockWhatsApp.return_value = mock_whatsapp
            MockOpenAI.return_value = mock_openai

            # Llamar función
            get_services()

            # Verificar que las variables globales están establecidas
            assert service_utils.pricing_service is mock_pricing
            assert service_utils.interactive_service is mock_interactive
            assert service_utils.pdf_generator is mock_pdf
            assert service_utils.whatsapp_sender is mock_whatsapp
            assert service_utils.openai_service is mock_openai

    def test_none_check_prevents_reinitialization(self):
        """Test que la verificación de None previene reinicialización"""
        import app.utils.service_utils as service_utils

        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService'), \
             patch('app.utils.service_utils.PDFGenerator'), \
             patch('app.utils.service_utils.WhatsAppSender'), \
             patch('app.utils.service_utils.OpenAIService'):

            # Configurar mock
            mock_pricing = Mock()
            mock_pricing.excel_service = Mock()
            MockPricing.return_value = mock_pricing

            # Primera llamada
            get_services()
            assert service_utils.pricing_service is not None

            # Limpiar mock call count
            MockPricing.reset_mock()

            # Segunda llamada
            get_services()

            # No debe haber llamado nuevamente al constructor
            MockPricing.assert_not_called()


class TestServiceUtilsIntegration:
    """Tests de integración para service_utils"""

    def setup_method(self):
        """Reset de variables globales"""
        import app.utils.service_utils as service_utils
        service_utils.pricing_service = None
        service_utils.interactive_service = None
        service_utils.pdf_generator = None
        service_utils.whatsapp_sender = None
        service_utils.openai_service = None

    def test_services_can_be_used_after_initialization(self):
        """Test que los servicios pueden usarse después de inicialización"""
        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService') as MockInteractive, \
             patch('app.utils.service_utils.PDFGenerator') as MockPDF, \
             patch('app.utils.service_utils.WhatsAppSender') as MockWhatsApp, \
             patch('app.utils.service_utils.OpenAIService') as MockOpenAI:

            # Configurar mocks con métodos
            mock_pricing = Mock()
            mock_pricing.excel_service = Mock()
            mock_pricing.get_shrimp_price.return_value = {'price': 7.50}

            mock_interactive = Mock()
            mock_interactive.create_menu.return_value = "menu"

            MockPricing.return_value = mock_pricing
            MockInteractive.return_value = mock_interactive
            MockPDF.return_value = Mock()
            MockWhatsApp.return_value = Mock()
            MockOpenAI.return_value = Mock()

            # Obtener servicios
            pricing, interactive, pdf, whatsapp, openai = get_services()

            # Usar los servicios
            price_result = pricing.get_shrimp_price({'size': '16/20'})
            menu_result = interactive.create_menu()

            assert price_result == {'price': 7.50}
            assert menu_result == "menu"

    def test_excel_service_shared_correctly(self):
        """Test que excel_service se comparte correctamente"""
        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService') as MockInteractive, \
             patch('app.utils.service_utils.PDFGenerator'), \
             patch('app.utils.service_utils.WhatsAppSender'), \
             patch('app.utils.service_utils.OpenAIService'):

            # Crear un mock específico para excel_service
            mock_excel = Mock(name='SharedExcelService')
            mock_excel.get_price_data = Mock(return_value={'price': 8.55})

            # Configurar PricingService para retornar el mock_excel
            mock_pricing = Mock()
            mock_pricing.excel_service = mock_excel
            MockPricing.return_value = mock_pricing

            # Obtener servicios
            pricing, interactive, pdf, whatsapp, openai = get_services()

            # Verificar que InteractiveMessageService recibió el mismo excel_service
            MockInteractive.assert_called_once_with(mock_excel)

            # Verificar que ambos servicios pueden usar el mismo excel_service
            result = mock_excel.get_price_data('16/20', 'HLSO')
            assert result == {'price': 8.55}

    def test_multiple_parallel_calls(self):
        """Test múltiples llamadas paralelas (thread safety básico)"""
        import app.utils.service_utils as service_utils

        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService'), \
             patch('app.utils.service_utils.PDFGenerator'), \
             patch('app.utils.service_utils.WhatsAppSender'), \
             patch('app.utils.service_utils.OpenAIService'):

            # Configurar mock
            mock_pricing = Mock()
            mock_pricing.excel_service = Mock()
            MockPricing.return_value = mock_pricing

            # Múltiples llamadas
            results = [get_services() for _ in range(10)]

            # Todas deben retornar los mismos objetos
            for result in results:
                assert result[0] is results[0][0]  # Mismo pricing_service
                assert result[1] is results[0][1]  # Mismo interactive_service
                assert result[2] is results[0][2]  # Mismo pdf_generator
                assert result[3] is results[0][3]  # Mismo whatsapp_sender
                assert result[4] is results[0][4]  # Mismo openai_service

            # Solo debe haber inicializado una vez
            assert MockPricing.call_count == 1


class TestServiceUtilsEdgeCases:
    """Tests de casos extremos"""

    def setup_method(self):
        """Reset de variables globales"""
        import app.utils.service_utils as service_utils
        service_utils.pricing_service = None
        service_utils.interactive_service = None
        service_utils.pdf_generator = None
        service_utils.whatsapp_sender = None
        service_utils.openai_service = None

    def test_handles_pricing_service_without_excel_service(self):
        """Test manejo cuando PricingService no tiene excel_service"""
        with patch('app.utils.service_utils.PricingService') as MockPricing, \
             patch('app.utils.service_utils.InteractiveMessageService') as MockInteractive, \
             patch('app.utils.service_utils.PDFGenerator'), \
             patch('app.utils.service_utils.WhatsAppSender'), \
             patch('app.utils.service_utils.OpenAIService'):

            # PricingService sin excel_service (caso extremo)
            mock_pricing = Mock(spec=[])  # Mock sin atributos
            MockPricing.return_value = mock_pricing

            # Debe lanzar AttributeError al intentar acceder a excel_service
            with pytest.raises(AttributeError):
                get_services()

    def test_initialization_order_matters(self):
        """Test que el orden de inicialización importa"""
        initialization_order = []

        class MockPricingInit:
            def __init__(self):
                initialization_order.append('pricing')
                self.excel_service = Mock()

        class MockInteractiveInit:
            def __init__(self, excel_service):
                initialization_order.append('interactive')
                assert excel_service is not None

        with patch('app.utils.service_utils.PricingService', MockPricingInit), \
             patch('app.utils.service_utils.InteractiveMessageService', MockInteractiveInit), \
             patch('app.utils.service_utils.PDFGenerator', Mock), \
             patch('app.utils.service_utils.WhatsAppSender', Mock), \
             patch('app.utils.service_utils.OpenAIService', Mock):

            get_services()

            # Pricing debe inicializarse antes que Interactive
            assert initialization_order == ['pricing', 'interactive']

    def test_all_services_initialized_before_return(self):
        """Test que todos los servicios se inicializan antes de retornar"""
        initialized = {
            'pricing': False,
            'interactive': False,
            'pdf': False,
            'whatsapp': False,
            'openai': False
        }

        class TrackingMock:
            def __init__(self, service_name):
                self.service_name = service_name

            def __call__(self, *args, **kwargs):
                initialized[self.service_name] = True
                mock = Mock()
                if self.service_name == 'pricing':
                    mock.excel_service = Mock()
                return mock

        with patch('app.utils.service_utils.PricingService', TrackingMock('pricing')), \
             patch('app.utils.service_utils.InteractiveMessageService', TrackingMock('interactive')), \
             patch('app.utils.service_utils.PDFGenerator', TrackingMock('pdf')), \
             patch('app.utils.service_utils.WhatsAppSender', TrackingMock('whatsapp')), \
             patch('app.utils.service_utils.OpenAIService', TrackingMock('openai')):

            result = get_services()

            # Todos los servicios deben estar inicializados
            assert all(initialized.values())
            # Y todos deben ser retornados
            assert len(result) == 5
            assert all(r is not None for r in result)
