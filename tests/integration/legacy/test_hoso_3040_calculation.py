"""
Test para verificar el cálculo de HOSO 30/40 con glaseo 20% y flete 0.15
"""
import sys
sys.path.append('.')

from app.services.pricing import PricingService

def test_hoso_3040_calculation():
    """
    Verifica el cálculo de HOSO 30/40 con glaseo 20% y flete 0.15
    """
    print("🧪 Probando cálculo HOSO 30/40...\n")
    
    # Crear servicio de pricing
    pricing_service = PricingService()
    
    # Consulta para HOSO 30/40 con glaseo 20% y flete 0.15
    query = {
        'product': 'HOSO',
        'size': '30/40',
        'glaseo_factor': 0.80,  # 20% glaseo = factor 0.80
        'glaseo_percentage': 20,
        'flete_custom': 0.15,
        'flete_solicitado': True,
        'custom_calculation': True
    }
    
    print("📋 Parámetros:")
    print(f"   Producto: {query['product']}")
    print(f"   Talla: {query['size']}")
    print(f"   Glaseo: {query['glaseo_percentage']}% (factor {query['glaseo_factor']})")
    print(f"   Flete: ${query['flete_custom']}")
    print()
    
    # Obtener precio
    result = pricing_service.get_shrimp_price(query)
    
    if result:
        print("✅ Resultado del cálculo:")
        print(f"   📊 Precio base (Excel): ${result.get('precio_kg', 0):.2f}/kg")
        print(f"   🚢 Precio FOB: ${result.get('precio_fob_kg', 0):.2f}/kg")
        print(f"   ❄️ Precio con glaseo: ${result.get('precio_glaseo_kg', 0):.2f}/kg")
        print(f"   💰 Precio FOB + glaseo: ${result.get('precio_fob_con_glaseo_kg', 0):.2f}/kg")
        print(f"   ✈️ Precio CFR (final): ${result.get('precio_final_kg', 0):.2f}/kg")
        print()
        
        # Verificar cálculo manual
        precio_base = result.get('precio_kg', 0)
        costo_fijo = 0.29
        glaseo_factor = 0.80
        flete = 0.15
        
        print("🧮 Verificación manual del cálculo:")
        print(f"   1. Precio base: ${precio_base:.2f}")
        
        precio_neto = precio_base - costo_fijo
        print(f"   2. Precio neto = ${precio_base:.2f} - ${costo_fijo:.2f} = ${precio_neto:.2f}")
        
        precio_glaseo = precio_neto * glaseo_factor
        print(f"   3. Precio con glaseo = ${precio_neto:.2f} × {glaseo_factor} = ${precio_glaseo:.2f}")
        
        precio_fob_glaseo = precio_glaseo + costo_fijo
        print(f"   4. Precio FOB + glaseo = ${precio_glaseo:.2f} + ${costo_fijo:.2f} = ${precio_fob_glaseo:.2f}")
        
        precio_cfr = precio_fob_glaseo + flete
        print(f"   5. Precio CFR = ${precio_fob_glaseo:.2f} + ${flete:.2f} = ${precio_cfr:.2f}")
        print()
        
        # Comparar con Excel
        precio_cfr_result = result.get('precio_final_kg', 0)
        print(f"📊 Comparación:")
        print(f"   Calculado: ${precio_cfr_result:.2f}")
        print(f"   Manual: ${precio_cfr:.2f}")
        print(f"   Excel esperado: $4.63")
        print()
        
        if abs(precio_cfr_result - 4.63) < 0.01:
            print("✅ El cálculo coincide con el Excel!")
        else:
            print(f"❌ El cálculo NO coincide. Diferencia: ${abs(precio_cfr_result - 4.63):.2f}")
            print()
            print("🔍 Investigando la causa...")
            
            # Verificar si el precio base es correcto
            if abs(precio_base - 5.52) > 0.01:
                print(f"   ⚠️ Precio base incorrecto: ${precio_base:.2f} (esperado: $5.52)")
            
            # Verificar si el glaseo es correcto
            if abs(glaseo_factor - 0.80) > 0.01:
                print(f"   ⚠️ Factor glaseo incorrecto: {glaseo_factor} (esperado: 0.80)")
            
            # Verificar si el flete es correcto
            flete_usado = result.get('flete', 0)
            if abs(flete_usado - 0.15) > 0.01:
                print(f"   ⚠️ Flete incorrecto: ${flete_usado:.2f} (esperado: $0.15)")
    else:
        print("❌ No se pudo obtener el precio")

if __name__ == "__main__":
    test_hoso_3040_calculation()
