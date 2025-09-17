import unittest
from app.services.pricing import PricingService
from app.services.utils import parse_user_message, format_price_response

class TestPricingService(unittest.TestCase):
    
    def setUp(self):
        self.pricing_service = PricingService()
    
    def test_calculate_final_price(self):
        """Test del cálculo de precio final"""
        # Datos de ejemplo: talla 16/20
        base_price = 8.55
        fixed_cost = 0.25
        glaseo_factor = 0.7
        freight = 0.20
        
        final_price = self.pricing_service.calculate_final_price(
            base_price, fixed_cost, glaseo_factor, freight
        )
        
        # Precio esperado: (8.55 + 0.25) / 0.7 + 0.20 = 12.77
        expected_price = 12.77
        self.assertAlmostEqual(final_price, expected_price, places=2)
    
    def test_parse_user_message(self):
        """Test del parseo de mensajes de usuario"""
        
        # Test 1: Mensaje simple con talla
        message1 = "16/20"
        result1 = parse_user_message(message1)
        self.assertEqual(result1['size'], "16/20")
        
        # Test 2: Mensaje completo
        message2 = "Precio HLSO 16/20 para 15,000 lb destino China"
        result2 = parse_user_message(message2)
        self.assertEqual(result2['size'], "16/20")
        self.assertEqual(result2['quantity'], "15,000")
        self.assertEqual(result2['destination'], "CHINA")
        
        # Test 3: Talla con espacios
        message3 = "21 25"
        result3 = parse_user_message(message3)
        self.assertEqual(result3['size'], "21/25")

if __name__ == '__main__':
    unittest.main()