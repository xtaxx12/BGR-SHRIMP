"""
Script maestro de validación y certificación
Orquesta la ejecución completa del sistema de validación
"""
import sys
import os
import json
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.run_validation import ValidationRunner
from scripts.validate_critical_points import CriticalPointValidator
from scripts.generate_quality_certificate import QualityCertificateGenerator


def print_header(title: str):
    """Imprime un encabezado formateado"""
    print("\n" + "="*80)
    print(title.center(80))
    print("="*80 + "\n")


def main():
    """Función principal que ejecuta todo el proceso de validación"""
    
    print_header("🚀 SISTEMA DE VALIDACIÓN Y CERTIFICACIÓN BGR SHRIMP BOT")
    
    start_time = datetime.now()
    
    # FASE 1: Ejecutar suite completa de tests
    print_header("FASE 1: EJECUCIÓN DE SUITE DE TESTS")
    
    validation_runner = ValidationRunner()
    validation_runner.run_all_tests()
    validation_runner.print_summary()
    validation_runner.save_report('validation_report.json')
    
    validation_summary = validation_runner.generate_summary()
    
    # FASE 2: Validar puntos críticos
    print_header("FASE 2: VALIDACIÓN DE PUNTOS CRÍTICOS")
    
    critical_validator = CriticalPointValidator()
    critical_validator.run_all_validations()
    critical_passed = critical_validator.print_summary()
    
    # Guardar resultados de puntos críticos
    critical_results = {
        'timestamp': datetime.now().isoformat(),
        'results': critical_validator.get_results()
    }
    
    with open('critical_points_report.json', 'w', encoding='utf-8') as f:
        json.dump(critical_results, f, indent=2, ensure_ascii=False)
    
    print("\n💾 Reporte de puntos críticos guardado en: critical_points_report.json")
    
    # FASE 3: Generar certificado de calidad
    print_header("FASE 3: GENERACIÓN DE CERTIFICADO DE CALIDAD")
    
    certificate_generator = QualityCertificateGenerator()
    
    # Cargar reportes
    validation_report = certificate_generator.load_validation_report('validation_report.json')
    critical_points = critical_results['results']
    
    # Generar certificados
    try:
        from reportlab.lib.pagesizes import letter
        pdf_path = certificate_generator.generate_certificate(
            validation_report=validation_report,
            critical_points=critical_points,
            output_filename='quality_certificate.pdf'
        )
        
        if pdf_path and os.path.exists(pdf_path):
            size = os.path.getsize(pdf_path)
            print(f"✅ Certificado PDF generado: {pdf_path}")
            print(f"   📊 Tamaño: {size:,} bytes")
    except ImportError:
        print("⚠️  ReportLab no disponible, generando solo certificado en texto plano...")
    
    # Generar certificado en texto plano (siempre)
    txt_path = certificate_generator.generate_text_certificate(
        validation_report=validation_report,
        critical_points=critical_points,
        output_filename='quality_certificate.txt'
    )
    
    if txt_path and os.path.exists(txt_path):
        size = os.path.getsize(txt_path)
        print(f"✅ Certificado TXT generado: {txt_path}")
        print(f"   📊 Tamaño: {size:,} bytes")
    
    # RESUMEN FINAL
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    print_header("📊 RESUMEN FINAL DE VALIDACIÓN Y CERTIFICACIÓN")
    
    print(f"⏱️  Duración total del proceso: {total_duration:.2f}s")
    print(f"📅 Inicio: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("📋 RESULTADOS DE TESTS:")
    print(f"   Total: {validation_summary['total_tests']}")
    print(f"   ✅ Pasados: {validation_summary['passed']}")
    print(f"   ❌ Fallados: {validation_summary['failed']}")
    print(f"   📈 Tasa de éxito: {validation_summary['success_rate']:.1f}%")
    print()
    
    print("🔍 RESULTADOS DE PUNTOS CRÍTICOS:")
    total_critical = len(critical_results['results'])
    passed_critical = sum(1 for r in critical_results['results'] if r['passed'])
    print(f"   Total: {total_critical}")
    print(f"   ✅ Pasados: {passed_critical}")
    print(f"   ❌ Fallados: {total_critical - passed_critical}")
    print(f"   📈 Tasa de éxito: {(passed_critical/total_critical*100):.1f}%")
    print()
    
    print("📄 ARCHIVOS GENERADOS:")
    print("   • validation_report.json")
    print("   • critical_points_report.json")
    print("   • quality_certificate.txt")
    if os.path.exists('quality_certificate.pdf'):
        print("   • quality_certificate.pdf")
    print()
    
    # Determinar estado final
    all_tests_passed = validation_summary['failed'] == 0
    all_critical_passed = critical_passed
    
    if all_tests_passed and all_critical_passed:
        print("✅ CERTIFICACIÓN EXITOSA")
        print("   El sistema está listo para despliegue en producción.")
        print()
        return 0
    elif validation_summary['success_rate'] >= 90 and passed_critical >= total_critical * 0.9:
        print("⚠️  CERTIFICACIÓN CONDICIONAL")
        print("   El sistema requiere correcciones menores antes del despliegue.")
        print()
        return 1
    else:
        print("❌ CERTIFICACIÓN FALLIDA")
        print("   El sistema requiere correcciones significativas antes del despliegue.")
        print()
        return 2


if __name__ == "__main__":
    try:
        exit_code = main()
        print("="*80)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
