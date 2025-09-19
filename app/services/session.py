import time
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.session_timeout = 300  # 5 minutos
    
    def get_session(self, user_id: str) -> Dict:
        """
        Obtiene la sesión del usuario
        """
        current_time = time.time()
        
        # Limpiar sesiones expiradas
        self._cleanup_expired_sessions(current_time)
        
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                'state': 'idle',
                'data': {},
                'last_activity': current_time
            }
        
        # Actualizar última actividad
        self.sessions[user_id]['last_activity'] = current_time
        return self.sessions[user_id]
    
    def set_session_state(self, user_id: str, state: str, data: Dict = None):
        """
        Establece el estado de la sesión
        """
        session = self.get_session(user_id)
        session['state'] = state
        if data:
            session['data'].update(data)
        
        logger.info(f"Usuario {user_id} - Estado: {state}, Datos: {session['data']}")
    
    def clear_session(self, user_id: str):
        """
        Limpia la sesión del usuario
        """
        if user_id in self.sessions:
            del self.sessions[user_id]
    
    def _cleanup_expired_sessions(self, current_time: float):
        """
        Limpia sesiones expiradas
        """
        expired_users = []
        for user_id, session in self.sessions.items():
            if current_time - session['last_activity'] > self.session_timeout:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.sessions[user_id]
            logger.info(f"Sesión expirada para usuario: {user_id}")

# Instancia global del manejador de sesiones
session_manager = SessionManager()