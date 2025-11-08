"""
Tests para utilidades de mensajes y deduplicación
"""
import time
import pytest
from app.utils.message_utils import (
    cleanup_old_messages,
    is_duplicate_message,
    processed_messages,
    message_timestamps
)


class TestMessageDeduplication:
    """Tests para deduplicación de mensajes"""

    def setup_method(self):
        """Limpiar estado antes de cada test"""
        processed_messages.clear()
        message_timestamps.clear()

    def test_first_message_not_duplicate(self):
        """Primer mensaje no es duplicado"""
        message_sid = "SM1234567890"
        assert is_duplicate_message(message_sid) is False
        assert message_sid in processed_messages

    def test_second_same_message_is_duplicate(self):
        """Segundo mensaje con mismo SID es duplicado"""
        message_sid = "SM1234567890"
        is_duplicate_message(message_sid)  # Primera vez
        assert is_duplicate_message(message_sid) is True  # Segunda vez

    def test_different_messages_not_duplicates(self):
        """Mensajes diferentes no son duplicados"""
        message_sid_1 = "SM1234567890"
        message_sid_2 = "SM0987654321"

        assert is_duplicate_message(message_sid_1) is False
        assert is_duplicate_message(message_sid_2) is False

    def test_cleanup_old_messages(self):
        """Limpia mensajes antiguos (>5 minutos)"""
        # Agregar mensaje antiguo manualmente
        old_message_sid = "SM_OLD_123"
        processed_messages.add(old_message_sid)
        message_timestamps[old_message_sid] = time.time() - 400  # 6 minutos y 40 segundos atrás

        # Agregar mensaje reciente
        recent_message_sid = "SM_RECENT_456"
        processed_messages.add(recent_message_sid)
        message_timestamps[recent_message_sid] = time.time()

        # Ejecutar limpieza
        cleanup_old_messages()

        # Verificar que el mensaje antiguo fue eliminado
        assert old_message_sid not in processed_messages
        assert old_message_sid not in message_timestamps

        # Verificar que el mensaje reciente se mantuvo
        assert recent_message_sid in processed_messages
        assert recent_message_sid in message_timestamps

    def test_is_duplicate_calls_cleanup(self):
        """is_duplicate_message llama a cleanup_old_messages"""
        # Agregar mensaje antiguo
        old_message_sid = "SM_OLD_789"
        processed_messages.add(old_message_sid)
        message_timestamps[old_message_sid] = time.time() - 400

        # Llamar is_duplicate_message con nuevo mensaje
        new_message_sid = "SM_NEW_101"
        is_duplicate_message(new_message_sid)

        # Verificar que el mensaje antiguo fue limpiado
        assert old_message_sid not in processed_messages

    def test_message_timestamp_recorded(self):
        """Verifica que el timestamp se registra correctamente"""
        message_sid = "SM1234567890"
        before_time = time.time()
        is_duplicate_message(message_sid)
        after_time = time.time()

        assert message_sid in message_timestamps
        assert before_time <= message_timestamps[message_sid] <= after_time

    def test_multiple_duplicates_same_message(self):
        """Múltiples llamadas al mismo mensaje siempre retornan True después de la primera"""
        message_sid = "SM1234567890"

        # Primera vez: False
        assert is_duplicate_message(message_sid) is False

        # Llamadas subsiguientes: True
        for _ in range(5):
            assert is_duplicate_message(message_sid) is True

    def test_cleanup_does_not_affect_recent_messages(self):
        """Limpieza no afecta mensajes recientes (<5 minutos)"""
        # Agregar varios mensajes recientes
        recent_sids = [f"SM_RECENT_{i}" for i in range(10)]
        for sid in recent_sids:
            is_duplicate_message(sid)

        # Ejecutar limpieza
        cleanup_old_messages()

        # Todos los mensajes recientes deben permanecer
        for sid in recent_sids:
            assert sid in processed_messages
            assert sid in message_timestamps