#!/usr/bin/env python3
"""
Prueba después de compartir Google Sheets
"""

from app.services.excel import ExcelService
import logging

# Configurar logging para ver mensajes detallados
logging.basicConfig(level=logging.INFO)

def test_after_sharing():
    print("=== PRUEBA DESPUÉS DE COMPARTIR GOOGLE SHEETS ===\n")
    
    print("🔄 Inicializando servicio...")
    excel_service = ExcelService()
    
    if excel_service.prices_data:
        products = excel_service.get_available_products()
        print(f"✅ Servicio funcionando")
        print(f"📦 Productos: {products}")
        
        if products:
            first_product = products[0]
            sizes = excel_service.get_available_sizes(first_product)
            print(f"📏 Tallas para {first_product}: {sizes}")
            
            if sizes:
                price_data = excel_service.get_price_data(sizes[0], first_product)
                print(f"💰 Precio {first_product} {sizes[0]}: ${price_data['precio_kg']:.2f}/kg - ${price_data['precio_lb']:.2f}/lb")
        
        print(f"\n📊 Total productos: {len(products)}")
        print(f"📊 Total tallas: {sum(len(excel_service.get_available_sizes(p)) for p in products)}")
        
    else:
        print("❌ Error: Servicio no inicializado")

if __name__ == "__main__":
    test_after_sharing()