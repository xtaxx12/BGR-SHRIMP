#!/usr/bin/env python3
"""
Debug paso a paso de la función parse_ai_analysis_to_query
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_parse_ai_analysis_to_query():
    """
    Reimplementar la función paso a paso para debuggear
    """
    print("🔍 Debuggeando parse_ai_analysis_to_query paso a paso...")
    
    # Datos de entrada
    ai_analysis = {
        'intent': 'proforma',
        'product': 'HOSO',
        'size': '30/40',
        'quantity': None,
        'destination': None,
        'glaseo_factor': None,  # ¡Explícitamente None!
        'glaseo_percentage': None,
        'flete_custom': 0.15,
        'precio_base_custom': None,
        'usar_libras': False,
        'cliente_nombre': None,
        'wants_proforma': True,
        'language': 'es',
        'confidence': 0.95
    }
    
    print(f"📝 Datos de entrada:")
    print(f"   glaseo_factor: {ai_analysis.get('glaseo_factor')}")
    
    # Paso 1: Validar intent
    if not ai_analysis or ai_analysis.get('intent') not in ['pricing', 'proforma']:
        print("❌ Intent inválido")
        return None
    print("✅ Intent válido")
    
    # Paso 2: Extraer información
    product = ai_analysis.get('product')
    size = ai_analysis.get('size')
    quantity = ai_analysis.get('quantity')
    destination = ai_analysis.get('destination')
    glaseo_factor = ai_analysis.get('glaseo_factor')
    glaseo_percentage = ai_analysis.get('glaseo_percentage')
    flete_custom = ai_analysis.get('flete_custom')
    usar_libras = ai_analysis.get('usar_libras', False)
    cliente_nombre = ai_analysis.get('cliente_nombre')
    
    print(f"📊 Valores extraídos:")
    print(f"   product: {product}")
    print(f"   size: {size}")
    print(f"   glaseo_factor: {glaseo_factor} (tipo: {type(glaseo_factor)})")
    print(f"   glaseo_percentage: {glaseo_percentage}")
    
    # Paso 3: Validar size
    if not size:
        print("❌ Size faltante")
        return None
    print("✅ Size válido")
    
    # Paso 4: Lógica inteligente para producto
    if not product and size:
        hoso_exclusive_sizes = ['20/30', '30/40', '40/50', '50/60', '60/70', '70/80']
        if size in hoso_exclusive_sizes:
            product = 'HOSO'
            print(f"🧠 Producto inferido: {product}")
    
    if not product:
        print("❌ Producto faltante")
        return None
    print(f"✅ Producto: {product}")
    
    # Paso 5: Determinar unidad
    unit = 'lb' if usar_libras else 'kg'
    print(f"📏 Unidad: {unit}")
    
    # Paso 6: Procesar flete
    flete_value = None
    flete_solicitado = False
    
    if flete_custom:
        try:
            flete_value = float(flete_custom)
            flete_solicitado = True
            print(f"💰 Flete personalizado: {flete_value}")
        except:
            print("❌ Error procesando flete")
    elif destination:
        flete_solicitado = True
        print(f"🌍 Flete solicitado por destino: {destination}")
    
    # Paso 7: Procesar glaseo (CRÍTICO)
    print(f"\n🔍 PROCESANDO GLASEO:")
    print(f"   glaseo_factor original: {glaseo_factor}")
    
    glaseo_value = None
    if glaseo_factor:
        print("   glaseo_factor es truthy, procesando...")
        try:
            glaseo_num = float(glaseo_factor)
            if glaseo_num > 1:
                glaseo_value = glaseo_num / 100
                print(f"   Convertido de porcentaje: {glaseo_value}")
            else:
                glaseo_value = glaseo_num
                print(f"   Usado como factor: {glaseo_value}")
        except:
            glaseo_value = None
            print("   Error en conversión, asignado None")
    else:
        glaseo_value = None
        print("   glaseo_factor es falsy, asignado None")
    
    print(f"   glaseo_value final: {glaseo_value}")
    
    # Paso 8: Crear query
    print(f"\n🏗️ CREANDO QUERY:")
    query = {}
    
    query['product'] = product
    print(f"   Asignado product: {query['product']}")
    
    query['size'] = size
    print(f"   Asignado size: {query['size']}")
    
    query['quantity'] = quantity
    print(f"   Asignado quantity: {query['quantity']}")
    
    query['destination'] = destination
    print(f"   Asignado destination: {query['destination']}")
    
    query['unit'] = unit
    print(f"   Asignado unit: {query['unit']}")
    
    query['glaseo_factor'] = glaseo_value
    print(f"   Asignado glaseo_factor: {query['glaseo_factor']} ⭐")
    
    query['glaseo_percentage'] = glaseo_percentage
    print(f"   Asignado glaseo_percentage: {query['glaseo_percentage']}")
    
    query['flete_custom'] = flete_value
    print(f"   Asignado flete_custom: {query['flete_custom']}")
    
    query['flete_solicitado'] = flete_solicitado
    print(f"   Asignado flete_solicitado: {query['flete_solicitado']}")
    
    query['usar_libras'] = usar_libras
    print(f"   Asignado usar_libras: {query['usar_libras']}")
    
    query['cliente_nombre'] = cliente_nombre
    print(f"   Asignado cliente_nombre: {query['cliente_nombre']}")
    
    query['custom_calculation'] = True
    print(f"   Asignado custom_calculation: {query['custom_calculation']}")
    
    print(f"\n📊 Query final:")
    for key, value in query.items():
        if key == 'glaseo_factor':
            print(f"   {key}: {value} ⭐")
        else:
            print(f"   {key}: {value}")
    
    return query

if __name__ == "__main__":
    result = debug_parse_ai_analysis_to_query()
    
    if result and result.get('glaseo_factor') is None:
        print("\n✅ CORRECTO: glaseo_factor es None")
    elif result and result.get('glaseo_factor') is not None:
        print(f"\n❌ ERROR: glaseo_factor debería ser None pero es {result.get('glaseo_factor')}")
    else:
        print("\n❌ ERROR: No se pudo generar resultado")