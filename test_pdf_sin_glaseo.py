"""
Test para verificar que el PDF se genera correctamente sin glaseo
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.pricing import PricingService
from app.services.pdf_generator import PDFGenerator

def test_pdf_sin_glaseo():
    """
    Prueba que el PDF se genera correctamente cuando no hay glaseo especificado
    """
    print("Test: Generacion de PDF sin glaseo\n")
    
    # Inicializar servicios
    pricing_service = PricingService()
    pdf_generator = PDFGenerator()
    
    # Simular consulta: "Precio CFR de HLSO 16/20"
    query = {
        'product': 'HLSO',
        'size': '16/20',
        'glaseo_factor': None,
        'glaseo_percentage': None,
        'flete_solicitado': True,
        'flete_custom': 0.25,
        'destination': 'Houston'
    }
    
    print("Parametros:")
    print(f"  Producto: {query['product']}")
    print(f"  Talla: {query['size']}")
    print(f"  Glaseo: NO especificado")
    print(f"  Flete: ${query['flete_custom']}")
    print()
    
    # Obtener precio
    result = pricing_service.get_shrimp_price(query)
    
    if result:
        print("Precio calculado:")
        print(f"  FOB: ${result.get('precio_fob_kg')}/kg")
        print(f"  CFR: ${result.get('precio_final_kg')}/kg")
        print(f"  Glaseo percentage: {result.get('glaseo_percentage')}")
        print(f"  Glaseo factor: {result.get('factor_glaseo')}")
        print()
        
        # Intentar generar PDF
        print("Generando PDF...")
        pdf_path = pdf_generator.generate_quote_pdf(result, "test_user", "es")
        
        if pdf_path:
            print(f"OK: PDF generado en {pdf_path}")
            return True
        else:
            print("ERROR: No se pudo generar el PDF")
            return False
    else:
        print("ERROR: No se pudo calcular el precio")
        return False

if __name__ == "__main__":
    try:
        success = test_pdf_sin_glaseo()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
