"""
Pipeline ETL para captura, procesamiento y preparación de datos de entrenamiento.

Flujo:
1. Captura de mensajes con consentimiento
2. Anonimización
3. Filtrado inicial
4. Análisis automático con OpenAI
5. Validación QA
6. Almacenamiento para exportación
"""
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.utils.anonymizer import anonymize, anonymize_conversation

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """
    Pipeline completo para preparar datos de entrenamiento desde mensajes de usuarios.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Inicializa el pipeline.
        
        Args:
            data_dir: Directorio base para almacenar datos
        """
        self.data_dir = Path(data_dir)
        self.etl_queue_dir = self.data_dir / "etl_queue"
        self.processed_dir = self.data_dir / "processed"
        self.rejected_dir = self.data_dir / "rejected"
        self.finetune_dir = self.data_dir / "finetune"
        
        # Crear directorios
        for dir_path in [self.etl_queue_dir, self.processed_dir, self.rejected_dir, self.finetune_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Estadísticas
        self._stats = {
            'captured': 0,
            'anonymized': 0,
            'filtered_out': 0,
            'analyzed': 0,
            'qa_passed': 0,
            'qa_failed': 0,
            'exported': 0,
            'needs_review': 0,
        }
    
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
            # Filtrado inicial básico
            if not self._should_capture(message):
                self._stats['filtered_out'] += 1
                return False
            
            # Anonimizar
            anonymized_message = anonymize(message)
            self._stats['anonymized'] += 1
            
            # Crear registro
            record = {
                'user_id': anonymize(user_id),  # Anonimizar también el user_id
                'role': role,
                'original_length': len(message),
                'content': anonymized_message,
                'metadata': metadata or {},
                'captured_at': datetime.now().isoformat(),
                'status': 'pending',
            }
            
            # Guardar en cola
            import time
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            microseconds = int(time.time() * 1000000) % 1000000
            filename = f"{timestamp}_{microseconds}_{user_id[:8]}.json"
            filepath = self.etl_queue_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            
            self._stats['captured'] += 1
            logger.info(f"📥 Mensaje capturado: {filepath.name}")
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
        
        # Debe contener al menos una palabra relevante
        relevant_keywords = [
            'hlso', 'hoso', 'p&d', 'cooked', 'precio', 'cotizacion', 'proforma',
            'glaseo', 'flete', 'cfr', 'cif', 'talla', 'camaron', 'langostino',
            'quote', 'price', 'shrimp'
        ]
        
        has_relevant = any(keyword in message_lower for keyword in relevant_keywords)
        
        # O contiene tallas
        has_size = bool(re.search(r'\d+[/-]\d+', message))
        
        return has_relevant or has_size
    
    def process_queue(
        self,
        openai_service=None,
        qa_service=None,
        max_items: int = 100
    ) -> Dict:
        """
        Procesa mensajes en la cola ETL.
        
        Args:
            openai_service: Servicio de OpenAI para análisis
            qa_service: Servicio de QA para validación
            max_items: Máximo de items a procesar
            
        Returns:
            Estadísticas del procesamiento
        """
        import re
        
        processed_count = 0
        results = {
            'processed': 0,
            'passed_qa': 0,
            'failed_qa': 0,
            'needs_review': 0,
            'errors': 0,
        }
        
        # Obtener archivos pendientes
        pending_files = sorted(self.etl_queue_dir.glob("*.json"))[:max_items]
        
        for filepath in pending_files:
            try:
                # Leer registro
                with open(filepath, 'r', encoding='utf-8') as f:
                    record = json.load(f)
                
                # Analizar con OpenAI si está disponible
                if openai_service and record['role'] == 'user':
                    analysis = openai_service.analyze_user_intent(record['content'])
                    record['analysis'] = analysis
                    record['confidence'] = analysis.get('confidence', 0)
                    self._stats['analyzed'] += 1
                else:
                    record['analysis'] = {}
                    record['confidence'] = 0.5
                
                # Validar con QA si está disponible
                qa_passed = True
                qa_errors = []
                
                if qa_service and record.get('analysis'):
                    analysis = record['analysis']
                    
                    # Validar producto
                    if analysis.get('product'):
                        if not qa_service.validate_product(analysis['product']):
                            qa_passed = False
                            qa_errors.append(f"Producto inválido: {analysis['product']}")
                    
                    # Validar talla
                    if analysis.get('size'):
                        if not qa_service.validate_size(analysis['size']):
                            qa_passed = False
                            qa_errors.append(f"Talla inválida: {analysis['size']}")
                    
                    # Validar glaseo
                    if analysis.get('glaseo_percentage') is not None:
                        if not qa_service.validate_glaseo(analysis['glaseo_percentage']):
                            qa_passed = False
                            qa_errors.append(f"Glaseo inválido: {analysis['glaseo_percentage']}")
                
                record['qa_passed'] = qa_passed
                record['qa_errors'] = qa_errors
                
                # Determinar destino
                if qa_passed and record.get('confidence', 0) >= 0.85:
                    # Aprobado para entrenamiento
                    dest_dir = self.processed_dir
                    record['status'] = 'approved'
                    results['passed_qa'] += 1
                    self._stats['qa_passed'] += 1
                elif record.get('confidence', 0) < 0.85:
                    # Necesita revisión humana
                    dest_dir = self.processed_dir
                    record['status'] = 'needs_review'
                    results['needs_review'] += 1
                    self._stats['needs_review'] += 1
                else:
                    # Rechazado
                    dest_dir = self.rejected_dir
                    record['status'] = 'rejected'
                    results['failed_qa'] += 1
                    self._stats['qa_failed'] += 1
                
                # Mover archivo
                dest_path = dest_dir / filepath.name
                with open(dest_path, 'w', encoding='utf-8') as f:
                    json.dump(record, f, ensure_ascii=False, indent=2)
                
                # Eliminar de cola
                filepath.unlink()
                
                processed_count += 1
                results['processed'] += 1
                
            except Exception as e:
                logger.error(f"❌ Error procesando {filepath.name}: {str(e)}")
                results['errors'] += 1
        
        logger.info(f"✅ Procesados {processed_count} mensajes: {results}")
        return results
    
    def export_for_finetune(
        self,
        min_confidence: float = 0.85,
        train_split: float = 0.9
    ) -> Tuple[int, int]:
        """
        Exporta datos aprobados a formato JSONL para fine-tuning.
        
        Args:
            min_confidence: Confianza mínima para incluir
            train_split: Proporción para entrenamiento (resto para validación)
            
        Returns:
            Tupla (ejemplos_train, ejemplos_valid)
        """
        import random
        
        examples = []
        
        # 🆕 Leer archivos desde la cola ETL directamente (no requiere procesamiento)
        all_files = list(self.etl_queue_dir.glob("*.json")) + list(self.processed_dir.glob("*.json"))
        
        # Agrupar mensajes por user_id y timestamp para crear pares
        messages_by_user = {}
        
        for filepath in all_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    record = json.load(f)
                
                user_id = record.get('user_id', 'unknown')
                role = record.get('role')
                content = record.get('content', '').strip()
                
                if not content or len(content) < 5:
                    continue
                
                if user_id not in messages_by_user:
                    messages_by_user[user_id] = []
                
                messages_by_user[user_id].append({
                    'role': role,
                    'content': content,
                    'timestamp': record.get('captured_at', ''),
                    'confidence': record.get('confidence', 0.7)  # Default confidence
                })
            
            except Exception as e:
                logger.error(f"❌ Error leyendo {filepath.name}: {str(e)}")
        
        # Crear pares user → assistant
        for user_id, messages in messages_by_user.items():
            # Ordenar por timestamp
            messages.sort(key=lambda x: x['timestamp'])
            
            # Buscar pares consecutivos
            for i in range(len(messages) - 1):
                if messages[i]['role'] == 'user' and messages[i+1]['role'] == 'assistant':
                    user_msg = messages[i]['content']
                    assistant_msg = messages[i+1]['content']
                    confidence = messages[i].get('confidence', 0.7)
                    
                    # Filtrar por longitud mínima
                    if len(user_msg) < 10 or len(assistant_msg) < 10:
                        continue
                    
                    # Formato nuevo de OpenAI (messages)
                    example = {
                        "messages": [
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": assistant_msg}
                        ]
                    }
                    examples.append(example)
        
        if not examples:
            logger.warning("⚠️ No hay ejemplos para exportar")
            return 0, 0
        
        # Mezclar y dividir
        random.shuffle(examples)
        split_idx = int(len(examples) * train_split)
        train_examples = examples[:split_idx]
        valid_examples = examples[split_idx:]
        
        # Exportar
        train_path = self.finetune_dir / "train.jsonl"
        valid_path = self.finetune_dir / "valid.jsonl"
        
        with open(train_path, 'w', encoding='utf-8') as f:
            for ex in train_examples:
                f.write(json.dumps(ex, ensure_ascii=False) + '\n')
        
        with open(valid_path, 'w', encoding='utf-8') as f:
            for ex in valid_examples:
                f.write(json.dumps(ex, ensure_ascii=False) + '\n')
        
        self._stats['exported'] = len(examples)
        logger.info(f"✅ Exportados {len(train_examples)} train, {len(valid_examples)} valid")
        
        return len(train_examples), len(valid_examples)
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del pipeline.
        
        Returns:
            Diccionario con estadísticas
        """
        # Agregar conteos de archivos
        stats = self._stats.copy()
        stats['queue_size'] = len(list(self.etl_queue_dir.glob("*.json")))
        stats['processed_size'] = len(list(self.processed_dir.glob("*.json")))
        stats['rejected_size'] = len(list(self.rejected_dir.glob("*.json")))
        return stats
    
    def reset_stats(self):
        """Reinicia las estadísticas."""
        for key in self._stats:
            self._stats[key] = 0


# Instancia global
_pipeline = None


def get_training_pipeline(data_dir: str = "data") -> TrainingPipeline:
    """
    Obtiene la instancia global del pipeline.
    
    Args:
        data_dir: Directorio de datos
        
    Returns:
        Instancia del pipeline
    """
    global _pipeline
    if _pipeline is None:
        _pipeline = TrainingPipeline(data_dir)
    return _pipeline
