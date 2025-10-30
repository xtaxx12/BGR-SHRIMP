"""
Script maestro de validación y certificación
Ejecuta todos los tests y genera reporte consolidado
"""
import sys
import os
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Tuple

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ValidationRunner:
    """Ejecuta todos los tests y genera reportes consolidados"""
    
    def __init__(self):
        self.test_files = [
            'test_quality_assurance.py',
            'test_flexible_glaseo.py',
            'test_consolidated_quote.py',
            'test_hoso_3040_calculation.py',
            'test_session_preservation.py',
            'test_routes_flete.py',
            'test_routes_glaseo.py',
            'test_natural_conversation.py'
        ]
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def run_test(self, test_file: str) -> Dict:
        """Ejecuta un test individual y captura el resultado"""
        print(f"\n{'='*80}")
        print(f"Ejecutando: {test_file}")
        print(f"{'='*80}\n")
        
        start = datetime.now()
        
        try:
            # Configurar environment para UTF-8
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Ejecutar el test con encoding UTF-8
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=60,
                encoding='utf-8',
                errors='replace',
                env=env
            )
            
            end = datetime.now()
            duration = (end - start).total_seconds()
            
            # Determinar si pasó o falló basado SOLO en el return code
            # Los warnings en stderr no deben considerarse errores
            passed = result.returncode == 0
            
            # Mostrar output del test
            if result.stdout:
                print(result.stdout)
            
            return {
                'test_file': test_file,
                'passed': passed,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            end = datetime.now()
            duration = (end - start).total_seconds()
            
            return {
                'test_file': test_file,
                'passed': False,
                'duration': duration,
                'stdout': '',
                'stderr': 'Test timeout after 60 seconds',
                'return_code': -1
            }
        
        except Exception as e:
            end = datetime.now()
            duration = (end - start).total_seconds()
            
            return {
                'test_file': test_file,
                'passed': False,
                'duration': duration,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1
            }
    
    def run_all_tests(self) -> List[Dict]:
        """Ejecuta todos los tests"""
        print("\n" + "="*80)
        print("🧪 INICIANDO SUITE COMPLETA DE TESTS")
        print("="*80)
        
        self.start_time = datetime.now()
        
        for test_file in self.test_files:
            result = self.run_test(test_file)
            self.results.append(result)
            
            # Mostrar resultado inmediato
            status = "✅ PASÓ" if result['passed'] else "❌ FALLÓ"
            print(f"\n{status} - {test_file} ({result['duration']:.2f}s)")
        
        self.end_time = datetime.now()
        
        return self.results
    
    def generate_summary(self) -> Dict:
        """Genera resumen de resultados"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'success_rate': (passed / total * 100) if total > 0 else 0,
            'total_duration': total_duration,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }
    
    def print_summary(self):
        """Imprime resumen en consola"""
        summary = self.generate_summary()
        
        print("\n" + "="*80)
        print("📊 RESUMEN DE VALIDACIÓN")
        print("="*80)
        print(f"\nTotal de tests: {summary['total_tests']}")
        print(f"✅ Pasados: {summary['passed']}")
        print(f"❌ Fallados: {summary['failed']}")
        print(f"📈 Tasa de éxito: {summary['success_rate']:.1f}%")
        print(f"⏱️  Duración total: {summary['total_duration']:.2f}s")
        
        if summary['failed'] > 0:
            print("\n❌ Tests fallados:")
            for result in self.results:
                if not result['passed']:
                    print(f"   • {result['test_file']}")
                    if result['stderr']:
                        print(f"     Error: {result['stderr'][:200]}")
        
        print("\n" + "="*80)
    
    def save_report(self, filename: str = 'validation_report.json'):
        """Guarda reporte en formato JSON"""
        report = {
            'summary': self.generate_summary(),
            'results': self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte guardado en: {filename}")


def main():
    """Función principal"""
    runner = ValidationRunner()
    
    # Ejecutar todos los tests
    runner.run_all_tests()
    
    # Mostrar resumen
    runner.print_summary()
    
    # Guardar reporte
    runner.save_report()
    
    # Retornar código de salida
    summary = runner.generate_summary()
    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
