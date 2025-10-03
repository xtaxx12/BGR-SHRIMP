#!/usr/bin/env python3
"""
Script de prueba para verificar que el bot pida glaseo cuando no se especifica
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.openai_service import OpenAIService
from app.services.utils import parse_ai_analysis_to_query
from app.services.pricing import PricingService

def test_glaseo_requirement():
    """
    Prueba que el bot pida glaseo cuando no se especifica
    """
    print("🧪 Probando requerimiento de glaseo...")
    
    # Simular mensaje del usuario sin glaseo
    user_message = "Cotizar un Contenedor de 30/40 con 0.15 de flete"
    
    # Crear servicios
    openai_service = OpenAIService()
    pricing_service = PricingService()
    
    # Analizar mensaje (simulando análisis básico)
    ai_analysis = {
        'intent': 'proforma',
        'product': 'HOSO',  # 30/40 es exclusivo de HOSO
        'size': '30/40',
        'quantity': None,
        'destination': None,
        'glaseo_factor': None,  # ¡No especificado!
        'flete_custom': 0.15,
        'precio_base_custom': None,
        'usar_libras': False,
        'cliente_nombre': None,
        'wants_proforma': True,
        'language': 'es',
        'confidence': 0.95
    }
    
    print(f"📝 Mensaje del usuario: {user_message}")
    print(f"🤖 Análisis de IA: {ai_analysis}")
    
    # Convertir análisis a consulta
    ai_query = parse_ai_analysis_to_query(ai_analysis)
    print(f"🔍 Consulta generada: {ai_query}")
    
    if ai_query:
        # Intentar obtener precio
        price_info = pricing_service.get_shrimp_price(ai_query)
        print(f"💰 Resultado de precio: {price_info}")
        
        if price_info is None:
            print("✅ CORRECTO: El sistema no calculó precio porque falta glaseo")
            
            # Verificar que glaseo_factor es None
            glaseo_factor = ai_query.get('glaseo_factor')
            if glaseo_factor is None:
                print("✅ CORRECTO: glaseo_factor es None, el bot debería pedir glaseo")
                return True
            else:
                print(f"❌ ERROR: glaseo_factor no es None: {glaseo_factor}")
                return False
        else:
            print("❌ ERROR: El sistema calculó precio sin glaseo especificado")
            return False
    else:
        print("❌ ERROR: No se pudo generar consulta")
        return False

def test_glaseo_specified():
    """
    Prueba que el bot funcione cuando SÍ se especifica glaseo
    """
    print("\n🧪 Probando con glaseo especificado...")
    
    # Simular mensaje del usuario CON glaseo
    user_message = "Cotizar un Contenedor de 30/40 con glaseo 20% y 0.15 de flete"
    
    # Crear servicios
    openai_service = OpenAIService()
    pricing_service = PricingService()
    
    # Analizar mensaje (simulando análisis básico)
    ai_analysis = {
        'intent': 'proforma',
        'product': 'HOSO',  # 30/40 es exclusivo de HOSO
        'size': '30/40',
        'quantity': None,
        'destination': None,
        'glaseo_factor': 0.80,  # ¡Especificado! 20% = 0.80
        'flete_custom': 0.15,
        'precio_base_custom': None,
        'usar_libras': False,
        'cliente_nombre': None,
        'wants_proforma': True,
        'language': 'es',
        'confidence': 0.95
    }
    
    print(f"📝 Mensaje del usuario: {user_message}")
    print(f"🤖 Análisis de IA: {ai_analysis}")
    
    # Convertir análisis a consulta
    ai_query = parse_ai_analysis_to_query(ai_analysis)
    print(f"🔍 Consulta generada: {ai_query}")
    
    if ai_query:
        # Intentar obtener precio
        price_info = pricing_service.get_shrimp_price(ai_query)
        print(f"💰 Resultado de precio: {price_info}")
        
        if price_info is not None:
            print("✅ CORRECTO: El sistema calculó precio con glaseo especificado")
            return True
        else:
            print("❌ ERROR: El sistema no pudo calcular precio aunque glaseo está especificado")
            return False
    else:
        print("❌ ERROR: No se pudo generar consulta")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de requerimiento de glaseo...\n")
    
    # Prueba 1: Sin glaseo (debería fallar y pedir glaseo)
    test1_passed = test_glaseo_requirement()
    
    # Prueba 2: Con glaseo (debería funcionar)
    test2_passed = test_glaseo_specified()
    
    print(f"\n📊 Resultados:")
    print(f"   Prueba 1 (sin glaseo): {'✅ PASÓ' if test1_passed else '❌ FALLÓ'}")
    print(f"   Prueba 2 (con glaseo): {'✅ PASÓ' if test2_passed else '❌ FALLÓ'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ¡Todas las pruebas pasaron! El bot ahora pedirá glaseo cuando no se especifique.")
    else:
        print("\n⚠️ Algunas pruebas fallaron. Revisar la implementación.")