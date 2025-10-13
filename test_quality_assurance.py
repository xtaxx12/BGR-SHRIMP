"""
Tests del sistema de aseguramiento de calidad
"""
import sys
sys.path.append('.')

from app.services.quality_assurance import qa_service

def test_quality_assurance():
    """
    Prueba el sistema de QA con diferentes escenarios
    """
    print("🧪 Probando Sistema de Aseguramiento de Calidad...\n")
    print("="*80)
    
    # Test 1: Producto válido
    print("\n1️⃣ Test: Producto válido")
    is_valid, error = qa_service.validate_product('HLSO')
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else f'❌ INVÁLIDO: {error}'}")
    
    # Test 2: Producto inválido
    print("\n2️⃣ Test: Producto inválido")
    is_valid, error = qa_service.validate_product('CAMARÓN_GIGANTE')
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else f'❌ INVÁLIDO: {error}'}")
    
    # Test 3: Talla válida
    print("\n3️⃣ Test: Talla válida")
    is_valid, error = qa_service.validate_size('16/20')
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else f'❌ INVÁLIDO: {error}'}")
    
    # Test 4: Talla inválida
    print("\n4️⃣ Test: Talla inválida")
    is_valid, error = qa_service.validate_size('99/100')
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else f'❌ INVÁLIDO: {error}'}")
    
    # Test 5: Glaseo válido
    print("\n5️⃣ Test: Glaseo válido (15%)")
    is_valid, error = qa_service.validate_glaseo(15)
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else f'❌ INVÁLIDO: {error}'}")
    
    # Test 6: Glaseo inválido
    print("\n6️⃣ Test: Glaseo inválido (60%)")
    is_valid, error = qa_service.validate_glaseo(60)
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else f'❌ INVÁLIDO: {error}'}")
    
    # Test 7: Precio válido
    print("\n7️⃣ Test: Precio válido (HLSO $8.00/kg)")
    is_valid, error = qa_service.validate_price('HLSO', 8.00)
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else f'❌ INVÁLIDO: {error}'}")
    
    # Test 8: Precio fuera de rango
    print("\n8️⃣ Test: Precio fuera de rango (HLSO $50.00/kg)")
    is_valid, error = qa_service.validate_price('HLSO', 50.00)
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else f'❌ INVÁLIDO: {error}'}")
    
    # Test 9: Validación completa de cotización
    print("\n9️⃣ Test: Validación completa de cotización")
    price_info = {
        'producto': 'HLSO',
        'talla': '16/20',
        'precio_kg': 8.88,
        'factor_glaseo': 0.80,
        'glaseo_percentage': 20,
        'costo_fijo': 0.29,
        'precio_glaseo_kg': 6.87,  # (8.88 - 0.29) * 0.80 = 6.872
        'precio_fob_con_glaseo_kg': 7.16,  # 6.87 + 0.29
        'flete': 0.15,
        'precio_final_kg': 7.31  # 7.16 + 0.15
    }
    
    is_valid, errors = qa_service.validate_price_calculation(price_info)
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else f'❌ INVÁLIDO'}")
    if not is_valid:
        for error in errors:
            print(f"      • {error}")
    
    # Test 10: Validación de múltiples productos
    print("\n🔟 Test: Validación de múltiples productos")
    products_info = [
        {
            'producto': 'HLSO',
            'talla': '16/20',
            'precio_kg': 8.88,
            'factor_glaseo': 0.80,
            'glaseo_percentage': 20,
            'costo_fijo': 0.29,
            'precio_glaseo_kg': 6.87,
            'precio_fob_con_glaseo_kg': 7.16,
            'flete': 0.15,
            'precio_final_kg': 7.31
        },
        {
            'producto': 'HOSO',
            'talla': '30/40',
            'precio_kg': 5.52,
            'factor_glaseo': 0.85,
            'glaseo_percentage': 15,
            'costo_fijo': 0.29,
            'precio_glaseo_kg': 4.45,  # (5.52 - 0.29) * 0.85 = 4.4455
            'precio_fob_con_glaseo_kg': 4.74,  # 4.45 + 0.29
            'flete': 0.15,
            'precio_final_kg': 4.89  # 4.74 + 0.15
        }
    ]
    
    is_valid, report = qa_service.validate_multiple_products(products_info)
    print(f"   Resultado: {'✅ TODOS VÁLIDOS' if is_valid else f'❌ ALGUNOS INVÁLIDOS'}")
    print(f"   Válidos: {report['valid_products']}/{report['total_products']}")
    
    if report['errors']:
        print("\n   Errores encontrados:")
        for error_info in report['errors']:
            print(f"      Producto: {error_info['product']}")
            for error in error_info['errors']:
                print(f"         • {error}")
    
    print("\n" + "="*80)
    print("✅ Tests de QA completados!")
    print("="*80)

if __name__ == "__main__":
    test_quality_assurance()
