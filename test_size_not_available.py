"""
Test para verificar que se muestra un mensaje claro cuando la talla no está disponible
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.pricing import PricingService

def test_size_not_available_for_product():
    """
    Test para verificar que cuando se solicita HLSO 20/30 (talla no disponible),
    se muestra un mensaje claro con las tallas disponibles
    """
    print("=" * 80)
    print("🧪 TEST: Mensaje de error cuando la talla no está disponible")
    print("=" * 80)
    print()
    
    pricing_service = PricingService()
    
    # Caso 1: HLSO 20/30 (talla no disponible para HLSO)
    print("📝 Caso 1: Solicitar HLSO 20/30 (talla no disponible)")
    print("-" * 80)
    
    user_input = {
        'product': 'HLSO',
        'size': '20/30',
        'glaseo_factor': None,
        'glaseo_percentage': 0,
        'flete_custom': 0.25,
        'flete_solicitado': True
    }
    
    result = pricing_service.get_shrimp_price(user_input)
    
    print(f"Solicitud: HLSO 20/30 con flete 0.25")
    print(f"Resultado:")
    if result:
        if result.get('error'):
            print(f"  ✅ Error detectado correctamente")
            print(f"  📝 Mensaje: {result.get('error_message')}")
            print(f"  📏 Tallas disponibles: {result.get('available_sizes')}")
        else:
            print(f"  ❌ ERROR: No se detectó el error (debería retornar error)")
            print(f"  Resultado: {result}")
    else:
        print(f"  ❌ ERROR: Retornó None (debería retornar dict con error)")
    
    print()
    print("-" * 80)
    print()
    
    # Caso 2: HLSO 16/20 (talla disponible)
    print("📝 Caso 2: Solicitar HLSO 16/20 (talla disponible)")
    print("-" * 80)
    
    user_input2 = {
        'product': 'HLSO',
        'size': '16/20',
        'glaseo_factor': None,
        'glaseo_percentage': 0,
        'flete_custom': 0.25,
        'flete_solicitado': True
    }
    
    result2 = pricing_service.get_shrimp_price(user_input2)
    
    print(f"Solicitud: HLSO 16/20 con flete 0.25")
    print(f"Resultado:")
    if result2:
        if result2.get('error'):
            print(f"  ❌ ERROR: Detectó error cuando no debería")
            print(f"  Mensaje: {result2.get('error_message')}")
        else:
            print(f"  ✅ Precio calculado correctamente")
            print(f"  💰 Precio FOB: ${result2.get('precio_fob_kg', 0):.2f}/kg")
            print(f"  ✈️ Precio CFR: ${result2.get('precio_final_kg', 0):.2f}/kg")
    else:
        print(f"  ❌ ERROR: Retornó None")
    
    print()
    print("=" * 80)
    print("🏁 FIN DEL TEST")
    print("=" * 80)

if __name__ == "__main__":
    test_size_not_available_for_product()
