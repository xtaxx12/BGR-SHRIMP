"""
Test para verificar la detección correcta de "cola" en solicitudes CFR
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.openai_service import OpenAIService

def test_cfr_cola_detection():
    """
    Test para verificar que "Precio cfr de cola 20/30 con 0.25 de flete"
    se detecta correctamente como P&D IQF (NO como COOKED)
    """
    print("=" * 80)
    print("🧪 TEST: Detección de 'cola' en solicitudes CFR")
    print("=" * 80)
    print()
    
    openai_service = OpenAIService()
    
    # Caso 1: "Precio cfr de cola 20/30 con 0.25 de flete"
    # Debe detectar: HLSO 20/30 con flete 0.25 (NO COOKED ni P&D IQF)
    print("📝 Caso 1: Precio CFR de cola 20/30 con 0.25 de flete")
    print("-" * 80)
    
    message1 = "Precio cfr de cola 20/30 con 0.25 de flete"
    result1 = openai_service._basic_intent_analysis(message1)
    
    print(f"Mensaje: '{message1}'")
    print(f"Resultado:")
    print(f"  - Intent: {result1.get('intent')}")
    print(f"  - Product: {result1.get('product')}")
    print(f"  - Size: {result1.get('size')}")
    print(f"  - Flete: {result1.get('flete_custom')}")
    print(f"  - Glaseo: {result1.get('glaseo_factor')}")
    print()
    
    # Verificar resultado
    if result1.get('product') == 'HLSO':
        print("✅ CORRECTO: Detectó HLSO (camarón sin cabeza, con cáscara)")
    elif result1.get('product') == 'COOKED':
        print("❌ ERROR: Detectó COOKED (debería ser HLSO)")
    elif result1.get('product') == 'P&D IQF':
        print("❌ ERROR: Detectó P&D IQF (debería ser HLSO)")
    else:
        print(f"⚠️ ADVERTENCIA: Detectó '{result1.get('product')}' (esperado: HLSO)")
    
    print()
    print("-" * 80)
    print()
    
    # Caso 2: "Precio cfr de cola cocedero 20/30 con 0.25 de flete"
    # Debe detectar: COOKED 20/30 con flete 0.25
    print("📝 Caso 2: Precio CFR de cola cocedero 20/30 con 0.25 de flete")
    print("-" * 80)
    
    message2 = "Precio cfr de cola cocedero 20/30 con 0.25 de flete"
    result2 = openai_service._basic_intent_analysis(message2)
    
    print(f"Mensaje: '{message2}'")
    print(f"Resultado:")
    print(f"  - Intent: {result2.get('intent')}")
    print(f"  - Product: {result2.get('product')}")
    print(f"  - Size: {result2.get('size')}")
    print(f"  - Flete: {result2.get('flete_custom')}")
    print(f"  - Glaseo: {result2.get('glaseo_factor')}")
    print()
    
    # Verificar resultado
    if result2.get('product') == 'COOKED':
        print("✅ CORRECTO: Detectó COOKED (colas cocidas)")
    elif result2.get('product') == 'P&D IQF':
        print("❌ ERROR: Detectó P&D IQF (debería ser COOKED)")
    else:
        print(f"⚠️ ADVERTENCIA: Detectó '{result2.get('product')}' (esperado: COOKED)")
    
    print()
    print("-" * 80)
    print()
    
    # Caso 3: "Colas 21/25" (sin cocedero, sin CFR)
    # Debe detectar: HLSO 21/25
    print("📝 Caso 3: Colas 21/25 (sin cocedero)")
    print("-" * 80)
    
    message3 = "Colas 21/25"
    result3 = openai_service._basic_intent_analysis(message3)
    
    print(f"Mensaje: '{message3}'")
    print(f"Resultado:")
    print(f"  - Intent: {result3.get('intent')}")
    print(f"  - Product: {result3.get('product')}")
    print(f"  - Size: {result3.get('size')}")
    print()
    
    # Verificar resultado
    if result3.get('product') == 'HLSO':
        print("✅ CORRECTO: Detectó HLSO (camarón sin cabeza, con cáscara)")
    elif result3.get('product') == 'COOKED':
        print("❌ ERROR: Detectó COOKED (debería ser HLSO)")
    elif result3.get('product') == 'P&D IQF':
        print("❌ ERROR: Detectó P&D IQF (debería ser HLSO)")
    else:
        print(f"⚠️ ADVERTENCIA: Detectó '{result3.get('product')}' (esperado: HLSO)")
    
    print()
    print("=" * 80)
    print("🏁 FIN DEL TEST")
    print("=" * 80)

if __name__ == "__main__":
    test_cfr_cola_detection()
