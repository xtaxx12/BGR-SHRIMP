"""
Test para verificar que el sistema NO aplica flete cuando se menciona DDP
"""
import sys
sys.path.insert(0, '.')

from app.services.openai_service import OpenAIService
from app.services.utils import parse_ai_analysis_to_query

def test_ddp_detection():
    """
    Verifica que cuando el usuario dice "precio DDP", el sistema NO aplica flete
    """
    print("🧪 Probando detección de DDP...\n")
    
    openai_service = OpenAIService()
    
    # Mensaje del usuario con DDP (sin especificar flete)
    mensaje = "Precios para esto por favor ..HOSO 50-60 block 10x4HLSO 16-20 block 10x4HLSO 26-30 block 10x4HLSO 36-40 block 10x4HLSO 51-60 block 10x4PYD TAIL OFF 61-70 IQF 5X216-20 EZPEEL IQF 10X226-30 EZPEEL IQF 10X2DDP LA or Houston al 15%"
    
    print(f"📝 Mensaje del usuario:")
    print(f"   {mensaje}\n")
    
    # Analizar intención
    ai_analysis = openai_service._basic_intent_analysis(mensaje)
    
    print(f"🔍 Análisis de intención:")
    print(f"   Intent: {ai_analysis.get('intent')}")
    print(f"   Product: {ai_analysis.get('product')}")
    print(f"   Size: {ai_analysis.get('size')}")
    print(f"   Glaseo: {ai_analysis.get('glaseo_percentage')}% (factor: {ai_analysis.get('glaseo_factor')})")
    print(f"   Is DDP: {ai_analysis.get('is_ddp')}")
    print(f"   Destination: {ai_analysis.get('destination')}")
    print(f"   Flete custom: {ai_analysis.get('flete_custom')}\n")
    
    # Convertir a query
    query = parse_ai_analysis_to_query(ai_analysis)
    
    if query:
        print(f"✅ Query generado:")
        print(f"   Product: {query.get('product')}")
        print(f"   Size: {query.get('size')}")
        print(f"   Glaseo factor: {query.get('glaseo_factor')}")
        print(f"   Glaseo percentage: {query.get('glaseo_percentage')}%")
        print(f"   Flete solicitado: {query.get('flete_solicitado')}")
        print(f"   Flete custom: {query.get('flete_custom')}\n")
        
        # Verificaciones
        if ai_analysis.get('is_ddp'):
            if query.get('flete_solicitado') and query.get('flete_custom') is None:
                print("✅ CORRECTO: DDP detectado SIN flete - el sistema PEDIRÁ el valor del flete")
            elif query.get('flete_solicitado') and query.get('flete_custom') is not None:
                print(f"✅ CORRECTO: DDP detectado CON flete ${query.get('flete_custom'):.2f} especificado")
            else:
                print("❌ ERROR: DDP detectado pero NO se está solicitando flete")
        else:
            print("⚠️ ADVERTENCIA: DDP NO fue detectado en el mensaje")
        
        # Verificar glaseo
        if query.get('glaseo_percentage') == 15:
            print("✅ CORRECTO: Glaseo 15% detectado correctamente")
        else:
            print(f"❌ ERROR: Glaseo esperado 15%, detectado {query.get('glaseo_percentage')}%")
    else:
        print("❌ No se pudo generar query")

if __name__ == "__main__":
    test_ddp_detection()
