"""
Test completo para verificar que NO se aplica flete cuando se menciona DDP
"""
import sys
sys.path.insert(0, '.')

from app.services.pricing import PricingService
from app.services.openai_service import OpenAIService
from app.services.utils import parse_ai_analysis_to_query

def test_ddp_full_flow():
    """
    Simula el flujo completo: análisis → query → cálculo de precio
    """
    print("🧪 Test completo de flujo DDP\n")
    print("="*60)
    
    # Inicializar servicios
    openai_service = OpenAIService()
    pricing_service = PricingService()
    
    # Mensaje del usuario
    mensaje = "Precios para esto por favor - HOSO 50-60 black 10x4 HLSO 16-20 block 10x4 DDP LA or Houston al 15%"
    
    print(f"\n📝 Mensaje del usuario:")
    print(f"   '{mensaje}'\n")
    
    # Paso 1: Análisis de intención
    print("🔍 PASO 1: Análisis de intención")
    print("-" * 60)
    ai_analysis = openai_service._basic_intent_analysis(mensaje)
    print(f"   ✓ Intent: {ai_analysis.get('intent')}")
    print(f"   ✓ Product: {ai_analysis.get('product')}")
    print(f"   ✓ Size: {ai_analysis.get('size')}")
    print(f"   ✓ Glaseo: {ai_analysis.get('glaseo_percentage')}%")
    print(f"   ✓ Is DDP: {ai_analysis.get('is_ddp')}")
    print(f"   ✓ Flete custom: {ai_analysis.get('flete_custom')}")
    
    # Paso 2: Convertir a query
    print(f"\n🔧 PASO 2: Conversión a query")
    print("-" * 60)
    query = parse_ai_analysis_to_query(ai_analysis)
    
    if not query:
        print("   ❌ ERROR: No se pudo generar query")
        return
    
    print(f"   ✓ Product: {query.get('product')}")
    print(f"   ✓ Size: {query.get('size')}")
    print(f"   ✓ Glaseo factor: {query.get('glaseo_factor')}")
    print(f"   ✓ Glaseo percentage: {query.get('glaseo_percentage')}%")
    print(f"   ✓ Flete solicitado: {query.get('flete_solicitado')}")
    print(f"   ✓ Flete custom: {query.get('flete_custom')}")
    
    # Paso 3: Calcular precio
    print(f"\n💰 PASO 3: Cálculo de precio")
    print("-" * 60)
    
    try:
        price_info = pricing_service.get_shrimp_price(query)
        
        if price_info:
            print(f"   ✓ Producto: {price_info.get('producto')} {price_info.get('talla')}")
            print(f"   ✓ Precio FOB: ${price_info.get('precio_kg', 0):.2f}/kg")
            print(f"   ✓ Precio con glaseo: ${price_info.get('precio_glaseo_kg', 0):.2f}/kg")
            print(f"   ✓ Precio FOB con glaseo: ${price_info.get('precio_fob_con_glaseo_kg', 0):.2f}/kg")
            print(f"   ✓ Flete aplicado: ${price_info.get('flete', 0):.2f}/kg")
            print(f"   ✓ Precio final CFR: ${price_info.get('precio_final_kg', 0):.2f}/kg")
            
            # Verificaciones
            print(f"\n✅ VERIFICACIONES:")
            print("-" * 60)
            
            if price_info.get('flete', 0) == 0:
                print("   ✅ CORRECTO: NO se aplicó flete (flete = $0.00)")
            else:
                print(f"   ❌ ERROR: Se aplicó flete de ${price_info.get('flete', 0):.2f}")
            
            if price_info.get('glaseo_percentage') == 15:
                print("   ✅ CORRECTO: Glaseo 15% aplicado correctamente")
            else:
                print(f"   ❌ ERROR: Glaseo esperado 15%, aplicado {price_info.get('glaseo_percentage')}%")
            
            # Verificar que precio final = precio FOB con glaseo (sin flete adicional)
            precio_fob_con_glaseo = price_info.get('precio_fob_con_glaseo_kg', 0)
            precio_final = price_info.get('precio_final_kg', 0)
            
            if abs(precio_fob_con_glaseo - precio_final) < 0.01:
                print("   ✅ CORRECTO: Precio final = Precio FOB con glaseo (sin flete adicional)")
            else:
                print(f"   ❌ ERROR: Precio final (${precio_final:.2f}) ≠ Precio FOB con glaseo (${precio_fob_con_glaseo:.2f})")
        else:
            print("   ❌ ERROR: No se pudo calcular el precio")
    
    except Exception as e:
        print(f"   ❌ ERROR en cálculo: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_ddp_full_flow()
