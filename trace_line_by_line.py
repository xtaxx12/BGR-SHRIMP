#!/usr/bin/env python3
"""
Trace línea por línea de la función parse_ai_analysis_to_query
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def trace_parse_ai_analysis_to_query():
    """
    Reimplementar la función con traces
    """
    print("🔍 Trace línea por línea...")
    
    # Datos de entrada
    ai_analysis = {
        'intent': 'proforma',
        'product': 'HOSO',
        'size': '30/40',
        'glaseo_factor': None,
    }
    
    print(f"📝 ai_analysis['glaseo_factor']: {ai_analysis.get('glaseo_factor')}")
    
    # Línea por línea
    if not ai_analysis or ai_analysis.get('intent') not in ['pricing', 'proforma']:
        print("❌ Intent check failed")
        return None
    print("✅ Intent check passed")
    
    # Extraer información
    glaseo_factor = ai_analysis.get('glaseo_factor')
    print(f"📊 glaseo_factor extraído: {glaseo_factor}")
    
    # Validaciones
    size = ai_analysis.get('size')
    if not size:
        print("❌ Size check failed")
        return None
    print(f"✅ Size check passed: {size}")
    
    product = ai_analysis.get('product')
    if not product:
        print("❌ Product check failed")
        return None
    print(f"✅ Product check passed: {product}")
    
    # Procesar glaseo
    print(f"\n🔍 PROCESANDO GLASEO:")
    print(f"   glaseo_factor antes del if: {glaseo_factor}")
    
    glaseo_value = None
    print(f"   glaseo_value inicializado: {glaseo_value}")
    
    if glaseo_factor:
        print("   Entrando en if glaseo_factor (truthy)")
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
            print("   Exception: asignado None")
    else:
        glaseo_value = None
        print("   Else: asignado None")
    
    print(f"   glaseo_value final: {glaseo_value}")
    
    # Crear query
    print(f"\n🏗️ CREANDO QUERY:")
    query = {}
    
    query['product'] = product
    query['size'] = size
    query['glaseo_factor'] = glaseo_value
    
    print(f"   query['glaseo_factor'] asignado: {query['glaseo_factor']}")
    
    # Verificar si algo cambió el valor
    if query['glaseo_factor'] != glaseo_value:
        print(f"🚨 ALERTA: query['glaseo_factor'] cambió de {glaseo_value} a {query['glaseo_factor']}")
    else:
        print(f"✅ query['glaseo_factor'] mantiene el valor: {query['glaseo_factor']}")
    
    return query

if __name__ == "__main__":
    result = trace_parse_ai_analysis_to_query()
    
    if result:
        print(f"\n📊 Resultado final:")
        print(f"   glaseo_factor: {result.get('glaseo_factor')}")
        
        if result.get('glaseo_factor') is None:
            print("✅ CORRECTO: glaseo_factor es None")
        else:
            print(f"❌ ERROR: glaseo_factor debería ser None pero es {result.get('glaseo_factor')}")
    else:
        print("❌ No se pudo generar resultado")