"""
Script de prueba para verificar que los mensajes se están capturando correctamente.
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.session import session_manager
from app.services.training_pipeline import get_training_pipeline

def test_message_capture():
    """Prueba la captura de mensajes con consentimiento."""
    
    print("=" * 80)
    print("🧪 TEST: Captura de Mensajes para Entrenamiento")
    print("=" * 80)
    
    # Usuario de prueba
    test_user = "test_user_capture_001"
    
    # 1. Dar consentimiento
    print("\n1️⃣ Otorgando consentimiento...")
    session_manager.set_training_consent(test_user, True)
    consent = session_manager.get_training_consent(test_user)
    print(f"   ✅ Consentimiento: {consent}")
    
    # 2. Simular conversación
    print("\n2️⃣ Simulando conversación...")
    conversation = [
        ("user", "Hola, necesito precios para HLSO 16/20 CFR Lisboa"),
        ("assistant", "Claro, necesito saber el porcentaje de glaseo. ¿Cuál prefieres?"),
        ("user", "20% glaseo"),
        ("assistant", "Perfecto, generando cotización..."),
    ]
    
    for role, content in conversation:
        session_manager.add_to_conversation(test_user, role, content)
        print(f"   📝 {role}: {content[:50]}...")
    
    # 3. Verificar que se capturaron
    print("\n3️⃣ Verificando captura...")
    pipeline = get_training_pipeline()
    
    # Contar archivos en cola
    import os
    from pathlib import Path
    
    queue_dir = Path("data/etl_queue")
    if queue_dir.exists():
        captured_files = list(queue_dir.glob("*.json"))
        print(f"   📥 Archivos capturados: {len(captured_files)}")
        
        if captured_files:
            # Mostrar contenido del primer archivo
            import json
            with open(captured_files[0], 'r', encoding='utf-8') as f:
                sample = json.load(f)
            
            print(f"\n   📄 Ejemplo de archivo capturado:")
            print(f"      - Role: {sample.get('role')}")
            print(f"      - Content: {sample.get('content')[:80]}...")
            print(f"      - Status: {sample.get('status')}")
            print(f"      - Captured at: {sample.get('captured_at')}")
    else:
        print(f"   ⚠️ Directorio de cola no existe: {queue_dir}")
    
    # 4. Estadísticas del pipeline
    print("\n4️⃣ Estadísticas del pipeline:")
    stats = pipeline.get_stats()
    for key, value in stats.items():
        print(f"   - {key}: {value}")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETADO")
    print("=" * 80)

if __name__ == "__main__":
    test_message_capture()
