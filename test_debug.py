#!/usr/bin/env python3
"""
Script para debuggear el problema del bot
"""

from app.services.interactive import InteractiveMessageService
from app.services.session import session_manager

def test_flow():
    interactive = InteractiveMessageService()
    
    print("=== PRUEBA DE FLUJO CORREGIDO ===\n")
    
    # Simular usuario
    user_id = "test_user"
    
    # 1. Estado inicial - comando precios
    print("1. Usuario escribe 'precios' desde estado inicial")
    session = session_manager.get_session(user_id)
    print(f"Estado actual: {session['state']}")
    
    # Simular que está en waiting_for_size_selection
    session_manager.set_session_state(user_id, 'waiting_for_size_selection', {
        'available_sizes': ['16/20', '21/25', '26/30']
    })
    
    print("2. Usuario está en waiting_for_size_selection")
    session = session_manager.get_session(user_id)
    print(f"Estado actual: {session['state']}")
    print(f"Datos: {session['data']}")
    
    # 3. Probar mensaje de tallas
    size_msg, sizes = interactive.create_size_selection_message()
    print(f"\n3. Mensaje de tallas:")
    print(size_msg)
    print(f"Tallas disponibles: {sizes}")
    
    # 4. Limpiar sesión
    session_manager.clear_session(user_id)
    print(f"\n4. Sesión limpiada")

if __name__ == "__main__":
    test_flow()