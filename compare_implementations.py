#!/usr/bin/env python3
"""
Comparar mi implementación con la función real
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.utils import parse_ai_analysis_to_query

def compare_implementations():
    """
    Comparar implementaciones
    """
    print("🔍 Comparando implementaciones...")
    
    # Datos de entrada
    ai_analysis = {
        'intent': 'proforma',
        'product': 'HOSO',
        'size': '30/40',
        'quantity': None,
        'destination': None,
        'glaseo_factor': None,
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
    
    # Llamar a la función real
    print(f"\n🔍 Llamando función REAL parse_ai_analysis_to_query...")
    result_real = parse_ai_analysis_to_query(ai_analysis)
    
    print(f"📊 Resultado REAL:")
    if result_real:
        for key, value in result_real.items():
            if key == 'glaseo_factor':
                print(f"   {key}: {value} ⭐")
            else:
                print(f"   {key}: {value}")
    else:
        print("   None")
    
    # Verificar si hay algún import o inicialización que esté causando el problema
    print(f"\n🔍 Verificando imports...")
    
    # Revisar si hay algún valor por defecto en algún lugar
    import app.services.utils as utils_module
    print(f"   Módulo utils cargado: {utils_module}")
    
    # Revisar si hay alguna variable global
    if hasattr(utils_module, 'DEFAULT_GLASEO'):
        print(f"   DEFAULT_GLASEO encontrado: {utils_module.DEFAULT_GLASEO}")
    else:
        print("   No hay DEFAULT_GLASEO")
    
    return result_real

if __name__ == "__main__":
    result = compare_implementations()
    
    if result and result.get('glaseo_factor') is None:
        print("\n✅ CORRECTO: función real mantiene glaseo_factor como None")
    elif result and result.get('glaseo_factor') is not None:
        print(f"\n❌ ERROR: función real cambió glaseo_factor a {result.get('glaseo_factor')}")
        
        # Investigar más
        print(f"\n🔍 Investigando más...")
        print(f"   Tipo de glaseo_factor: {type(result.get('glaseo_factor'))}")
        print(f"   Valor exacto: {repr(result.get('glaseo_factor'))}")
    else:
        print("\n❌ ERROR: función real retornó None")