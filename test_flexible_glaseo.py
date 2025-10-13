"""
Test para verificar que el bot acepta cualquier porcentaje de glaseo
"""
import sys
sys.path.append('.')

# Importar la función helper
from app.routes import glaseo_percentage_to_factor

def test_flexible_glaseo():
    """
    Prueba la conversión de glaseo con diferentes porcentajes
    """
    print("🧪 Probando conversión flexible de glaseo...\n")
    
    test_cases = [
        (10, 0.90),
        (14, 0.86),
        (15, 0.85),
        (20, 0.80),
        (25, 0.75),
        (30, 0.70),
        (5, 0.95),
        (50, 0.50),
    ]
    
    print("="*80)
    print("Fórmula: Factor = 1 - (percentage / 100)")
    print("="*80)
    print()
    
    all_passed = True
    
    for percentage, expected_factor in test_cases:
        calculated_factor = glaseo_percentage_to_factor(percentage)
        
        if abs(calculated_factor - expected_factor) < 0.001:  # Tolerancia para flotantes
            status = "✅"
        else:
            status = "❌"
            all_passed = False
        
        print(f"{status} Glaseo {percentage}%:")
        print(f"   Esperado: {expected_factor}")
        print(f"   Calculado: {calculated_factor}")
        print(f"   Fórmula: 1 - ({percentage}/100) = {calculated_factor}")
        print()
    
    print("="*80)
    if all_passed:
        print("✅ Todos los tests pasaron!")
    else:
        print("❌ Algunos tests fallaron")
    print("="*80)
    
    # Ejemplos prácticos
    print("\n📋 Ejemplos prácticos:")
    print()
    print("Usuario: 'Proforma HLSO 16/20 con glaseo 15%'")
    print(f"   → Factor calculado: {glaseo_percentage_to_factor(15)}")
    print(f"   → Precio neto $10.00 × {glaseo_percentage_to_factor(15)} = ${10.00 * glaseo_percentage_to_factor(15):.2f}")
    print()
    print("Usuario: 'Cotización HOSO 30/40 glaseo 25%'")
    print(f"   → Factor calculado: {glaseo_percentage_to_factor(25)}")
    print(f"   → Precio neto $8.00 × {glaseo_percentage_to_factor(25)} = ${8.00 * glaseo_percentage_to_factor(25):.2f}")
    print()
    print("Usuario: 'HLSO 21/25 al 14%'")
    print(f"   → Factor calculado: {glaseo_percentage_to_factor(14)}")
    print(f"   → Precio neto $12.00 × {glaseo_percentage_to_factor(14)} = ${12.00 * glaseo_percentage_to_factor(14):.2f}")

if __name__ == "__main__":
    test_flexible_glaseo()
