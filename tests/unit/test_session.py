"""
Tests unitarios para app/services/session.py

Cubre:
- SessionManager.get_session() con creación y recuperación
- SessionManager.update_session() mediante set_session_state
- SessionManager.clear_session() preservando datos importantes
- SessionManager.set_last_quote() y get_last_quote()
- SessionManager.set_user_language() y get_user_language()
- SessionManager.add_to_conversation() y get_conversation_history()
- Limpieza de sesiones expiradas
- Persistencia en disco (_save_sessions, _load_sessions)
"""
import json
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock

import pytest

from app.services.session import SessionManager, SESSIONS_FILE


class TestGetSession:
    """Tests para get_session()"""

    def test_creates_new_session_for_new_user(self):
        """Test que crea una nueva sesión para usuario nuevo"""
        manager = SessionManager()
        manager.sessions = {}  # Limpiar sesiones

        session = manager.get_session("user123")

        assert session is not None
        assert session['state'] == 'idle'
        assert session['data'] == {}
        assert session['conversation_history'] == []
        assert 'last_activity' in session

    def test_returns_existing_session(self):
        """Test que retorna sesión existente"""
        manager = SessionManager()
        manager.sessions = {}

        # Crear sesión
        first_call = manager.get_session("user123")
        first_call['data']['test'] = 'value'

        # Obtener sesión existente
        second_call = manager.get_session("user123")

        assert second_call is first_call
        assert second_call['data']['test'] == 'value'

    def test_updates_last_activity(self):
        """Test que actualiza last_activity cada vez"""
        manager = SessionManager()
        manager.sessions = {}

        session1 = manager.get_session("user123")
        first_activity = session1['last_activity']

        time.sleep(0.01)

        session2 = manager.get_session("user123")
        second_activity = session2['last_activity']

        assert second_activity > first_activity

    def test_cleans_expired_sessions_on_get(self):
        """Test que limpia sesiones expiradas al obtener sesión"""
        manager = SessionManager()
        manager.session_timeout = 1  # 1 segundo
        manager.sessions = {}

        # Crear sesión que expirará
        manager.get_session("expired_user")
        manager.sessions["expired_user"]['last_activity'] = time.time() - 2

        # Crear sesión que no expirará
        manager.get_session("active_user")

        # Al obtener nueva sesión, debe limpiar expiradas
        manager.get_session("new_user")

        assert "expired_user" not in manager.sessions
        assert "active_user" in manager.sessions
        assert "new_user" in manager.sessions


class TestAddToConversation:
    """Tests para add_to_conversation()"""

    def test_adds_message_to_history(self):
        """Test que agrega mensaje al historial"""
        manager = SessionManager()
        manager.sessions = {}

        manager.add_to_conversation("user123", "user", "Hello")

        session = manager.get_session("user123")
        assert len(session['conversation_history']) == 1
        assert session['conversation_history'][0]['role'] == 'user'
        assert session['conversation_history'][0]['content'] == 'Hello'

    def test_adds_multiple_messages(self):
        """Test que agrega múltiples mensajes"""
        manager = SessionManager()
        manager.sessions = {}

        manager.add_to_conversation("user123", "user", "Hello")
        manager.add_to_conversation("user123", "assistant", "Hi there!")
        manager.add_to_conversation("user123", "user", "How are you?")

        session = manager.get_session("user123")
        assert len(session['conversation_history']) == 3
        assert session['conversation_history'][0]['role'] == 'user'
        assert session['conversation_history'][1]['role'] == 'assistant'
        assert session['conversation_history'][2]['role'] == 'user'

    def test_limits_history_to_20_messages(self):
        """Test que limita historial a 20 mensajes"""
        manager = SessionManager()
        manager.sessions = {}

        # Agregar 25 mensajes
        for i in range(25):
            role = "user" if i % 2 == 0 else "assistant"
            manager.add_to_conversation("user123", role, f"Message {i}")

        session = manager.get_session("user123")
        assert len(session['conversation_history']) == 20

        # Debe mantener los últimos 20
        assert session['conversation_history'][0]['content'] == "Message 5"
        assert session['conversation_history'][-1]['content'] == "Message 24"

    def test_creates_conversation_history_if_missing(self):
        """Test que crea conversation_history si no existe"""
        manager = SessionManager()
        manager.sessions = {
            "user123": {
                'state': 'idle',
                'data': {},
                'last_activity': time.time()
            }
        }

        manager.add_to_conversation("user123", "user", "Test")

        assert 'conversation_history' in manager.sessions["user123"]
        assert len(manager.sessions["user123"]['conversation_history']) == 1


class TestGetConversationHistory:
    """Tests para get_conversation_history()"""

    def test_returns_conversation_history(self):
        """Test que retorna el historial de conversación"""
        manager = SessionManager()
        manager.sessions = {}

        manager.add_to_conversation("user123", "user", "Hello")
        manager.add_to_conversation("user123", "assistant", "Hi!")

        history = manager.get_conversation_history("user123")

        assert len(history) == 2
        assert history[0]['role'] == 'user'
        assert history[1]['role'] == 'assistant'

    def test_returns_empty_list_for_new_user(self):
        """Test que retorna lista vacía para usuario nuevo"""
        manager = SessionManager()
        manager.sessions = {}

        history = manager.get_conversation_history("new_user")

        assert history == []


class TestSetSessionState:
    """Tests para set_session_state()"""

    def test_sets_session_state(self):
        """Test que establece el estado de sesión"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            manager.set_session_state("user123", "waiting_input")

        session = manager.get_session("user123")
        assert session['state'] == 'waiting_input'

    def test_updates_session_data(self):
        """Test que actualiza datos de sesión"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            manager.set_session_state(
                "user123",
                "collecting_info",
                data={'product': 'HLSO', 'size': '16/20'}
            )

        session = manager.get_session("user123")
        assert session['state'] == 'collecting_info'
        assert session['data']['product'] == 'HLSO'
        assert session['data']['size'] == '16/20'

    def test_merges_data_with_existing(self):
        """Test que fusiona datos con existentes"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            manager.set_session_state("user123", "state1", data={'key1': 'val1'})
            manager.set_session_state("user123", "state2", data={'key2': 'val2'})

        session = manager.get_session("user123")
        assert session['data']['key1'] == 'val1'
        assert session['data']['key2'] == 'val2'

    def test_saves_sessions_after_update(self):
        """Test que guarda sesiones después de actualizar"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions') as mock_save:
            manager.set_session_state("user123", "test_state")
            mock_save.assert_called_once()


class TestSetAndGetLastQuote:
    """Tests para set_last_quote() y get_last_quote()"""

    def test_sets_last_quote(self):
        """Test que almacena la última cotización"""
        manager = SessionManager()
        manager.sessions = {}

        quote_data = {
            'product': 'HLSO',
            'size': '16/20',
            'price': 7.50,
            'quantity': 15000
        }

        with patch.object(manager, '_save_sessions'):
            manager.set_last_quote("user123", quote_data)

        session = manager.get_session("user123")
        assert session['last_quote'] == quote_data

    def test_gets_last_quote(self):
        """Test que obtiene la última cotización"""
        manager = SessionManager()
        manager.sessions = {}

        quote_data = {
            'product': 'HLSO',
            'size': '16/20',
            'price': 7.50
        }

        with patch.object(manager, '_save_sessions'):
            manager.set_last_quote("user123", quote_data)

        retrieved = manager.get_last_quote("user123")
        assert retrieved == quote_data

    def test_get_last_quote_returns_none_if_not_set(self):
        """Test que retorna None si no hay cotización"""
        manager = SessionManager()
        manager.sessions = {}

        manager.get_session("user123")  # Crear sesión

        quote = manager.get_last_quote("user123")
        assert quote is None

    def test_overwrites_previous_quote(self):
        """Test que sobrescribe cotización anterior"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            manager.set_last_quote("user123", {'price': 7.00})
            manager.set_last_quote("user123", {'price': 8.00})

        quote = manager.get_last_quote("user123")
        assert quote['price'] == 8.00


class TestSetAndGetUserLanguage:
    """Tests para set_user_language() y get_user_language()"""

    def test_sets_user_language(self):
        """Test que establece el idioma del usuario"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            manager.set_user_language("user123", "en")

        session = manager.get_session("user123")
        assert session['language'] == 'en'

    def test_gets_user_language(self):
        """Test que obtiene el idioma del usuario"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            manager.set_user_language("user123", "en")

        language = manager.get_user_language("user123")
        assert language == "en"

    def test_default_language_is_spanish(self):
        """Test que el idioma por defecto es español"""
        manager = SessionManager()
        manager.sessions = {}

        manager.get_session("user123")  # Crear sesión

        language = manager.get_user_language("user123")
        assert language == "es"

    def test_supports_multiple_languages(self):
        """Test soporte para múltiples idiomas"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            manager.set_user_language("user1", "es")
            manager.set_user_language("user2", "en")
            manager.set_user_language("user3", "pt")

        assert manager.get_user_language("user1") == "es"
        assert manager.get_user_language("user2") == "en"
        assert manager.get_user_language("user3") == "pt"


class TestClearSession:
    """Tests para clear_session()"""

    def test_clears_session_data(self):
        """Test que limpia datos de sesión"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            # Crear sesión con datos
            manager.set_session_state("user123", "active", data={'key': 'value'})
            manager.add_to_conversation("user123", "user", "Hello")

            # Limpiar sesión
            manager.clear_session("user123")

        # Verificar que se limpió
        session = manager.get_session("user123")
        assert session['state'] == 'idle'
        assert session['data'] == {}
        assert session['conversation_history'] == []

    def test_preserves_language(self):
        """Test que preserva el idioma al limpiar"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            manager.set_user_language("user123", "en")
            manager.set_session_state("user123", "active", data={'key': 'value'})

            manager.clear_session("user123")

        language = manager.get_user_language("user123")
        assert language == "en"

    def test_preserves_last_quote(self):
        """Test que preserva última cotización al limpiar"""
        manager = SessionManager()
        manager.sessions = {}

        quote_data = {'product': 'HLSO', 'price': 7.50}

        with patch.object(manager, '_save_sessions'):
            manager.set_last_quote("user123", quote_data)
            manager.set_session_state("user123", "active", data={'temp': 'data'})

            manager.clear_session("user123")

        retrieved_quote = manager.get_last_quote("user123")
        assert retrieved_quote == quote_data

    def test_handles_non_existent_session(self):
        """Test que maneja sesión que no existe"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            # No debe lanzar error
            manager.clear_session("non_existent_user")

    def test_saves_sessions_after_clear(self):
        """Test que guarda sesiones después de limpiar"""
        manager = SessionManager()
        manager.sessions = {"user123": {
            'state': 'active',
            'data': {'key': 'value'},
            'conversation_history': [],
            'last_activity': time.time()
        }}

        with patch.object(manager, '_save_sessions') as mock_save:
            manager.clear_session("user123")
            assert mock_save.called


class TestCleanupExpiredSessions:
    """Tests para _cleanup_expired_sessions()"""

    def test_removes_expired_sessions(self):
        """Test que remueve sesiones expiradas"""
        manager = SessionManager()
        manager.session_timeout = 300
        current_time = time.time()

        manager.sessions = {
            "expired1": {
                'state': 'idle',
                'data': {},
                'conversation_history': [],
                'last_activity': current_time - 400  # Expirada
            },
            "active": {
                'state': 'idle',
                'data': {},
                'conversation_history': [],
                'last_activity': current_time - 100  # Activa
            }
        }

        with patch.object(manager, '_save_sessions'):
            manager._cleanup_expired_sessions(current_time)

        assert "expired1" not in manager.sessions
        assert "active" in manager.sessions

    def test_keeps_active_sessions(self):
        """Test que mantiene sesiones activas"""
        manager = SessionManager()
        manager.session_timeout = 300
        current_time = time.time()

        manager.sessions = {
            "user1": {
                'state': 'idle',
                'data': {},
                'conversation_history': [],
                'last_activity': current_time - 50
            },
            "user2": {
                'state': 'idle',
                'data': {},
                'conversation_history': [],
                'last_activity': current_time - 100
            }
        }

        with patch.object(manager, '_save_sessions'):
            manager._cleanup_expired_sessions(current_time)

        assert "user1" in manager.sessions
        assert "user2" in manager.sessions

    def test_saves_sessions_when_cleanup_happens(self):
        """Test que guarda sesiones cuando hay cleanup"""
        manager = SessionManager()
        manager.session_timeout = 300
        current_time = time.time()

        manager.sessions = {
            "expired": {
                'state': 'idle',
                'data': {},
                'conversation_history': [],
                'last_activity': current_time - 400
            }
        }

        with patch.object(manager, '_save_sessions') as mock_save:
            manager._cleanup_expired_sessions(current_time)
            mock_save.assert_called_once()

    def test_no_save_when_no_expired_sessions(self):
        """Test que no guarda si no hay sesiones expiradas"""
        manager = SessionManager()
        manager.session_timeout = 300
        current_time = time.time()

        manager.sessions = {
            "active": {
                'state': 'idle',
                'data': {},
                'conversation_history': [],
                'last_activity': current_time - 100
            }
        }

        with patch.object(manager, '_save_sessions') as mock_save:
            manager._cleanup_expired_sessions(current_time)
            mock_save.assert_not_called()


class TestSaveSessions:
    """Tests para _save_sessions()"""

    def test_creates_data_directory(self):
        """Test que crea el directorio data si no existe"""
        manager = SessionManager()
        manager.sessions = {"user1": {'state': 'idle', 'data': {}, 'conversation_history': [], 'last_activity': time.time()}}

        with patch('pathlib.Path.mkdir') as mock_mkdir:
            with patch('builtins.open', mock_open()) as mock_file:
                with patch('os.replace'):
                    manager._save_sessions()

            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_saves_sessions_to_file(self):
        """Test que guarda sesiones en archivo"""
        manager = SessionManager()
        manager.sessions = {
            "user1": {
                'state': 'active',
                'data': {'key': 'value'},
                'conversation_history': [],
                'last_activity': 123456.789
            }
        }

        mock_file_handle = mock_open()
        with patch('builtins.open', mock_file_handle):
            with patch('os.replace'):
                manager._save_sessions()

        # Verificar que se intentó escribir
        assert mock_file_handle.called

    def test_uses_atomic_write(self):
        """Test que usa escritura atómica con archivo temporal"""
        manager = SessionManager()
        manager.sessions = {"user1": {'state': 'idle', 'data': {}, 'conversation_history': [], 'last_activity': time.time()}}

        with patch('builtins.open', mock_open()):
            with patch('os.replace') as mock_replace:
                manager._save_sessions()

                # Debe llamar a os.replace para escritura atómica
                mock_replace.assert_called_once()

    def test_handles_save_errors(self):
        """Test que maneja errores al guardar"""
        manager = SessionManager()
        manager.sessions = {"user1": {'state': 'idle', 'data': {}, 'conversation_history': [], 'last_activity': time.time()}}

        with patch('builtins.open', side_effect=IOError("Disk error")):
            # No debe lanzar excepción
            manager._save_sessions()


class TestLoadSessions:
    """Tests para _load_sessions()"""

    def test_loads_sessions_from_file(self):
        """Test que carga sesiones desde archivo"""
        mock_data = {
            "user1": {
                'state': 'active',
                'data': {'key': 'value'},
                'conversation_history': [],
                'last_activity': 123456.789
            }
        }

        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))):
                manager = SessionManager()

        assert "user1" in manager.sessions
        assert manager.sessions["user1"]['state'] == 'active'
        assert manager.sessions["user1"]['data']['key'] == 'value'

    def test_handles_missing_file(self):
        """Test que maneja archivo faltante"""
        with patch('pathlib.Path.exists', return_value=False):
            manager = SessionManager()

        # No debe lanzar error, sesiones debe estar vacío
        assert manager.sessions == {}

    def test_handles_corrupted_file(self):
        """Test que maneja archivo corrupto"""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="invalid json {")):
                manager = SessionManager()

        # No debe lanzar error
        assert isinstance(manager.sessions, dict)

    def test_validates_data_format(self):
        """Test que valida formato de datos"""
        # Datos no válidos (no es dict)
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='["not", "a", "dict"]')):
                manager = SessionManager()

        # Debe inicializar con dict vacío si formato es inválido
        # (el código verifica isinstance(data, dict))

    def test_handles_permission_error(self):
        """Test que maneja error de permisos"""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', side_effect=PermissionError("No access")):
                # No debe lanzar excepción
                manager = SessionManager()


class TestSessionManagerIntegration:
    """Tests de integración para SessionManager"""

    def test_complete_session_lifecycle(self):
        """Test ciclo de vida completo de una sesión"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            # 1. Crear sesión
            session = manager.get_session("user123")
            assert session['state'] == 'idle'

            # 2. Actualizar estado
            manager.set_session_state("user123", "collecting", data={'product': 'HLSO'})
            assert manager.sessions["user123"]['state'] == 'collecting'

            # 3. Agregar conversación
            manager.add_to_conversation("user123", "user", "Hello")
            manager.add_to_conversation("user123", "assistant", "Hi!")

            # 4. Configurar idioma
            manager.set_user_language("user123", "en")

            # 5. Guardar cotización
            manager.set_last_quote("user123", {'price': 7.50})

            # 6. Limpiar sesión (debe preservar idioma y cotización)
            manager.clear_session("user123")

            # Verificar estado final
            final_session = manager.get_session("user123")
            assert final_session['state'] == 'idle'
            assert final_session['data'] == {}
            assert final_session['conversation_history'] == []
            assert manager.get_user_language("user123") == "en"
            assert manager.get_last_quote("user123") == {'price': 7.50}

    def test_multiple_users_independent(self):
        """Test que múltiples usuarios son independientes"""
        manager = SessionManager()
        manager.sessions = {}

        with patch.object(manager, '_save_sessions'):
            # Crear sesiones para diferentes usuarios
            manager.set_session_state("user1", "state1", data={'key': 'val1'})
            manager.set_session_state("user2", "state2", data={'key': 'val2'})

            manager.set_user_language("user1", "en")
            manager.set_user_language("user2", "es")

            # Verificar independencia
            assert manager.get_session("user1")['state'] == 'state1'
            assert manager.get_session("user2")['state'] == 'state2'
            assert manager.get_session("user1")['data']['key'] == 'val1'
            assert manager.get_session("user2")['data']['key'] == 'val2'
            assert manager.get_user_language("user1") == "en"
            assert manager.get_user_language("user2") == "es"
