#!/usr/bin/env python3
"""
Nueva implementación de parse_ai_analysis_to_query para probar
"""

from typing import Dict, Optional

def parse_ai_analysis_to_query_fixed(ai_analysis: Dict) -> Optional[Dict]:
    """
    Versión corregida que NO usa valores por defecto para glaseo
    """
    if not ai_analysis or ai_analysis.get('intent') not in ['pricing', 'proforma']:
        return None
    
    # Extraer información del análisis de IA
    product = ai_analysis.get('product')
    size = ai_analysis.get('size')
    quantity = ai_analysis.get('quantity')
    destination = ai_analysis.get('destination')
    glaseo_factor = ai_analysis.get('glaseo_factor')
    glaseo_percentage = ai_analysis.get('glaseo_percentage')
    flete_custom = ai_analysis.get('flete_custom')
    usar_libras = ai_analysis.get('usar_libras', False)
    cliente_nombre = ai_analysis.get('cliente_nombre')
    
    # Validar que tengamos producto y talla
    if not size:
        return None
    
    # Lógica inteligente: Si no hay producto pero la talla es exclusiva de HOSO, asumir HOSO
    if not product and size:
        hoso_exclusive_sizes = ['20/30', '30/40', '40/50', '50/60', '60/70', '70/80']
        if size in hoso_exclusive_sizes:
            product = 'HOSO'
    
    if not product:
        return None
    
    # Determinar unidad base según destino
    unit = 'lb' if usar_libras else 'kg'
    
    # Procesar flete personalizado del usuario
    flete_value = None
    flete_solicitado = False
    
    if flete_custom:
        try:
            flete_value = float(flete_custom)
            flete_solicitado = True
        except:
            pass
    elif destination:
        flete_solicitado = True
    
    # Procesar factor de glaseo - CRÍTICO: NO USAR VALOR POR DEFECTO
    glaseo_value = None
    if glaseo_factor:
        try:
            glaseo_num = float(glaseo_factor)
            if glaseo_num > 1:
                glaseo_value = glaseo_num / 100
            else:
                glaseo_value = glaseo_num
        except:
            glaseo_value = None  # NUNCA usar valor por defecto
    else:
        glaseo_value = None  # NUNCA usar valor por defecto
    
    # Crear consulta estructurada
    query = {
        'product': product,
        'size': size,
        'quantity': quantity,
        'destination': destination,
        'unit': unit,
        'glaseo_factor': glaseo_value,  # Debe ser None si no se especifica
        'glaseo_percentage': glaseo_percentage,
        'flete_custom': flete_value,
        'flete_solicitado': flete_solicitado,
        'usar_libras': usar_libras,
        'cliente_nombre': cliente_nombre,
        'custom_calculation': True
    }
    
    return query

def test_fixed_function():
    """
    Probar la función corregida
    """
    print("🧪 Probando función corregida...")
    
    ai_analysis = {
        'intent': 'proforma',
        'product': 'HOSO',
        'size': '30/40',
        'quantity': None,
        'destination': None,
        'glaseo_factor': None,  # Explícitamente None
        'glaseo_percentage': None,
        'flete_custom': 0.15,
        'precio_base_custom': None,
        'usar_libras': False,
        'cliente_nombre': None,
        'wants_proforma': True,
        'language': 'es',
        'confidence': 0.95
    }
    
    print(f"📝 Entrada: glaseo_factor = {ai_analysis.get('glaseo_factor')}")
    
    result = parse_ai_analysis_to_query_fixed(ai_analysis)
    
    print(f"📊 Resultado: glaseo_factor = {result.get('glaseo_factor') if result else 'None'}")
    
    if result and result.get('glaseo_factor') is None:
        print("✅ CORRECTO: La función corregida mantiene glaseo_factor como None")
        return True
    else:
        print(f"❌ ERROR: glaseo_factor = {result.get('glaseo_factor') if result else 'None'}")
        return False

if __name__ == "__main__":
    success = test_fixed_function()
    
    if success:
        print("\n🎉 La función corregida funciona correctamente")
        print("💡 El problema está en el archivo utils.py original")
    else:
        print("\n❌ Hay un problema con la lógica")