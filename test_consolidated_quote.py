"""
Test para verificar la funcionalidad de cotización consolidada
"""
import sys
sys.path.append('.')

from app.services.openai_service import OpenAIService
from app.services.pricing import PricingService
from app.services.pdf_generator import PDFGenerator

def test_consolidated_quote():
    """
    Prueba el flujo completo de cotización consolidada
    """
    print("🧪 Probando cotización consolidada...\n")
    
    # 1. Mensaje del usuario
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
    
    print(f"1️⃣ Mensaje del usuario:")
    print(f"{user_message}")
    print("\n" + "="*80 + "\n")
    
    # 2. Detectar múltiples productos
    openai_service = OpenAIService()
    products = openai_service.detect_multiple_products(user_message)
    
    print(f"2️⃣ Productos detectados: {len(products) if products else 0}")
    if products:
        for i, p in enumerate(products, 1):
            print(f"   {i}. {p['product']} {p['size']}")
    print()
    
    # 3. Calcular precios para todos
    if products:
        print(f"3️⃣ Calculando precios con glaseo 20%...")
        
        pricing_service = PricingService()
        products_info = []
        
        for product_data in products:
            query = {
                'product': product_data['product'],
                'size': product_data['size'],
                'glaseo_factor': 0.80,
                'glaseo_percentage': 20,
                'flete_custom': 0.15,
                'flete_solicitado': True,
                'custom_calculation': True
            }
            
            price_info = pricing_service.get_shrimp_price(query)
            
            if price_info:
                products_info.append(price_info)
                print(f"   ✅ {product_data['product']} {product_data['size']}: ${price_info.get('precio_final_kg', 0):.2f}/kg")
            else:
                print(f"   ❌ {product_data['product']} {product_data['size']}: Sin precio")
        
        print()
        print(f"4️⃣ Precios calculados: {len(products_info)}/{len(products)}")
        print()
        
        # 4. Generar PDF consolidado
        if products_info:
            print(f"5️⃣ Generando PDF consolidado...")
            
            pdf_generator = PDFGenerator()
            pdf_path = pdf_generator.generate_consolidated_quote_pdf(
                products_info,
                user_phone="+593988057425",
                language="es",
                glaseo_percentage=20,
                destination="LA / Houston"
            )
            
            if pdf_path:
                print(f"   ✅ PDF generado: {pdf_path}")
                
                # Verificar tamaño del archivo
                import os
                if os.path.exists(pdf_path):
                    size = os.path.getsize(pdf_path)
                    print(f"   📊 Tamaño: {size} bytes")
                    print()
                    print("✅ ¡Test completado exitosamente!")
                else:
                    print("   ❌ Archivo no encontrado")
            else:
                print("   ❌ Error generando PDF")
        else:
            print("❌ No se pudieron calcular precios")
    else:
        print("❌ No se detectaron productos")

if __name__ == "__main__":
    test_consolidated_quote()
