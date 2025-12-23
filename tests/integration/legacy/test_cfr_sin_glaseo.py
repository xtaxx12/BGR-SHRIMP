"""
Test para verificar que CFR sin glaseo NO muestra glaseo en el PDF
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.pricing import PricingService

def test_cfr_sin_glaseo():
    """
    Prueba que cuando el usuario solicita CFR sin mencionar glaseo,
    el sistema NO debe aplicar ni mostrar ningún glaseo por defecto.
    """
    print("🧪 Probando CFR sin glaseo especificado...\n")
    
    # Inicializar servicio
    pricing_service = PricingService()
    
    # Simular consulta: "Precio CFR de HLSO 16/20"
    # El usuario NO menciona glaseo, solo pide precio CFR
    query = {
        'product': 'HLSO',
        'size': '16/20',
        'glaseo_factor': None,  # No especificado
        'glaseo_percentage': None,  # No especificado
        'flete_solicitado': True,  # Solicita CFR (con flete)
        'flete_custom': 0.25,
        'destination': 'Houston'
    }
    
    print(f"📋 Parámetros:")
    print(f"   Producto: {query['product']}")
    print(f"   Talla: {query['size']}")
    print(f"   Glaseo especificado: NO")
    print(f"   Flete: ${query['flete_custom']}")
    print(f"   Destino: {query['destination']}")
    print()
    
    # Obtener precio
    result = pricing_service.get_shrimp_price(query)
    
    if result:
        print("✅ Resultado del cálculo:")
        print(f"   📊 Precio FOB: ${result.get('precio_fob_kg')}/kg")
        print(f"   ✈️ Precio CFR (final): ${result.get('precio_final_kg')}/kg")
        print(f"   ❄️ Glaseo percentage: {result.get('glaseo_percentage')}")
        print(f"   ❄️ Glaseo factor: {result.get('factor_glaseo')}")
        print()
        
        # Verificar que NO hay glaseo
        if result.get('glaseo_percentage') is None and result.get('factor_glaseo') is None:
            print("✅ CORRECTO: No se aplicó glaseo por defecto")
            print("   El PDF mostrará 'N/A' en el campo de glaseo")
            return True
        else:
            print("❌ ERROR: Se aplicó glaseo por defecto cuando no debería")
            print(f"   Glaseo percentage: {result.get('glaseo_percentage')}")
            print(f"   Glaseo factor: {result.get('factor_glaseo')}")
            return False
    else:
        print("❌ Error: No se pudo calcular el precio")
        return False

if __name__ == "__main__":
    success = test_cfr_sin_glaseo()
    sys.exit(0 if success else 1)
