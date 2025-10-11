"""
Test del flujo completo para HOSO 30/40
"""
import sys
sys.path.append('.')

from app.services.pricing import PricingService
from app.services.openai_service import OpenAIService
from app.services.utils import parse_ai_analysis_to_query

def test_full_flow():
    """
    Simula el flujo completo del usuario
    """
    print("🧪 Simulando flujo completo HOSO 30/40...\n")
    
    # 1. Mensaje del usuario
    user_message = "Cotizar un Contenedor de 30/40 con 0.15 de flete"
    print(f"1️⃣ Mensaje del usuario: '{user_message}'")
    print()
    
    # 2. Análisis de OpenAI
    openai_service = OpenAIService()
    ai_analysis = openai_service._basic_intent_analysis(user_message)
    
    print(f"2️⃣ Análisis de intención:")
    print(f"   Intent: {ai_analysis.get('intent')}")
    print(f"   Product: {ai_analysis.get('product')}")
    print(f"   Size: {ai_analysis.get('size')}")
    print(f"   Glaseo factor: {ai_analysis.get('glaseo_factor')}")
    print(f"   Flete custom: {ai_analysis.get('flete_custom')}")
    print()
    
    # 3. Usuario responde con glaseo 20%
    print(f"3️⃣ Usuario responde: '20' (glaseo 20%)")
    
    # Actualizar análisis con glaseo
    ai_analysis['glaseo_factor'] = 0.80
    ai_analysis['glaseo_percentage'] = 20
    print()
    
    # 4. Convertir a query
    ai_query = parse_ai_analysis_to_query(ai_analysis)
    
    print(f"4️⃣ Query generada:")
    print(f"   Product: {ai_query.get('product')}")
    print(f"   Size: {ai_query.get('size')}")
    print(f"   Glaseo factor: {ai_query.get('glaseo_factor')}")
    print(f"   Flete custom: {ai_query.get('flete_custom')}")
    print()
    
    # 5. Calcular precio
    pricing_service = PricingService()
    price_info = pricing_service.get_shrimp_price(ai_query)
    
    print(f"5️⃣ Precio calculado:")
    print(f"   Precio base: ${price_info.get('precio_kg', 0):.2f}")
    print(f"   Precio FOB: ${price_info.get('precio_fob_kg', 0):.2f}")
    print(f"   Precio glaseo: ${price_info.get('precio_glaseo_kg', 0):.2f}")
    print(f"   Precio FOB+glaseo: ${price_info.get('precio_fob_con_glaseo_kg', 0):.2f}")
    print(f"   Precio CFR final: ${price_info.get('precio_final_kg', 0):.2f}")
    print(f"   Flete usado: ${price_info.get('flete', 0):.2f}")
    print()
    
    # 6. Verificar
    precio_cfr = price_info.get('precio_final_kg', 0)
    print(f"6️⃣ Verificación:")
    print(f"   Precio CFR calculado: ${precio_cfr:.2f}")
    print(f"   Precio CFR esperado: $4.63")
    
    if abs(precio_cfr - 4.63) < 0.01:
        print(f"   ✅ Correcto!")
    else:
        print(f"   ❌ Incorrecto! Diferencia: ${abs(precio_cfr - 4.63):.2f}")

if __name__ == "__main__":
    test_full_flow()
