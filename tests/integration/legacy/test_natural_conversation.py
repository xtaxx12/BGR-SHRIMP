"""
Test para verificar la conversación natural con GPT
"""
import sys
sys.path.append('.')

from app.services.openai_service import OpenAIService
from app.services.session import SessionManager

def test_natural_conversation():
    """
    Simula una conversación natural completa
    """
    print("🧪 Probando conversación natural con GPT...\n")
    print("="*80)
    
    openai_service = OpenAIService()
    session_manager = SessionManager()
    user_id = "test_user_conversation"
    
    if not openai_service.is_available():
        print("⚠️ OpenAI no está disponible. Configura OPENAI_API_KEY para probar.")
        return
    
    # Conversación de ejemplo
    conversation = [
        "Hola",
        "Necesito precios de HLSO 16/20 y HOSO 30/40",
        "Con glaseo 20%",
        "En español por favor",
    ]
    
    for i, user_message in enumerate(conversation, 1):
        print(f"\n{'='*80}")
        print(f"Turno {i}")
        print(f"{'='*80}\n")
        
        print(f"👤 Usuario: {user_message}")
        
        # Agregar mensaje del usuario al historial
        session_manager.add_to_conversation(user_id, 'user', user_message)
        
        # Obtener historial y datos de sesión
        session = session_manager.get_session(user_id)
        conversation_history = session_manager.get_conversation_history(user_id)
        session_data = session.get('data', {})
        
        # Obtener respuesta de GPT
        gpt_response = openai_service.chat_with_context(
            user_message,
            conversation_history[:-1],  # Excluir el mensaje actual
            session_data
        )
        
        # Mostrar respuesta
        print(f"\n🤖 Bot: {gpt_response['response']}")
        
        if gpt_response.get('action'):
            print(f"   📋 Acción: {gpt_response['action']}")
        
        if gpt_response.get('data'):
            print(f"   📊 Datos: {gpt_response['data']}")
        
        # Agregar respuesta del bot al historial
        session_manager.add_to_conversation(user_id, 'assistant', gpt_response['response'])
        
        # Actualizar datos de sesión si hay
        if gpt_response.get('data'):
            session['data'].update(gpt_response['data'])
    
    print(f"\n{'='*80}")
    print("✅ Conversación completada!")
    print(f"{'='*80}\n")
    
    # Mostrar resumen del historial
    print("📜 Historial de conversación:")
    history = session_manager.get_conversation_history(user_id)
    for msg in history:
        role_emoji = "👤" if msg['role'] == 'user' else "🤖"
        print(f"   {role_emoji} {msg['role']}: {msg['content'][:100]}...")

if __name__ == "__main__":
    test_natural_conversation()
