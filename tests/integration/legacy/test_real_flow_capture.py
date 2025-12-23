"""
Test para verificar que la captura funciona en el flujo real de WhatsApp.
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.session import session_manager

def test_real_flow():
    """Simula el flujo real de WhatsApp con captura."""
    
    print("=" * 80)
    print("🧪 TEST: Flujo Real de Captura en WhatsApp")
    print("=" * 80)
    
    # Usuario real (el que viste en sessions.json)
    real_user = "+593968058769"
    
    # 1. Verificar estado actual
    print("\n1️⃣ Estado actual del usuario:")
    session = session_manager.get_session(real_user)
    print(f"   - Consentimiento: {session.get('consent_for_training')}")
    print(f"   - Timestamp: {session.get('consent_timestamp')}")
    print(f"   - Mensajes en historial: {len(session.get('conversation_history', []))}")
    
    # 2. Simular nueva conversación
    print("\n2️⃣ Simulando nueva conversación...")
    
    # Mensaje del usuario
    user_message = "Necesito precios para HLSO 21/25 CFR Lisboa con 20% glaseo"
    print(f"   👤 Usuario: {user_message}")
    session_manager.add_to_conversation(real_user, 'user', user_message)
    
    # Respuesta del asistente
    assistant_response = "Perfecto, voy a calcular el precio para HLSO 21/25 CFR Lisboa con 20% glaseo..."
    print(f"   🤖 Asistente: {assistant_response}")
    session_manager.add_to_conversation(real_user, 'assistant', assistant_response)
    
    # 3. Verificar que se guardó
    print("\n3️⃣ Verificando que se guardó...")
    session = session_manager.get_session(real_user)
    history = session.get('conversation_history', [])
    print(f"   📝 Mensajes en historial: {len(history)}")
    
    if len(history) >= 2:
        print(f"   ✅ Último mensaje usuario: {history[-2]['content'][:50]}...")
        print(f"   ✅ Última respuesta asistente: {history[-1]['content'][:50]}...")
    
    # 4. Verificar archivos capturados
    print("\n4️⃣ Verificando archivos capturados...")
    from pathlib import Path
    queue_dir = Path("data/etl_queue")
    if queue_dir.exists():
        captured_files = list(queue_dir.glob("*.json"))
        print(f"   📥 Archivos en cola: {len(captured_files)}")
        
        # Mostrar los últimos 2
        if len(captured_files) >= 2:
            import json
            for f in captured_files[-2:]:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    print(f"   - {f.name}: {data['role']} - {data['content'][:40]}...")
    
    # 5. Exportar
    print("\n5️⃣ Exportando datos...")
    import subprocess
    result = subprocess.run(
        ["python", "scripts/export_for_finetune.py", "--min-confidence", "0.5", "--source", "sessions"],
        capture_output=True,
        text=True
    )
    
    # Buscar líneas relevantes en la salida
    for line in result.stdout.split('\n'):
        if 'Pares válidos' in line or 'Train:' in line or 'Valid:' in line or 'Total:' in line:
            print(f"   {line.strip()}")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETADO")
    print("=" * 80)
    print("\n💡 NOTA: Si ves 'Pares válidos: 0', significa que el historial")
    print("   no se está guardando en el flujo real de WhatsApp.")
    print("   Verifica que el bot esté usando el código actualizado.")

if __name__ == "__main__":
    test_real_flow()
