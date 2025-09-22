#!/usr/bin/env python3
"""
Prueba del sistema de botones interactivos
"""

from app.services.interactive import InteractiveMessageService
import json

def test_interactive_menus():
    interactive = InteractiveMessageService()
    
    print("=== SISTEMA DE BOTONES INTERACTIVOS ===\n")
    
    # 1. Menú principal interactivo
    main_menu = interactive.create_interactive_main_menu()
    print("MENÚ PRINCIPAL INTERACTIVO:")
    print(json.dumps(main_menu, indent=2, ensure_ascii=False))
    print("\n" + "="*60 + "\n")
    
    # 2. Menú de cliente interactivo
    client_menu = interactive.create_interactive_client_menu()
    print("MENÚ CLIENTE INTERACTIVO:")
    print(json.dumps(client_menu, indent=2, ensure_ascii=False))
    print("\n" + "="*60 + "\n")
    
    # 3. Menú de no cliente interactivo
    non_client_menu = interactive.create_interactive_non_client_menu()
    print("MENÚ NO CLIENTE INTERACTIVO:")
    print(json.dumps(non_client_menu, indent=2, ensure_ascii=False))
    print("\n" + "="*60 + "\n")
    
    # 4. Prueba de parseo de respuestas de botones
    print("PRUEBA DE PARSEO DE BOTONES:")
    test_buttons = ["soy_cliente", "no_soy_cliente", "consulta", "precios", "contacto"]
    
    for button_id in test_buttons:
        action, value = interactive.parse_interactive_response(button_id)
        print(f"Botón: {button_id} -> Acción: {action}, Valor: {value}")
    
    print("\n" + "="*60 + "\n")
    
    # 5. Menú de tallas interactivo
    print("MENÚ DE TALLAS INTERACTIVO:")
    try:
        size_menus, sizes = interactive.create_interactive_size_menu()
        print(f"Se crearon {len(size_menus)} menús de tallas")
        print(f"Tallas disponibles: {sizes}")
        
        if size_menus:
            print("Primer menú de tallas:")
            print(json.dumps(size_menus[0], indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error creando menú de tallas: {e}")

if __name__ == "__main__":
    test_interactive_menus()