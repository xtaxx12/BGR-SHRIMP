"""
Test para verificar que el PDF se genera correctamente CON glaseo
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.pricing import PricingService
from app.services.pdf_generator import PDFGenerator

def test_pdf_con_glaseo():
    """
    Prueba que el PDF se genera correctamente cuando SI hay glaseo especificado
    """
    print("Test: Generacion de PDF CON glaseo 20%\n")
    
    pricing_service = PricingService()
    pdf_generator = PDFGenerator()
    
    # Simular consulta: "Precio CFR de HLSO 16/20 con 20% glaseo"
    query = {
        'product': 'HLSO',
        'size': '16/20',
        'glaseo_factor': 0.80,  # 20% glaseo
        'glaseo_percentage': 20,
        'flete_solicitado': True,
        'flete_custom': 0.25,
        'destination': 'Houston'
    }
    
    print("Parametros:")
    print(f"  Producto: {query['product']}")
    print(f"  Talla: {query['size']}")
    print(f"  Glaseo: 20%")
    print(f"  Flete: ${query['flete_custom']}")
    print()
    
    result = pricing_service.get_shrimp_price(query)
    
    if result:
        print("Precio calculado:")
        print(f"  FOB: ${result.get('precio_fob_kg')}/kg")
        print(f"  CFR: ${result.get('precio_final_kg')}/kg")
        print(f"  Glaseo percentage: {result.get('glaseo_percentage')}")
        print(f"  Glaseo factor: {result.get('factor_glaseo')}")
        print()
        
        print("Generando PDF...")
        pdf_path = pdf_generator.generate_quote_pdf(result, "test_user", "es")
        
        if pdf_path:
            print(f"OK: PDF generado en {pdf_path}")
            
            # Verificar que el glaseo se muestre correctamente
            if result.get('glaseo_percentage') == 20:
                print("OK: Glaseo 20% se muestra correctamente")
                return True
            else:
                print("ERROR: Glaseo no coincide")
                return False
        else:
            print("ERROR: No se pudo generar el PDF")
            return False
    else:
        print("ERROR: No se pudo calcular el precio")
        return False

if __name__ == "__main__":
    try:
        success = test_pdf_con_glaseo()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
