import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SESSIONS_FILE = Path("data") / "sessions.json"


class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.session_timeout = 300  # 5 minutos
        # Intentar cargar sesiones desde disco
        try:
            self._load_sessions()
        except Exception as e:
            logger.warning(f"No se pudieron cargar sesiones previas: {e}")

    def get_session(self, user_id: str) -> dict:
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
                'conversation_history': [],  # Historial de conversación con GPT
                'last_activity': current_time
            }

        # Actualizar última actividad
        self.sessions[user_id]['last_activity'] = current_time
        return self.sessions[user_id]

    def add_to_conversation(self, user_id: str, role: str, content: str):
        """
        Agrega un mensaje al historial de conversación
        
        Args:
            user_id: ID del usuario
            role: 'user' o 'assistant'
            content: Contenido del mensaje
        """
        session = self.get_session(user_id)

        if 'conversation_history' not in session:
            session['conversation_history'] = []

        session['conversation_history'].append({
            'role': role,
            'content': content
        })

        # Mantener solo los últimos 20 mensajes para no exceder límites de tokens
        if len(session['conversation_history']) > 20:
            session['conversation_history'] = session['conversation_history'][-20:]

        logger.debug(f"Mensaje agregado al historial de {user_id}: {role}")
        
        # 🆕 Guardar sesiones después de agregar mensaje
        self._save_sessions()
        
        # 🆕 ETL: Capturar mensaje para entrenamiento si hay consentimiento
        # Capturar tanto mensajes de usuario como respuestas del asistente
        if session.get('consent_for_training'):
            self._capture_for_training(user_id, content, role)

    def get_conversation_history(self, user_id: str) -> list:
        """
        Obtiene el historial de conversación del usuario
        """
        session = self.get_session(user_id)
        return session.get('conversation_history', [])

    def set_session_state(self, user_id: str, state: str, data: dict = None):
        """
        Establece el estado de la sesión
        """
        session = self.get_session(user_id)
        session['state'] = state
        if data:
            session['data'].update(data)

        logger.debug(f"Usuario {user_id} - Estado: {state}, Datos: {session['data']}")
        self._save_sessions()

    def set_last_quote(self, user_id: str, quote_data: dict):
        """
        Almacena la última cotización para poder generar PDF
        """
        session = self.get_session(user_id)
        session['last_quote'] = quote_data
        logger.debug(f"Cotización almacenada para usuario {user_id}")
        self._save_sessions()

    def get_last_quote(self, user_id: str) -> dict | None:
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
        self._save_sessions()

    def get_user_language(self, user_id: str) -> str:
        """
        Obtiene el idioma preferido del usuario (por defecto español)
        """
        session = self.get_session(user_id)
        return session.get('language', 'es')

    def clear_session(self, user_id: str):
        """
        Limpia la sesión del usuario (preserva idioma, última cotización y consentimiento)
        """
        if user_id in self.sessions:
            # Preservar datos importantes al limpiar sesión
            language = self.sessions[user_id].get('language', 'es')
            last_quote = self.sessions[user_id].get('last_quote')
            # 🆕 Preservar consentimiento
            consent_for_training = self.sessions[user_id].get('consent_for_training')
            consent_timestamp = self.sessions[user_id].get('consent_timestamp')
            consent_asked = self.sessions[user_id].get('consent_asked')
            
            del self.sessions[user_id]
            # Recrear sesión con datos preservados
            self.get_session(user_id)
            self.sessions[user_id]['language'] = language
            
            if last_quote:
                self.sessions[user_id]['last_quote'] = last_quote
                logger.debug(f"Cotización preservada después de limpiar sesión para {user_id}")
            
            # 🆕 Restaurar consentimiento
            if consent_timestamp is not None:
                self.sessions[user_id]['consent_for_training'] = consent_for_training
                self.sessions[user_id]['consent_timestamp'] = consent_timestamp
                self.sessions[user_id]['consent_asked'] = consent_asked
                logger.debug(f"Consentimiento preservado después de limpiar sesión para {user_id}")
            
            self._save_sessions()

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
        if expired_users:
            self._save_sessions()

    def _save_sessions(self):
        """Guardar sesiones en disco de forma atómica"""
        try:
            SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = SESSIONS_FILE.with_suffix('.tmp')
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, ensure_ascii=False, indent=2)
            os.replace(tmp, SESSIONS_FILE)
        except Exception as e:
            logger.error(f"Error guardando sesiones en disco: {e}")

    def _load_sessions(self):
        """Cargar sesiones desde disco si existe"""
        if SESSIONS_FILE.exists():
            try:
                with open(SESSIONS_FILE, encoding='utf-8') as f:
                    data = json.load(f)
                    # Verificar formato
                    if isinstance(data, dict):
                        self.sessions = data
                        logger.info(f"Cargadas {len(self.sessions)} sesiones desde disco")
            except Exception as e:
                logger.error(f"Error cargando sessions file: {e}")

    # 🆕 MÉTODOS PARA ENTRENAMIENTO Y CONSENTIMIENTO
    
    def set_training_consent(self, user_id: str, consent: bool):
        """
        Establece el consentimiento del usuario para usar sus mensajes en entrenamiento.
        
        Args:
            user_id: ID del usuario
            consent: True si acepta, False si no
        """
        session = self.get_session(user_id)
        session['consent_for_training'] = consent
        session['consent_timestamp'] = time.time()
        self._save_sessions()
        logger.info(f"✅ Consentimiento de entrenamiento para {user_id}: {consent}")
    
    def get_training_consent(self, user_id: str) -> bool:
        """
        Obtiene el consentimiento del usuario para entrenamiento.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si ha dado consentimiento
        """
        session = self.get_session(user_id)
        return session.get('consent_for_training', False)
    
    def _capture_for_training(self, user_id: str, content: str, role: str):
        """
        Captura un mensaje para el pipeline de entrenamiento.
        
        Args:
            user_id: ID del usuario
            content: Contenido del mensaje
            role: Rol (user/assistant)
        """
        try:
            # 🆕 Usar el nuevo sistema de captura con base de datos
            from app.services.training_capture_db import get_capture_service
            
            capture = get_capture_service()
            
            # Capturar con metadatos
            metadata = {
                'state': self.sessions[user_id].get('state'),
                'has_quote': 'last_quote' in self.sessions[user_id],
            }
            
            capture.capture_message(user_id, content, role, metadata)
            
        except Exception as e:
            logger.error(f"❌ Error capturando mensaje para entrenamiento: {str(e)}")
    
    def export_training_data(self, user_id: str = None) -> dict:
        """
        Exporta datos de entrenamiento.
        
        Args:
            user_id: Si se especifica, solo exporta de ese usuario
            
        Returns:
            Estadísticas de exportación
        """
        try:
            from app.services.training_pipeline import get_training_pipeline
            
            pipeline = get_training_pipeline()
            train_count, valid_count = pipeline.export_for_finetune()
            
            return {
                'success': True,
                'train_examples': train_count,
                'valid_examples': valid_count,
                'total': train_count + valid_count
            }
        except Exception as e:
            logger.error(f"❌ Error exportando datos de entrenamiento: {str(e)}")
            return {'success': False, 'error': str(e)}


# Instancia global del manejador de sesiones
session_manager = SessionManager()
