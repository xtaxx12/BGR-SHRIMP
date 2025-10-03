#!/usr/bin/env python3
"""
Test importando directamente la función
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import directo
from app.services.utils import parse_ai_analysis_to_query

def test_direct_import():
    """
    Test con import directo
    """
    print("🔍 Test con import directo...")
    
    # Datos de entrada
    ai_analysis = {
        'intent': 'proforma',
        'product': 'HOSO',
        'size': '30/40',
        'glaseo_factor': None,  # Explícitamente None
    }
    
    print(f"📝 Entrada: glaseo_factor = {ai_analysis.get('glaseo_factor')}")
    
    # Llamar función
    result = parse_ai_analysis_to_query(ai_analysis)
    
    print(f"📊 Resultado: glaseo_factor = {result.get('glaseo_factor') if result else 'None'}")
    
    # Verificar si el problema está en el import
    import inspect
    source = inspect.getsource(parse_ai_analysis_to_query)
    
    # Buscar si hay algún valor por defecto hardcodeado
    if '0.7' in source:
        print("🚨 ENCONTRADO: La función contiene '0.7' en su código fuente")
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if '0.7' in line:
                print(f"   Línea {i+1}: {line.strip()}")
    else:
        print("✅ No se encontró '0.7' en el código fuente de la función")
    
    return result

if __name__ == "__main__":
    result = test_direct_import()