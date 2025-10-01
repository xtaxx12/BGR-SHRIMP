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
        
        logger.debug(f"Usuario {user_id} - Estado: {state}, Datos: {session['data']}")
    
    def set_last_quote(self, user_id: str, quote_data: Dict):
        """
        Almacena la última cotización para poder generar PDF
        """
        session = self.get_session(user_id)
        session['last_quote'] = quote_data
        logger.debug(f"Cotización almacenada para usuario {user_id}")
    
    def get_last_quote(self, user_id: str) -> Optional[Dict]:
        """
        Obtiene la última cotización del usuario
        """
        session = self.get_session(user_id)
        return session.get('last_quote')
    
    def set_user_language(self, user_id: str, language: str):
        """
        Establece el idioma preferido del usuario
        """
        session = self.get_session(user_id)
        session['language'] = language
        logger.info(f"Idioma configurado para usuario {user_id}: {language}")
    
    def get_user_language(self, user_id: str) -> str:
        """
        Obtiene el idioma preferido del usuario (por defecto español)
        """
        session = self.get_session(user_id)
        return session.get('language', 'es')
    
    def clear_session(self, user_id: str):
        """
        Limpia la sesión del usuario (preserva idioma)
        """
        if user_id in self.sessions:
            # Preservar idioma al limpiar sesión
            language = self.sessions[user_id].get('language', 'es')
            del self.sessions[user_id]
            # Recrear sesión con idioma preservado
            self.get_session(user_id)
            self.sessions[user_id]['language'] = language
    
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