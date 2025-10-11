"""
Test para verificar que la sesión preserva la última cotización
"""
import sys
sys.path.append('.')

from app.services.session import SessionManager

def test_session_preservation():
    """
    Verifica que clear_session preserve idioma y última cotización
    """
    print("🧪 Probando preservación de sesión...\n")
    
    # Crear instancia de SessionManager
    session_manager = SessionManager()
    user_id = "test_user_123"
    
    # 1. Crear sesión y guardar datos
    print("1️⃣ Guardando idioma y cotización...")
    session_manager.set_user_language(user_id, 'es')
    
    test_quote = {
        'producto': 'HOSO',
        'talla': '30/40',
        'precio_kg': 5.50,
        'flete': 0.15,
        'factor_glaseo': 0.80
    }
    session_manager.set_last_quote(user_id, test_quote)
    
    # Verificar que se guardaron
    language = session_manager.get_user_language(user_id)
    quote = session_manager.get_last_quote(user_id)
    
    print(f"   ✅ Idioma guardado: {language}")
    print(f"   ✅ Cotización guardada: {quote['producto']} {quote['talla']}")
    print()
    
    # 2. Limpiar sesión
    print("2️⃣ Limpiando sesión...")
    session_manager.clear_session(user_id)
    print("   ✅ Sesión limpiada")
    print()
    
    # 3. Verificar que se preservaron los datos
    print("3️⃣ Verificando datos preservados...")
    language_after = session_manager.get_user_language(user_id)
    quote_after = session_manager.get_last_quote(user_id)
    
    if language_after == language:
        print(f"   ✅ Idioma preservado: {language_after}")
    else:
        print(f"   ❌ Idioma NO preservado: {language_after} (esperado: {language})")
        return False
    
    if quote_after and quote_after['producto'] == test_quote['producto']:
        print(f"   ✅ Cotización preservada: {quote_after['producto']} {quote_after['talla']}")
    else:
        print(f"   ❌ Cotización NO preservada: {quote_after}")
        return False
    
    print()
    print("✅ Todos los tests pasaron!")
    return True

if __name__ == "__main__":
    success = test_session_preservation()
    exit(0 if success else 1)
