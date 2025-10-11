"""
Test para verificar cómo el bot procesa mensajes con múltiples productos
"""
import sys
sys.path.append('.')

from app.services.openai_service import OpenAIService

def test_multiple_products_message():
    """
    Prueba cómo el bot procesa un mensaje con múltiples productos
    """
    print("🧪 Probando mensaje con múltiples productos...\n")
    
    # Mensaje real del cliente
    user_message = """Precios para esto por favor ..
HOSO 50-60 block 10x4
HLSO 16-20 block 10x4
HLSO 26-30 block 10x4
HLSO 36-40 block 10x4
HLSO 51-60 block 10x4
PYD TAIL OFF 61-70 IQF 5X2
16-20 EZPEEL IQF 10X2
26-30 EZPEEL IQF 10X2
DDP LA or Houston"""
    
    print(f"📱 Mensaje del cliente:")
    print(f"{user_message}")
    print("\n" + "="*80 + "\n")
    
    # Analizar con el servicio actual
    openai_service = OpenAIService()
    ai_analysis = openai_service._basic_intent_analysis(user_message)
    
    print(f"🤖 Análisis del bot actual:")
    print(f"   Intent: {ai_analysis.get('intent')}")
    print(f"   Product: {ai_analysis.get('product')}")
    print(f"   Size: {ai_analysis.get('size')}")
    print(f"   Destination: {ai_analysis.get('destination')}")
    print(f"   Confidence: {ai_analysis.get('confidence')}")
    print()
    
    # Análisis de lo que debería detectar
    print("📊 Lo que DEBERÍA detectar:")
    print("   ✓ Intent: pricing/proforma (solicitud de precios)")
    print("   ✓ Múltiples productos:")
    print("      1. HOSO 50-60 (o 50/60)")
    print("      2. HLSO 16-20")
    print("      3. HLSO 26-30")
    print("      4. HLSO 36-40")
    print("      5. HLSO 51-60")
    print("      6. P&D TAIL OFF 61-70 (PYD = P&D)")
    print("      7. EZPEEL 16-20")
    print("      8. EZPEEL 26-30")
    print("   ✓ Destino: LA o Houston (DDP)")
    print("   ✓ Formato: block 10x4, IQF 5X2, IQF 10X2")
    print()
    
    # Problema actual
    print("⚠️ PROBLEMA ACTUAL:")
    print("   El bot solo puede procesar UN producto a la vez")
    print("   Solo detectará el primer producto encontrado")
    print()
    
    # Solución propuesta
    print("💡 SOLUCIONES POSIBLES:")
    print()
    print("   OPCIÓN 1: Procesamiento Secuencial")
    print("   ----------------------------------------")
    print("   Bot: 'Detecté 8 productos. ¿Quieres cotización para todos?'")
    print("   Bot: 'Generaré una proforma por cada producto.'")
    print("   Bot: [Genera 8 PDFs separados]")
    print()
    
    print("   OPCIÓN 2: Proforma Consolidada (RECOMENDADA)")
    print("   ----------------------------------------")
    print("   Bot: 'Detecté 8 productos. Generando cotización consolidada...'")
    print("   Bot: [Genera 1 PDF con tabla de todos los productos]")
    print()
    
    print("   OPCIÓN 3: Interactiva")
    print("   ----------------------------------------")
    print("   Bot: 'Detecté 8 productos:'")
    print("   Bot: '1. HOSO 50-60'")
    print("   Bot: '2. HLSO 16-20'")
    print("   Bot: '...'")
    print("   Bot: '¿Para cuáles necesitas cotización?'")
    print("   Usuario: 'Todos' o '1,3,5'")
    print()

if __name__ == "__main__":
    test_multiple_products_message()
