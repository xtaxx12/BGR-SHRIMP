#!/usr/bin/env python3
"""
Script de debug para encontrar dónde se asigna el glaseo por defecto
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.utils import parse_ai_analysis_to_query

def debug_glaseo_assignment():
    """
    Debug paso a paso del procesamiento del glaseo
    """
    print("🔍 Debuggeando asignación de glaseo...")
    
    # Simular análisis de IA sin glaseo
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
    
    print(f"📝 Análisis de IA original:")
    for key, value in ai_analysis.items():
        print(f"   {key}: {value}")
    
    print(f"\n🔍 Procesando con parse_ai_analysis_to_query...")
    
    # Extraer valores paso a paso
    glaseo_factor = ai_analysis.get('glaseo_factor')
    print(f"   glaseo_factor extraído: {glaseo_factor} (tipo: {type(glaseo_factor)})")
    
    # Procesar factor de glaseo (copiando la lógica exacta)
    glaseo_value = None
    if glaseo_factor:
        print(f"   glaseo_factor es truthy, procesando...")
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
            print(f"   Error en conversión, asignado None")
    else:
        glaseo_value = None
        print(f"   glaseo_factor es falsy, asignado None")
    
    print(f"   glaseo_value final: {glaseo_value}")
    
    # Llamar a la función real
    result = parse_ai_analysis_to_query(ai_analysis)
    
    print(f"\n📊 Resultado de parse_ai_analysis_to_query:")
    if result:
        for key, value in result.items():
            if key == 'glaseo_factor':
                print(f"   {key}: {value} ⭐ (este es el problema si no es None)")
            else:
                print(f"   {key}: {value}")
    else:
        print("   None")
    
    return result

if __name__ == "__main__":
    result = debug_glaseo_assignment()
    
    if result and result.get('glaseo_factor') is None:
        print("\n✅ CORRECTO: glaseo_factor es None")
    elif result and result.get('glaseo_factor') is not None:
        print(f"\n❌ ERROR: glaseo_factor debería ser None pero es {result.get('glaseo_factor')}")
    else:
        print("\n❌ ERROR: No se pudo generar resultado")