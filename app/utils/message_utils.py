"""
Utilidades para manejo de mensajes y deduplicación.
"""
import logging
import time

logger = logging.getLogger(__name__)

# Cache para deduplicación de mensajes
processed_messages: set[str] = set()
message_timestamps: dict[str, float] = {}


def cleanup_old_messages():
    """
    Limpia mensajes procesados antiguos (más de 5 minutos)
    """
    current_time = time.time()
    expired_messages = []

    for message_sid, timestamp in message_timestamps.items():
        if current_time - timestamp > 300:  # 5 minutos
            expired_messages.append(message_sid)

    for message_sid in expired_messages:
        processed_messages.discard(message_sid)
        message_timestamps.pop(message_sid, None)


def is_duplicate_message(message_sid: str) -> bool:
    """
    Verifica si un mensaje ya fue procesado
    """
    cleanup_old_messages()

    if message_sid in processed_messages:
        logger.warning(f"🔄 Mensaje duplicado detectado: {message_sid}")
        return True

    # Marcar como procesado
    processed_messages.add(message_sid)
    message_timestamps[message_sid] = time.time()
    return False
