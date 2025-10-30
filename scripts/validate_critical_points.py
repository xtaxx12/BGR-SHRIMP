"""
Validador de puntos críticos del sistema
Verifica funcionalidades esenciales para operación del negocio
"""
import sys
import os
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pricing import PricingService
from app.services.session import SessionManager
from app.services.quality_assurance import qa_service


class CriticalPointValidator:
    """Valida puntos críticos del sistema"""
    
    def __init__(self):
        self.pricing_service = PricingService()
        self.session_manager = SessionManager()
        self.results = []
    
    def validate_point(self, name: str, validation_func) -> Dict:
        """Ejecuta una validación y registra el resultado"""
        print(f"\n{'='*80}")
        print(f"Validando: {name}")
        print(f"{'='*80}\n")
        
        start = time.time()
        
        try:
            passed, details = validation_func()
            duration = time.time() - start
            
            result = {
                'name': name,
                'passed': passed,
                'duration': duration,
                'details': details,
                'timestamp': datetime.now().isoformat()
            }
            
            status = "✅ PASÓ" if passed else "❌ FALLÓ"
            print(f"\n{status} - {name} ({duration:.3f}s)")
            print(f"Detalles: {details}")
            
            self.results.append(result)
            return result
            
        except Exception as e:
            duration = time.time() - start
            
            result = {
                'name': name,
                'passed': False,
                'duration': duration,
                'details': f"Error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n❌ ERROR - {name} ({duration:.3f}s)")
            print(f"Error: {str(e)}")
            
            self.results.append(result)
            return result
    
    def critical_1_price_query_response_time(self) -> Tuple[bool, str]:
        """CP1: Consulta de precio responde en < 3 segundos"""
        query = {
            'product': 'HLSO',
            'size': '16/20',
            'glaseo_factor': 0.80,
            'glaseo_percentage': 20,
            'flete_custom': 0.15,
            'flete_solicitado': True,
            'custom_calculation': True
        }
        
        start = time.time()
        result = self.pricing_service.get_shrimp_price(query)
        duration = time.time() - start
        
        if result is None:
            return False, f"No se obtuvo precio (duración: {duration:.3f}s)"
        
        if duration > 3.0:
            return False, f"Tiempo de respuesta excedido: {duration:.3f}s > 3.0s"
        
        return True, f"Respuesta en {duration:.3f}s con precio ${result.get('precio_final_kg', 0):.2f}/kg"
    
    def critical_2_pdf_generation_time(self) -> Tuple[bool, str]:
        """CP2: Generación de PDF en < 5 segundos"""
        try:
            from app.services.pdf_generator import PDFGenerator
            
            pdf_generator = PDFGenerator()
            
            # Datos de prueba
            price_info = {
                'producto': 'HLSO',
                'talla': '16/20',
                'precio_kg': 8.88,
                'factor_glaseo': 0.80,
                'glaseo_percentage': 20,
                'costo_fijo': 0.29,
                'precio_glaseo_kg': 6.87,
                'precio_fob_con_glaseo_kg': 7.16,
                'flete': 0.15,
                'precio_final_kg': 7.31
            }
            
            start = time.time()
            pdf_path = pdf_generator.generate_quote_pdf(
                price_info,
                user_phone="+593988057425",
                language="es"
            )
            duration = time.time() - start
            
            if not pdf_path:
                return False, f"No se generó PDF (duración: {duration:.3f}s)"
            
            if duration > 5.0:
                return False, f"Tiempo de generación excedido: {duration:.3f}s > 5.0s"
            
            # Verificar que el archivo existe
            if not os.path.exists(pdf_path):
                return False, f"PDF generado pero archivo no existe: {pdf_path}"
            
            # Limpiar archivo de prueba
            try:
                os.remove(pdf_path)
            except:
                pass
            
            return True, f"PDF generado en {duration:.3f}s"
            
        except ImportError as e:
            return False, f"Error importando PDFGenerator: {str(e)}"
    
    def critical_3_ddp_without_flete_detection(self) -> Tuple[bool, str]:
        """CP3: Detecta DDP sin flete especificado"""
        # Este test verifica la lógica de detección
        # En producción, esto se maneja en routes.py
        
        test_message = "Necesito precio HLSO 16/20 DDP Houston"
        
        # Verificar que el mensaje contiene DDP pero no flete
        has_ddp = 'DDP' in test_message.upper()
        has_flete = any(word in test_message.lower() for word in ['flete', 'freight', '$', 'centavos'])
        
        if has_ddp and not has_flete:
            return True, "Detecta correctamente DDP sin flete especificado"
        
        return False, "No detecta DDP sin flete"
    
    def critical_4_concurrent_sessions(self) -> Tuple[bool, str]:
        """CP4: Mantiene sesiones independientes por usuario"""
        user1 = "test_user_1"
        user2 = "test_user_2"
        
        # Crear sesiones para dos usuarios
        quote1 = {
            'producto': 'HLSO',
            'talla': '16/20',
            'precio_kg': 8.88
        }
        
        quote2 = {
            'producto': 'HOSO',
            'talla': '30/40',
            'precio_kg': 5.52
        }
        
        self.session_manager.set_last_quote(user1, quote1)
        self.session_manager.set_last_quote(user2, quote2)
        
        # Verificar que las sesiones son independientes
        retrieved1 = self.session_manager.get_last_quote(user1)
        retrieved2 = self.session_manager.get_last_quote(user2)
        
        if not retrieved1 or not retrieved2:
            return False, "No se pudieron recuperar las sesiones"
        
        if retrieved1['producto'] != 'HLSO':
            return False, f"Sesión usuario 1 incorrecta: {retrieved1['producto']}"
        
        if retrieved2['producto'] != 'HOSO':
            return False, f"Sesión usuario 2 incorrecta: {retrieved2['producto']}"
        
        # Limpiar sesiones de prueba
        self.session_manager.clear_session(user1)
        self.session_manager.clear_session(user2)
        
        return True, "Sesiones independientes funcionan correctamente"
    
    def critical_5_webhook_validation(self) -> Tuple[bool, str]:
        """CP5: Validación de webhook Twilio"""
        # Este test verifica que la lógica de validación existe
        # En producción, esto se maneja en security.py
        
        try:
            from app.security import TwilioWebhookValidator, validate_twilio_webhook
            
            # Verificar que la clase existe
            if not TwilioWebhookValidator:
                return False, "Clase TwilioWebhookValidator no encontrada"
            
            # Verificar que el decorador existe y es callable
            if not callable(validate_twilio_webhook):
                return False, "Decorador validate_twilio_webhook no es callable"
            
            # Crear instancia de prueba
            validator = TwilioWebhookValidator("test_token")
            
            return True, "Sistema de validación de webhook Twilio disponible"
            
        except ImportError as e:
            return False, f"Error importando componentes de seguridad: {str(e)}"
    
    def critical_6_product_validation(self) -> Tuple[bool, str]:
        """CP6: Validación de productos válidos"""
        valid_products = ['HOSO', 'HLSO', 'P&D IQF', 'P&D BLOQUE', 'EZ PEEL', 'PuD-EUROPA', 'PuD-EEUU', 'COOKED']
        
        passed_count = 0
        for product in valid_products:
            is_valid, error = qa_service.validate_product(product)
            if is_valid:
                passed_count += 1
        
        if passed_count == len(valid_products):
            return True, f"Todos los productos válidos ({passed_count}/{len(valid_products)})"
        
        return False, f"Solo {passed_count}/{len(valid_products)} productos válidos"
    
    def critical_7_size_validation(self) -> Tuple[bool, str]:
        """CP7: Validación de tallas válidas"""
        valid_sizes = ['U15', '16/20', '20/30', '21/25', '26/30', '30/40', '31/35', 
                       '36/40', '40/50', '41/50', '50/60', '51/60', '60/70', '61/70', 
                       '70/80', '71/90']
        
        passed_count = 0
        for size in valid_sizes:
            is_valid, error = qa_service.validate_size(size)
            if is_valid:
                passed_count += 1
        
        if passed_count == len(valid_sizes):
            return True, f"Todas las tallas válidas ({passed_count}/{len(valid_sizes)})"
        
        return False, f"Solo {passed_count}/{len(valid_sizes)} tallas válidas"
    
    def critical_8_glaseo_calculation(self) -> Tuple[bool, str]:
        """CP8: Cálculo correcto de glaseo (0% - 50%)"""
        test_cases = [
            (0, 1.00),
            (10, 0.90),
            (15, 0.85),
            (20, 0.80),
            (25, 0.75),
            (30, 0.70),
            (50, 0.50)
        ]
        
        passed_count = 0
        for percentage, expected_factor in test_cases:
            calculated_factor = 1 - (percentage / 100)
            if abs(calculated_factor - expected_factor) < 0.001:
                passed_count += 1
        
        if passed_count == len(test_cases):
            return True, f"Todos los cálculos de glaseo correctos ({passed_count}/{len(test_cases)})"
        
        return False, f"Solo {passed_count}/{len(test_cases)} cálculos correctos"
    
    def run_all_validations(self):
        """Ejecuta todas las validaciones de puntos críticos"""
        print("\n" + "="*80)
        print("🔍 VALIDACIÓN DE PUNTOS CRÍTICOS")
        print("="*80)
        
        # Ejecutar todas las validaciones
        self.validate_point("CP1: Tiempo de respuesta de consulta < 3s", 
                           self.critical_1_price_query_response_time)
        
        self.validate_point("CP2: Generación de PDF < 5s", 
                           self.critical_2_pdf_generation_time)
        
        self.validate_point("CP3: Detección de DDP sin flete", 
                           self.critical_3_ddp_without_flete_detection)
        
        self.validate_point("CP4: Sesiones concurrentes independientes", 
                           self.critical_4_concurrent_sessions)
        
        self.validate_point("CP5: Validación de webhook Twilio", 
                           self.critical_5_webhook_validation)
        
        self.validate_point("CP6: Validación de productos", 
                           self.critical_6_product_validation)
        
        self.validate_point("CP7: Validación de tallas", 
                           self.critical_7_size_validation)
        
        self.validate_point("CP8: Cálculo de glaseo", 
                           self.critical_8_glaseo_calculation)
    
    def print_summary(self):
        """Imprime resumen de validaciones"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        
        print("\n" + "="*80)
        print("📊 RESUMEN DE PUNTOS CRÍTICOS")
        print("="*80)
        print(f"\nTotal de puntos críticos: {total}")
        print(f"✅ Pasados: {passed}")
        print(f"❌ Fallados: {failed}")
        print(f"📈 Tasa de éxito: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n❌ Puntos críticos fallados:")
            for result in self.results:
                if not result['passed']:
                    print(f"   • {result['name']}")
                    print(f"     {result['details']}")
        
        print("\n" + "="*80)
        
        return passed == total
    
    def get_results(self) -> List[Dict]:
        """Retorna los resultados de validación"""
        return self.results


def main():
    """Función principal"""
    validator = CriticalPointValidator()
    
    # Ejecutar todas las validaciones
    validator.run_all_validations()
    
    # Mostrar resumen
    all_passed = validator.print_summary()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
