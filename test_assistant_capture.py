"""
Test para verificar que se capturan las respuestas del asistente.
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.session import session_manager

def test_assistant_responses():
    """Verifica que se capturan respuestas del asistente."""
    
    print("=" * 80)
    print("🧪 TEST: Captura de Respuestas del Asistente")
    print("=" * 80)
    
    # Usuario de prueba
    test_user = "test_assistant_001"
    
    # 1. Dar consentimiento
    print("\n1️⃣ Otorgando consentimiento...")
    session_manager.set_training_consent(test_user, True)
    
    # 2. Simular conversación completa
    print("\n2️⃣ Simulando conversación con respuestas del asistente...")
    
    # Usuario pregunta
    user_msg = "Necesito precios para HLSO 16/20 CFR Lisboa con 20% glaseo"
    session_manager.add_to_conversation(test_user, 'user', user_msg)
    print(f"   👤 Usuario: {user_msg}")
    
    # Asistente responde
    assistant_msg = "✅ Cotización consolidada generada con flete $0.20 - 7 productos 🚢"
    session_manager.add_to_conversation(test_user, 'assistant', assistant_msg)
    print(f"   🤖 Asistente: {assistant_msg}")
    
    # 3. Verificar historial
    print("\n3️⃣ Verificando historial...")
    session = session_manager.get_session(test_user)
    history = session.get('conversation_history', [])
    
    print(f"   📝 Total mensajes: {len(history)}")
    
    user_count = sum(1 for m in history if m['role'] == 'user')
    assistant_count = sum(1 for m in history if m['role'] == 'assistant')
    
    print(f"   👤 Mensajes usuario: {user_count}")
    print(f"   🤖 Mensajes asistente: {assistant_count}")
    
    # 4. Verificar archivos capturados
    print("\n4️⃣ Verificando archivos capturados...")
    from pathlib import Path
    import json
    
    queue_dir = Path("data/etl_queue")
    if queue_dir.exists():
        captured_files = list(queue_dir.glob("*.json"))
        print(f"   📥 Total archivos: {len(captured_files)}")
        
        # Contar por rol
        user_files = 0
        assistant_files = 0
        
        for f in captured_files:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if data['role'] == 'user':
                    user_files += 1
                elif data['role'] == 'assistant':
                    assistant_files += 1
        
        print(f"   👤 Archivos usuario: {user_files}")
        print(f"   🤖 Archivos asistente: {assistant_files}")
        
        # Mostrar último archivo de asistente
        assistant_file = [f for f in captured_files if 'assistant' in open(f, 'r', encoding='utf-8').read()]
        if assistant_file:
            with open(assistant_file[-1], 'r', encoding='utf-8') as file:
                data = json.load(file)
                print(f"\n   📄 Último mensaje asistente capturado:")
                print(f"      - Content: {data['content'][:60]}...")
                print(f"      - Status: {data['status']}")
    
    # 5. Resultado
    print("\n" + "=" * 80)
    if assistant_count > 0:
        print("✅ TEST EXITOSO: Se están capturando respuestas del asistente")
    else:
        print("❌ TEST FALLIDO: No se capturaron respuestas del asistente")
    print("=" * 80)

if __name__ == "__main__":
    test_assistant_responses()
