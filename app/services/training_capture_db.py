"""
Sistema de captura de mensajes usando SQLite para persistencia.

Este módulo reemplaza el sistema basado en archivos JSON con una base de datos SQLite
que persiste incluso cuando el contenedor se reinicia en Render.

Uso:
    from app.services.training_capture_db import get_capture_service
    
    capture = get_capture_service()
    capture.capture_message(user_id, message, role='user')
"""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager

from app.utils.anonymizer import anonymize

logger = logging.getLogger(__name__)


class TrainingCaptureDB:
    """
    Servicio de captura de mensajes con persistencia en SQLite.
    """
    
    def __init__(self, db_path: str = "data/training_messages.db"):
        """
        Inicializa el servicio de captura.
        
        Args:
            db_path: Ruta a la base de datos SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Inicializar base de datos
        self._init_database()
        
        logger.info(f"📦 Training Capture DB inicializado: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones a la base de datos."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """Crea las tablas si no existen."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla principal de mensajes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    original_length INTEGER,
                    status TEXT DEFAULT 'pending',
                    confidence REAL DEFAULT 0.0,
                    analysis TEXT,
                    qa_passed BOOLEAN DEFAULT 0,
                    qa_errors TEXT,
                    metadata TEXT,
                    captured_at TEXT NOT NULL,
                    processed_at TEXT,
                    reviewed_at TEXT,
                    reviewed_by TEXT,
                    review_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices para búsquedas rápidas
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON messages(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id 
                ON messages(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_captured_at 
                ON messages(captured_at DESC)
            """)
            
            logger.info("✅ Base de datos inicializada")
    
    def capture_message(
        self,
        user_id: str,
        message: str,
        role: str = "user",
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Captura un mensaje para procesamiento.
        
        Args:
            user_id: ID del usuario
            message: Contenido del mensaje
            role: Rol (user/assistant)
            metadata: Metadatos adicionales
            
        Returns:
            True si se capturó exitosamente
        """
        try:
            # Filtrado básico
            if not self._should_capture(message):
                return False
            
            # Anonimizar
            anonymized_user_id = anonymize(user_id)
            anonymized_message = anonymize(message)
            
            # Guardar en base de datos
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages 
                    (user_id, role, content, original_length, metadata, captured_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    anonymized_user_id,
                    role,
                    anonymized_message,
                    len(message),
                    json.dumps(metadata or {}),
                    datetime.now().isoformat(),
                    'needs_review'  # Por defecto necesita revisión
                ))
            
            logger.info(f"📥 Mensaje capturado: {role} de {anonymized_user_id[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error capturando mensaje: {str(e)}")
            return False
    
    def _should_capture(self, message: str) -> bool:
        """
        Determina si un mensaje debe ser capturado.
        
        Args:
            message: Mensaje a evaluar
            
        Returns:
            True si debe capturarse
        """
        if not message or not isinstance(message, str):
            return False
        
        message_lower = message.lower().strip()
        
        # Muy corto
        if len(message_lower) < 5:
            return False
        
        # Solo saludos simples
        simple_greetings = ['hola', 'hi', 'hello', 'ok', 'gracias', 'thanks', 'bye', 'adios']
        if message_lower in simple_greetings:
            return False
        
        return True
    
    def get_pending_reviews(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "captured_at",
        sort_desc: bool = True
    ) -> Tuple[List[Dict], int]:
        """
        Obtiene mensajes pendientes de revisión.
        
        Args:
            limit: Máximo de items a retornar
            offset: Offset para paginación
            sort_by: Campo para ordenar
            sort_desc: Orden descendente
            
        Returns:
            Tupla (lista de mensajes, total)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Contar total
                cursor.execute("""
                    SELECT COUNT(*) as total 
                    FROM messages 
                    WHERE status = 'needs_review'
                """)
                total = cursor.fetchone()['total']
                
                # Obtener mensajes
                order = "DESC" if sort_desc else "ASC"
                query = f"""
                    SELECT * FROM messages 
                    WHERE status = 'needs_review'
                    ORDER BY {sort_by} {order}
                    LIMIT ? OFFSET ?
                """
                
                cursor.execute(query, (limit, offset))
                rows = cursor.fetchall()
                
                messages = []
                for row in rows:
                    messages.append({
                        'id': str(row['id']),
                        'user_id': row['user_id'],
                        'role': row['role'],
                        'content': row['content'],
                        'status': row['status'],
                        'confidence': row['confidence'],
                        'analysis': json.loads(row['analysis']) if row['analysis'] else {},
                        'qa_passed': bool(row['qa_passed']),
                        'qa_errors': json.loads(row['qa_errors']) if row['qa_errors'] else [],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                        'captured_at': row['captured_at'],
                        'reviewed_at': row['reviewed_at'],
                        'reviewed_by': row['reviewed_by'],
                        'review_notes': row['review_notes'],
                    })
                
                return messages, total
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo mensajes pendientes: {str(e)}")
            return [], 0
    
    def approve_message(
        self,
        message_id: int,
        reviewer: str = "admin",
        notes: str = ""
    ) -> Tuple[bool, str]:
        """
        Aprueba un mensaje para entrenamiento.
        
        Args:
            message_id: ID del mensaje
            reviewer: Nombre del revisor
            notes: Notas de revisión
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE messages 
                    SET status = 'approved',
                        reviewed_at = ?,
                        reviewed_by = ?,
                        review_notes = ?
                    WHERE id = ?
                """, (
                    datetime.now().isoformat(),
                    reviewer,
                    notes,
                    message_id
                ))
                
                if cursor.rowcount == 0:
                    return False, f"Mensaje {message_id} no encontrado"
                
                logger.info(f"✅ Mensaje {message_id} aprobado por {reviewer}")
                return True, f"Mensaje {message_id} aprobado"
                
        except Exception as e:
            logger.error(f"❌ Error aprobando mensaje: {str(e)}")
            return False, str(e)
    
    def reject_message(
        self,
        message_id: int,
        reviewer: str = "admin",
        reason: str = ""
    ) -> Tuple[bool, str]:
        """
        Rechaza un mensaje.
        
        Args:
            message_id: ID del mensaje
            reviewer: Nombre del revisor
            reason: Razón del rechazo
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE messages 
                    SET status = 'rejected',
                        reviewed_at = ?,
                        reviewed_by = ?,
                        review_notes = ?
                    WHERE id = ?
                """, (
                    datetime.now().isoformat(),
                    reviewer,
                    reason,
                    message_id
                ))
                
                if cursor.rowcount == 0:
                    return False, f"Mensaje {message_id} no encontrado"
                
                logger.info(f"❌ Mensaje {message_id} rechazado por {reviewer}")
                return True, f"Mensaje {message_id} rechazado"
                
        except Exception as e:
            logger.error(f"❌ Error rechazando mensaje: {str(e)}")
            return False, str(e)
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas de captura."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Contar por status
                cursor.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM messages 
                    GROUP BY status
                """)
                
                stats = {
                    'total_messages': 0,
                    'by_status': {},
                    'by_role': {}
                }
                
                for row in cursor.fetchall():
                    status = row['status']
                    count = row['count']
                    stats['by_status'][status] = count
                    stats['total_messages'] += count
                
                # Contar por rol
                cursor.execute("""
                    SELECT role, COUNT(*) as count 
                    FROM messages 
                    GROUP BY role
                """)
                
                for row in cursor.fetchall():
                    stats['by_role'][row['role']] = row['count']
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {str(e)}")
            return {}
    
    def export_for_finetune(self, output_path: str = "data/finetune/train.jsonl") -> int:
        """
        Exporta mensajes aprobados a formato JSONL para fine-tuning.
        
        Args:
            output_path: Ruta del archivo de salida
            
        Returns:
            Número de ejemplos exportados
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener mensajes aprobados ordenados por usuario y tiempo
                cursor.execute("""
                    SELECT * FROM messages 
                    WHERE status = 'approved'
                    ORDER BY user_id, captured_at
                """)
                
                messages = cursor.fetchall()
                
                # Agrupar por usuario para crear pares
                examples = []
                current_user = None
                user_messages = []
                
                for msg in messages:
                    if msg['user_id'] != current_user:
                        # Procesar usuario anterior
                        if user_messages:
                            examples.extend(self._create_pairs(user_messages))
                        # Nuevo usuario
                        current_user = msg['user_id']
                        user_messages = []
                    
                    user_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
                
                # Procesar último usuario
                if user_messages:
                    examples.extend(self._create_pairs(user_messages))
                
                # Exportar
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    for example in examples:
                        f.write(json.dumps(example, ensure_ascii=False) + '\n')
                
                logger.info(f"✅ Exportados {len(examples)} ejemplos a {output_path}")
                return len(examples)
                
        except Exception as e:
            logger.error(f"❌ Error exportando para fine-tuning: {str(e)}")
            return 0
    
    def _create_pairs(self, messages: List[Dict]) -> List[Dict]:
        """Crea pares user-assistant de una lista de mensajes."""
        pairs = []
        
        for i in range(len(messages) - 1):
            if messages[i]['role'] == 'user' and messages[i+1]['role'] == 'assistant':
                pairs.append({
                    "messages": [
                        {"role": "user", "content": messages[i]['content']},
                        {"role": "assistant", "content": messages[i+1]['content']}
                    ]
                })
        
        return pairs


# Singleton
_capture_service: Optional[TrainingCaptureDB] = None


def get_capture_service(db_path: str = "data/training_messages.db") -> TrainingCaptureDB:
    """
    Obtiene la instancia singleton del servicio de captura.
    
    Args:
        db_path: Ruta a la base de datos
        
    Returns:
        Instancia de TrainingCaptureDB
    """
    global _capture_service
    if _capture_service is None:
        _capture_service = TrainingCaptureDB(db_path)
    return _capture_service
