"""
Tests para utilidades de lenguaje y glaseo
"""
import pytest
from app.utils.language_utils import glaseo_percentage_to_factor, detect_language


class TestGlaseoPercentageToFactor:
    """Tests para la conversión de porcentaje de glaseo a factor"""

    def test_glaseo_10_percent(self):
        """Test: 10% glaseo → factor 0.90"""
        assert glaseo_percentage_to_factor(10) == 0.90

    def test_glaseo_15_percent(self):
        """Test: 15% glaseo → factor 0.85"""
        assert glaseo_percentage_to_factor(15) == 0.85

    def test_glaseo_20_percent(self):
        """Test: 20% glaseo → factor 0.80"""
        assert glaseo_percentage_to_factor(20) == 0.80

    def test_glaseo_25_percent(self):
        """Test: 25% glaseo → factor 0.75"""
        assert glaseo_percentage_to_factor(25) == 0.75

    def test_glaseo_0_percent(self):
        """Test: 0% glaseo → factor 1.00"""
        assert glaseo_percentage_to_factor(0) == 1.00

    def test_glaseo_100_percent(self):
        """Test: 100% glaseo → factor 0.00"""
        assert glaseo_percentage_to_factor(100) == 0.00


class TestDetectLanguage:
    """Tests para la detección de idioma"""

    def test_detect_spanish_from_message(self):
        """Detecta español basado en palabras comunes"""
        message = "Hola, por favor dame el precio de camarón"
        assert detect_language(message) == 'es'

    def test_detect_english_from_message(self):
        """Detecta inglés basado en palabras comunes"""
        message = "Hello, please give me the price quote"
        assert detect_language(message) == 'en'

    def test_detect_spanish_with_proforma(self):
        """Detecta español con palabra 'proforma'"""
        message = "Necesito una proforma para cotización"
        assert detect_language(message) == 'es'

    def test_detect_english_with_price(self):
        """Detecta inglés con palabra 'price'"""
        message = "I need a price for this product"
        assert detect_language(message) == 'en'

    def test_detect_from_ai_analysis_spanish(self):
        """Usa análisis de IA cuando está disponible (español)"""
        message = "some text"
        ai_analysis = {'language': 'es'}
        assert detect_language(message, ai_analysis) == 'es'

    def test_detect_from_ai_analysis_english(self):
        """Usa análisis de IA cuando está disponible (inglés)"""
        message = "some text"
        ai_analysis = {'language': 'en'}
        assert detect_language(message, ai_analysis) == 'en'

    def test_detect_from_ai_analysis_invalid_language(self):
        """Ignora análisis de IA con idioma inválido"""
        message = "hola gracias"
        ai_analysis = {'language': 'fr'}  # francés no soportado
        # Debe usar heurística y detectar español
        assert detect_language(message, ai_analysis) == 'es'

    def test_detect_with_empty_message(self):
        """Maneja mensaje vacío (por defecto español)"""
        message = ""
        # Por defecto debería retornar español (es_score == en_score == 0)
        assert detect_language(message) == 'es'

    def test_detect_with_mixed_language(self):
        """Detecta el idioma predominante en mensajes mixtos"""
        # Más palabras en español
        message_es = "Hello, necesito precio y cotización por favor gracias"
        assert detect_language(message_es) == 'es'

        # Más palabras en inglés
        message_en = "Hola, I need price and quote please thank you"
        assert detect_language(message_en) == 'en'

    def test_detect_case_insensitive(self):
        """Detecta idioma sin importar mayúsculas/minúsculas"""
        message_upper = "HOLA GRACIAS PRECIO"
        message_lower = "hola gracias precio"
        message_mixed = "HoLa GrAcIaS pReCiO"

        assert detect_language(message_upper) == 'es'
        assert detect_language(message_lower) == 'es'
        assert detect_language(message_mixed) == 'es'
