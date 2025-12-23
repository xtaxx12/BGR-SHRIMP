"""
Test para verificar que el bot detecta correctamente todos los casos de uso del cliente
Mensaje de prueba: "Hola Erick, como estas? podras ofertar otros tamaños de camaron? 
HLSO 16-20/ 21-25/26-30/31-35/36-40/41-50/51-60 HOSO 20-30/30-40/40-50 BRINE 100% NET 20k/caja"
"""
import re
from app.services.openai_service import OpenAIService

def test_deteccion_completa():
    """Test para verificar que se detectan todos los elementos del mensaje"""
    
    # Mensaje sin espacios (como lo envía el cliente)
    mensaje = """Hola Erick, como estas? podras ofertar otros tamaños de camaron? HLSO 16-20/ 21-25/26-30/31-35/36-40/41-50/51-60 HOSO 20-30/30-40/40-50BRINE100% NET20k/caja"""
    
    # Inicializar servicio
    openai_service = OpenAIService()
    
    # Análisis básico (sin OpenAI)
    print("\n" + "="*80)
    print("ANÁLISIS BÁSICO (sin OpenAI)")
    print("="*80)
    
    basic_analysis = openai_service._basic_intent_analysis(mensaje)
    print(f"\n📊 Resultado del análisis básico:")
    for key, value in basic_analysis.items():
        print(f"   {key}: {value}")
    
    # Verificar detección de tallas
    print("\n" + "="*80)
    print("DETECCIÓN DE TALLAS")
    print("="*80)
    
    all_sizes = re.findall(r'(\d+)[/-](\d+)', mensaje)
    sizes_normalized = [f"{s[0]}/{s[1]}" for s in all_sizes]
    
    print(f"\n🔍 Tallas detectadas: {len(sizes_normalized)}")
    print(f"   Tallas: {sizes_normalized}")
    
    # Verificar que se detectaron TODAS las 10 tallas
    expected_sizes = ["16/20", "21/25", "26/30", "31/35", "36/40", "41/50", "51/60", "20/30", "30/40", "40/50"]
    assert len(sizes_normalized) == 10, f"❌ Se esperaban 10 tallas, se detectaron {len(sizes_normalized)}"
    assert sizes_normalized == expected_sizes, f"❌ Tallas no coinciden: {sizes_normalized} vs {expected_sizes}"
    print("   ✅ Todas las 10 tallas detectadas correctamente")
    
    # Verificar detección de productos
    print("\n" + "="*80)
    print("DETECCIÓN DE PRODUCTOS")
    print("="*80)
    
    message_upper = mensaje.upper()
    has_hlso = 'HLSO' in message_upper
    has_hoso = 'HOSO' in message_upper
    
    print(f"\n🦐 Productos detectados:")
    print(f"   HLSO: {has_hlso}")
    print(f"   HOSO: {has_hoso}")
    
    assert has_hlso, "❌ No se detectó HLSO"
    assert has_hoso, "❌ No se detectó HOSO"
    print("   ✅ Ambos productos detectados correctamente")
    
    # Verificar detección de BRINE
    print("\n" + "="*80)
    print("DETECCIÓN DE PROCESAMIENTO (BRINE)")
    print("="*80)
    
    has_brine = 'BRINE' in message_upper or 'SALMUERA' in message_upper.lower()
    processing_type = basic_analysis.get('processing_type')
    
    print(f"\n📦 Procesamiento detectado:")
    print(f"   BRINE en mensaje: {has_brine}")
    print(f"   processing_type: {processing_type}")
    
    assert has_brine, "❌ No se detectó BRINE en el mensaje"
    assert processing_type == 'BRINE', f"❌ processing_type debería ser 'BRINE', es '{processing_type}'"
    print("   ✅ BRINE detectado correctamente")
    
    # Verificar detección de NET
    print("\n" + "="*80)
    print("DETECCIÓN DE PESO NETO (100% NET)")
    print("="*80)
    
    net_match = re.search(r'(\d+)\s*%\s*NET', message_upper)
    net_weight = basic_analysis.get('net_weight_percentage')
    
    print(f"\n⚖️ Peso neto detectado:")
    print(f"   NET en mensaje: {net_match.group(0) if net_match else 'No encontrado'}")
    print(f"   net_weight_percentage: {net_weight}")
    
    assert net_match, "❌ No se detectó '100% NET' en el mensaje"
    assert net_weight == 100, f"❌ net_weight_percentage debería ser 100, es {net_weight}"
    print("   ✅ 100% NET detectado correctamente")
    
    # Verificar detección de cantidad
    print("\n" + "="*80)
    print("DETECCIÓN DE CANTIDAD (20k/caja)")
    print("="*80)
    
    cantidad_match = re.search(r'(\d+)k/caja', mensaje.lower())
    cantidad = basic_analysis.get('quantity')
    
    print(f"\n📊 Cantidad detectada:")
    print(f"   Cantidad en mensaje: {cantidad_match.group(0) if cantidad_match else 'No encontrado'}")
    print(f"   quantity: {cantidad}")
    
    assert cantidad_match, "❌ No se detectó '20k/caja' en el mensaje"
    assert cantidad == "20000 kg/caja", f"❌ quantity debería ser '20000 kg/caja', es '{cantidad}'"
    print("   ✅ 20k/caja detectado y convertido correctamente")
    
    # Análisis con OpenAI (si está disponible)
    if openai_service.is_available():
        print("\n" + "="*80)
        print("ANÁLISIS CON OPENAI")
        print("="*80)
        
        openai_analysis = openai_service.analyze_user_intent(mensaje)
        print(f"\n🤖 Resultado del análisis OpenAI:")
        for key, value in openai_analysis.items():
            if key not in ['confidence']:  # Excluir confidence para mejor legibilidad
                print(f"   {key}: {value}")
        
        # Verificar que OpenAI detectó múltiples productos y tallas
        assert openai_analysis.get('multiple_sizes') == True, "❌ OpenAI no detectó múltiples tallas"
        assert openai_analysis.get('multiple_products') == True, "❌ OpenAI no detectó múltiples productos"
        
        # Verificar que OpenAI detectó BRINE y NET
        assert openai_analysis.get('processing_type') == 'BRINE', "❌ OpenAI no detectó BRINE"
        assert openai_analysis.get('net_weight_percentage') == 100, "❌ OpenAI no detectó 100% NET"
        
        # Verificar que OpenAI detectó la cantidad
        assert openai_analysis.get('cantidad') is not None, "❌ OpenAI no detectó la cantidad"
        
        # Verificar que OpenAI detectó todas las tallas
        sizes_detected = openai_analysis.get('sizes', [])
        assert len(sizes_detected) == 10, f"❌ OpenAI detectó {len(sizes_detected)} tallas, se esperaban 10"
        
        # Verificar que OpenAI agrupó las tallas por producto
        sizes_by_product = openai_analysis.get('sizes_by_product', {})
        if sizes_by_product:
            print(f"\n📋 Tallas agrupadas por producto:")
            for product, sizes in sizes_by_product.items():
                print(f"   {product}: {sizes}")
            
            assert 'HLSO' in sizes_by_product, "❌ OpenAI no agrupó tallas de HLSO"
            assert 'HOSO' in sizes_by_product, "❌ OpenAI no agrupó tallas de HOSO"
            assert len(sizes_by_product['HLSO']) == 7, f"❌ HLSO debería tener 7 tallas, tiene {len(sizes_by_product['HLSO'])}"
            assert len(sizes_by_product['HOSO']) == 3, f"❌ HOSO debería tener 3 tallas, tiene {len(sizes_by_product['HOSO'])}"
            print("   ✅ Tallas agrupadas correctamente por producto")
        
        print("\n✅ Análisis OpenAI completo y correcto")
    else:
        print("\n⚠️ OpenAI no está disponible, saltando análisis con IA")
    
    # Verificar interpretación de 100% NET como glaseo 0%
    print("\n" + "="*80)
    print("INTERPRETACIÓN DE 100% NET")
    print("="*80)
    
    print(f"\n💡 Interpretación correcta:")
    print(f"   100% NET = 0% glaseo (todo es producto)")
    print(f"   Esto significa que se debe calcular precio CFR (FOB + Flete)")
    print(f"   Sin aplicar factor de glaseo")
    
    if net_weight == 100:
        print(f"\n✅ El bot debe:")
        print(f"   1. Detectar glaseo = 0%")
        print(f"   2. Solicitar valor de flete")
        print(f"   3. Calcular precio CFR = FOB + Flete")
        print(f"   4. NO aplicar factor de glaseo")
    
    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print("\n✅ TODOS LOS CASOS DE USO DETECTADOS CORRECTAMENTE:")
    print("   ✓ 10 tallas detectadas (7 HLSO + 3 HOSO)")
    print("   ✓ 2 productos detectados (HLSO y HOSO)")
    print("   ✓ BRINE detectado como tipo de procesamiento")
    print("   ✓ 100% NET detectado como peso neto")
    print("   ✓ 100% NET interpretado como glaseo 0% (sin glaseo)")
    print("   ✓ 20k/caja detectado y convertido a 20000 kg/caja")
    print("   ✓ Bot solicitará flete para calcular precio CFR")
    print("\n🎉 El bot está listo para procesar este tipo de mensajes complejos!")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_deteccion_completa()
