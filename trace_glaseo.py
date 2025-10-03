#!/usr/bin/env python3
"""
Script para trazar exactamente dónde se está asignando el glaseo
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Monkey patch para trazar asignaciones
original_dict_setitem = dict.__setitem__

def traced_setitem(self, key, value):
    if key == 'glaseo_factor' and value == 0.7:
        import traceback
        print(f"🚨 ALERTA: Asignando glaseo_factor = 0.7")
        print("📍 Stack trace:")
        traceback.print_stack()
        print("=" * 50)
    return original_dict_setitem(self, key, value)

# Aplicar el monkey patch
dict.__setitem__ = traced_setitem

from app.services.utils import parse_ai_analysis_to_query

def trace_glaseo_assignment():
    """
    Trazar la asignación del glaseo
    """
    print("🔍 Iniciando trace de glaseo...")
    
    # Simular análisis de IA sin glaseo
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
    
    print(f"📝 Llamando parse_ai_analysis_to_query...")
    result = parse_ai_analysis_to_query(ai_analysis)
    
    print(f"📊 Resultado:")
    if result:
        print(f"   glaseo_factor: {result.get('glaseo_factor')}")
    else:
        print("   None")
    
    return result

if __name__ == "__main__":
    result = trace_glaseo_assignment()
    
    # Restaurar el método original
    dict.__setitem__ = original_dict_setitem