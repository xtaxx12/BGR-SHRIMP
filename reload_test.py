#!/usr/bin/env python3
"""
Test forzando recarga del módulo
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import importlib

def test_with_reload():
    """
    Test forzando recarga del módulo
    """
    print("🔍 Test forzando recarga del módulo...")
    
    # Importar y recargar
    import app.services.utils as utils_module
    importlib.reload(utils_module)
    
    from app.services.utils import parse_ai_analysis_to_query
    
    # Datos de entrada
    ai_analysis = {
        'intent': 'proforma',
        'product': 'HOSO',
        'size': '30/40',
        'glaseo_factor': None,
    }
    
    print(f"📝 Entrada: glaseo_factor = {ai_analysis.get('glaseo_factor')}")
    
    # Llamar función
    result = parse_ai_analysis_to_query(ai_analysis)
    
    print(f"📊 Resultado: glaseo_factor = {result.get('glaseo_factor') if result else 'None'}")
    
    # Verificar código fuente después de reload
    import inspect
    source = inspect.getsource(parse_ai_analysis_to_query)
    
    if '0.7' in source:
        print("🚨 PROBLEMA: Aún hay '0.7' después del reload")
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if '0.7' in line and 'glaseo' in line.lower():
                print(f"   Línea {i+1}: {line.strip()}")
    else:
        print("✅ No hay '0.7' después del reload")
    
    return result

if __name__ == "__main__":
    result = test_with_reload()