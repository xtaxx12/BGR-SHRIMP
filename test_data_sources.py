#!/usr/bin/env python3
"""
Prueba de fuentes de datos (Google Sheets vs Excel local)
"""

import os
from dotenv import load_dotenv
from app.services.excel import ExcelService

# Cargar variables de entorno
load_dotenv()

def test_data_sources():
    print("=== PRUEBA DE FUENTES DE DATOS ===\n")
    
    # Verificar configuración
    google_sheets_id = os.getenv("GOOGLE_SHEETS_ID")
    google_credentials = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    excel_path = "data/CALCULO_DE _PRECIOS-AGUAJE17.xlsx"
    
    print("📋 CONFIGURACIÓN:")
    print(f"Google Sheets ID: {'✅ Configurado' if google_sheets_id else '❌ No configurado'}")
    print(f"Google Credentials: {'✅ Configurado' if google_credentials else '❌ No configurado'}")
    print(f"Excel local: {'✅ Existe' if os.path.exists(excel_path) else '❌ No existe'}")
    
    print("\n" + "="*50 + "\n")
    
    # Probar servicio
    print("🧪 PROBANDO SERVICIO:")
    excel_service = ExcelService()
    
    if excel_service.prices_data:
        products = excel_service.get_available_products()
        print(f"✅ Servicio inicializado correctamente")
        print(f"📦 Productos disponibles: {len(products)}")
        print(f"🏷️ Productos: {products}")
        
        if products:
            first_product = products[0]
            sizes = excel_service.get_available_sizes(first_product)
            print(f"📏 Tallas para {first_product}: {len(sizes)}")
            print(f"📏 Tallas: {sizes}")
            
            if sizes:
                price_data = excel_service.get_price_data(sizes[0], first_product)
                print(f"💰 Precio {first_product} {sizes[0]}: ${price_data['precio_kg']:.2f}/kg")
        
        # Estadísticas
        total_sizes = sum(len(excel_service.get_available_sizes(p)) for p in products)
        print(f"\n📊 ESTADÍSTICAS:")
        print(f"Total productos: {len(products)}")
        print(f"Total tallas: {total_sizes}")
        
    else:
        print("❌ Error: No se pudieron cargar datos de ninguna fuente")
        print("\n🔧 SOLUCIONES:")
        print("1. Configura Google Sheets siguiendo las instrucciones")
        print("2. O asegúrate de que el archivo Excel esté en data/")

if __name__ == "__main__":
    test_data_sources()