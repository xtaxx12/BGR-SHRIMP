"""
Servicio de Revisión Humana para datos de entrenamiento.

Este módulo permite:
1. Listar mensajes que necesitan revisión (status='needs_review')
2. Aprobar mensajes para entrenamiento
3. Rechazar mensajes
4. Editar mensajes antes de aprobar
5. Re-analizar mensajes con OpenAI
6. Estadísticas de revisión

Uso:
    from app.services.human_review import get_review_service

    review = get_review_service()
    pending = review.get_pending_reviews()
    review.approve_item(item_id)
"""
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ReviewItem:
    """Representa un item pendiente de revisión."""
    id: str
    filename: str
    content: str
    role: str
    user_id: str
    status: str
    confidence: float
    analysis: Dict[str, Any]
    qa_passed: bool
    qa_errors: List[str]
    metadata: Dict[str, Any]
    captured_at: str
    review_notes: str = ""
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convierte a diccionario."""
        return asdict(self)


class HumanReviewService:
    """
    Servicio para revisión humana de datos de entrenamiento.

    Los items con status='needs_review' son mostrados para revisión.
    Un revisor puede:
    - Aprobar: Mover a 'approved' para incluir en entrenamiento
    - Rechazar: Mover a 'rejected' para excluir
    - Editar: Modificar contenido/análisis antes de aprobar
    - Re-analizar: Volver a analizar con OpenAI
    """

    def __init__(self, data_dir: str = "data"):
        """
        Inicializa el servicio de revisión.

        Args:
            data_dir: Directorio base de datos
        """
        self.data_dir = Path(data_dir)
        self.processed_dir = self.data_dir / "processed"
        self.rejected_dir = self.data_dir / "rejected"
        self.approved_dir = self.data_dir / "approved"  # Nuevo directorio para aprobados

        # Crear directorios si no existen
        for dir_path in [self.processed_dir, self.rejected_dir, self.approved_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Estadísticas de revisión
        self._stats = {
            'total_reviewed': 0,
            'approved': 0,
            'rejected': 0,
            'edited': 0,
            'reanalyzed': 0,
        }

        logger.info("👁️ Servicio de Revisión Humana inicializado")

    # ==================== LISTAR ITEMS ====================

    def get_pending_reviews(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "captured_at",
        sort_desc: bool = True
    ) -> Tuple[List[ReviewItem], int]:
        """
        Obtiene items pendientes de revisión.

        Args:
            limit: Máximo de items a retornar
            offset: Offset para paginación
            sort_by: Campo para ordenar (captured_at, confidence)
            sort_desc: Orden descendente

        Returns:
            Tupla (lista de items, total de items pendientes)
        """
        items = []

        # Buscar en processed_dir los que tienen status='needs_review'
        for filepath in self.processed_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    record = json.load(f)

                if record.get('status') == 'needs_review':
                    item = self._record_to_review_item(filepath, record)
                    items.append(item)

            except Exception as e:
                logger.error(f"❌ Error leyendo {filepath.name}: {str(e)}")

        # Ordenar
        if sort_by == 'confidence':
            items.sort(key=lambda x: x.confidence, reverse=sort_desc)
        else:  # captured_at
            items.sort(key=lambda x: x.captured_at, reverse=sort_desc)

        total = len(items)

        # Paginar
        paginated = items[offset:offset + limit]

        return paginated, total

    def get_review_item(self, item_id: str) -> Optional[ReviewItem]:
        """
        Obtiene un item específico por ID.

        Args:
            item_id: ID del item (nombre de archivo sin extensión)

        Returns:
            ReviewItem o None si no existe
        """
        # Buscar en processed_dir
        filepath = self.processed_dir / f"{item_id}.json"

        if not filepath.exists():
            # Buscar en otros directorios
            for dir_path in [self.approved_dir, self.rejected_dir]:
                alt_path = dir_path / f"{item_id}.json"
                if alt_path.exists():
                    filepath = alt_path
                    break

        if not filepath.exists():
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                record = json.load(f)
            return self._record_to_review_item(filepath, record)
        except Exception as e:
            logger.error(f"❌ Error leyendo item {item_id}: {str(e)}")
            return None

    def _record_to_review_item(self, filepath: Path, record: Dict) -> ReviewItem:
        """Convierte un registro a ReviewItem."""
        return ReviewItem(
            id=filepath.stem,  # Nombre sin extensión
            filename=filepath.name,
            content=record.get('content', ''),
            role=record.get('role', 'user'),
            user_id=record.get('user_id', 'unknown'),
            status=record.get('status', 'unknown'),
            confidence=record.get('confidence', 0),
            analysis=record.get('analysis', {}),
            qa_passed=record.get('qa_passed', False),
            qa_errors=record.get('qa_errors', []),
            metadata=record.get('metadata', {}),
            captured_at=record.get('captured_at', ''),
            review_notes=record.get('review_notes', ''),
            reviewed_at=record.get('reviewed_at'),
            reviewed_by=record.get('reviewed_by'),
        )

    # ==================== ACCIONES DE REVISIÓN ====================

    def approve_item(
        self,
        item_id: str,
        reviewer: str = "admin",
        notes: str = ""
    ) -> Tuple[bool, str]:
        """
        Aprueba un item para entrenamiento.

        Args:
            item_id: ID del item
            reviewer: Nombre del revisor
            notes: Notas de revisión

        Returns:
            Tupla (éxito, mensaje)
        """
        filepath = self.processed_dir / f"{item_id}.json"

        if not filepath.exists():
            return False, f"Item {item_id} no encontrado"

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                record = json.load(f)

            # Actualizar estado
            record['status'] = 'approved'
            record['reviewed_at'] = datetime.now().isoformat()
            record['reviewed_by'] = reviewer
            record['review_notes'] = notes

            # Mover a directorio de aprobados
            dest_path = self.approved_dir / filepath.name
            with open(dest_path, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            # Eliminar del directorio original
            filepath.unlink()

            self._stats['approved'] += 1
            self._stats['total_reviewed'] += 1

            logger.info(f"✅ Item {item_id} aprobado por {reviewer}")
            return True, f"Item {item_id} aprobado exitosamente"

        except Exception as e:
            logger.error(f"❌ Error aprobando item {item_id}: {str(e)}")
            return False, str(e)

    def reject_item(
        self,
        item_id: str,
        reviewer: str = "admin",
        reason: str = ""
    ) -> Tuple[bool, str]:
        """
        Rechaza un item para entrenamiento.

        Args:
            item_id: ID del item
            reviewer: Nombre del revisor
            reason: Razón del rechazo

        Returns:
            Tupla (éxito, mensaje)
        """
        filepath = self.processed_dir / f"{item_id}.json"

        if not filepath.exists():
            return False, f"Item {item_id} no encontrado"

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                record = json.load(f)

            # Actualizar estado
            record['status'] = 'rejected'
            record['reviewed_at'] = datetime.now().isoformat()
            record['reviewed_by'] = reviewer
            record['rejection_reason'] = reason

            # Mover a directorio de rechazados
            dest_path = self.rejected_dir / filepath.name
            with open(dest_path, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            # Eliminar del directorio original
            filepath.unlink()

            self._stats['rejected'] += 1
            self._stats['total_reviewed'] += 1

            logger.info(f"❌ Item {item_id} rechazado por {reviewer}: {reason}")
            return True, f"Item {item_id} rechazado"

        except Exception as e:
            logger.error(f"❌ Error rechazando item {item_id}: {str(e)}")
            return False, str(e)

    def edit_item(
        self,
        item_id: str,
        new_content: Optional[str] = None,
        new_analysis: Optional[Dict] = None,
        reviewer: str = "admin"
    ) -> Tuple[bool, str]:
        """
        Edita un item antes de aprobarlo.

        Args:
            item_id: ID del item
            new_content: Nuevo contenido (opcional)
            new_analysis: Nuevo análisis (opcional)
            reviewer: Nombre del revisor

        Returns:
            Tupla (éxito, mensaje)
        """
        filepath = self.processed_dir / f"{item_id}.json"

        if not filepath.exists():
            return False, f"Item {item_id} no encontrado"

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                record = json.load(f)

            # Guardar versión original
            if 'original_content' not in record:
                record['original_content'] = record.get('content')
            if 'original_analysis' not in record:
                record['original_analysis'] = record.get('analysis')

            # Aplicar ediciones
            if new_content is not None:
                record['content'] = new_content

            if new_analysis is not None:
                record['analysis'] = new_analysis
                # Actualizar confianza si se proporciona
                if 'confidence' in new_analysis:
                    record['confidence'] = new_analysis['confidence']

            record['edited_at'] = datetime.now().isoformat()
            record['edited_by'] = reviewer

            # Guardar cambios
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            self._stats['edited'] += 1

            logger.info(f"✏️ Item {item_id} editado por {reviewer}")
            return True, f"Item {item_id} editado exitosamente"

        except Exception as e:
            logger.error(f"❌ Error editando item {item_id}: {str(e)}")
            return False, str(e)

    def reanalyze_item(
        self,
        item_id: str,
        openai_service=None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Re-analiza un item con OpenAI.

        Args:
            item_id: ID del item
            openai_service: Servicio de OpenAI (opcional, se crea si no se proporciona)

        Returns:
            Tupla (éxito, mensaje, nuevo_análisis)
        """
        filepath = self.processed_dir / f"{item_id}.json"

        if not filepath.exists():
            return False, f"Item {item_id} no encontrado", None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                record = json.load(f)

            content = record.get('content', '')

            if not content:
                return False, "El item no tiene contenido para analizar", None

            # Crear servicio de OpenAI si no se proporciona
            if openai_service is None:
                from app.services.openai_service import OpenAIService
                openai_service = OpenAIService()

            if not openai_service.is_available():
                return False, "Servicio OpenAI no disponible", None

            # Analizar
            new_analysis = openai_service.analyze_user_intent(content)

            # Guardar análisis anterior
            if 'previous_analyses' not in record:
                record['previous_analyses'] = []
            record['previous_analyses'].append({
                'analysis': record.get('analysis'),
                'confidence': record.get('confidence'),
                'timestamp': datetime.now().isoformat()
            })

            # Actualizar con nuevo análisis
            record['analysis'] = new_analysis
            record['confidence'] = new_analysis.get('confidence', 0)
            record['reanalyzed_at'] = datetime.now().isoformat()

            # Actualizar estado si la confianza ahora es suficiente
            if record['confidence'] >= 0.85:
                record['status'] = 'approved'
                logger.info(f"✅ Item {item_id} auto-aprobado tras re-análisis (confianza: {record['confidence']:.2f})")

            # Guardar cambios
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            self._stats['reanalyzed'] += 1

            logger.info(f"🔄 Item {item_id} re-analizado. Nueva confianza: {record['confidence']:.2f}")
            return True, f"Item re-analizado. Confianza: {record['confidence']:.2f}", new_analysis

        except Exception as e:
            logger.error(f"❌ Error re-analizando item {item_id}: {str(e)}")
            return False, str(e), None

    # ==================== ACCIONES EN LOTE ====================

    def approve_batch(
        self,
        item_ids: List[str],
        reviewer: str = "admin"
    ) -> Dict[str, Any]:
        """
        Aprueba múltiples items.

        Args:
            item_ids: Lista de IDs
            reviewer: Nombre del revisor

        Returns:
            Resultados del batch
        """
        results = {
            'total': len(item_ids),
            'approved': 0,
            'failed': 0,
            'errors': []
        }

        for item_id in item_ids:
            success, message = self.approve_item(item_id, reviewer)
            if success:
                results['approved'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({'id': item_id, 'error': message})

        return results

    def reject_batch(
        self,
        item_ids: List[str],
        reviewer: str = "admin",
        reason: str = "Rechazado en batch"
    ) -> Dict[str, Any]:
        """
        Rechaza múltiples items.

        Args:
            item_ids: Lista de IDs
            reviewer: Nombre del revisor
            reason: Razón del rechazo

        Returns:
            Resultados del batch
        """
        results = {
            'total': len(item_ids),
            'rejected': 0,
            'failed': 0,
            'errors': []
        }

        for item_id in item_ids:
            success, message = self.reject_item(item_id, reviewer, reason)
            if success:
                results['rejected'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({'id': item_id, 'error': message})

        return results

    def auto_approve_high_confidence(
        self,
        min_confidence: float = 0.90,
        reviewer: str = "auto"
    ) -> Dict[str, Any]:
        """
        Auto-aprueba items con alta confianza.

        Args:
            min_confidence: Confianza mínima para auto-aprobar
            reviewer: Nombre del revisor

        Returns:
            Resultados
        """
        items, _ = self.get_pending_reviews(limit=1000)

        high_confidence_ids = [
            item.id for item in items
            if item.confidence >= min_confidence
        ]

        if not high_confidence_ids:
            return {'total': 0, 'approved': 0, 'message': 'No hay items con confianza suficiente'}

        return self.approve_batch(high_confidence_ids, reviewer)

    # ==================== ESTADÍSTICAS ====================

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servicio de revisión."""
        # Contar items por estado
        pending_count = 0
        approved_count = 0
        rejected_count = 0

        # Contar en processed (needs_review)
        for filepath in self.processed_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    record = json.load(f)
                if record.get('status') == 'needs_review':
                    pending_count += 1
                elif record.get('status') == 'approved':
                    approved_count += 1
            except:
                pass

        # Contar en approved
        approved_count += len(list(self.approved_dir.glob("*.json")))

        # Contar en rejected
        rejected_count = len(list(self.rejected_dir.glob("*.json")))

        # Calcular distribución de confianza
        confidence_distribution = self._get_confidence_distribution()

        return {
            'pending_reviews': pending_count,
            'approved': approved_count,
            'rejected': rejected_count,
            'session_stats': self._stats.copy(),
            'confidence_distribution': confidence_distribution,
        }

    def _get_confidence_distribution(self) -> Dict[str, int]:
        """Obtiene distribución de confianza de items pendientes."""
        distribution = {
            'very_low_0_50': 0,    # 0-50%
            'low_50_70': 0,        # 50-70%
            'medium_70_85': 0,     # 70-85%
            'high_85_95': 0,       # 85-95%
            'very_high_95_100': 0, # 95-100%
        }

        for filepath in self.processed_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    record = json.load(f)

                if record.get('status') != 'needs_review':
                    continue

                conf = record.get('confidence', 0)

                if conf < 0.50:
                    distribution['very_low_0_50'] += 1
                elif conf < 0.70:
                    distribution['low_50_70'] += 1
                elif conf < 0.85:
                    distribution['medium_70_85'] += 1
                elif conf < 0.95:
                    distribution['high_85_95'] += 1
                else:
                    distribution['very_high_95_100'] += 1

            except:
                pass

        return distribution

    def get_review_summary(self) -> str:
        """Genera un resumen legible del estado de revisión."""
        stats = self.get_stats()

        lines = [
            "📊 RESUMEN DE REVISIÓN DE DATOS",
            "=" * 40,
            f"📋 Pendientes de revisión: {stats['pending_reviews']}",
            f"✅ Aprobados: {stats['approved']}",
            f"❌ Rechazados: {stats['rejected']}",
            "",
            "📈 Distribución de confianza (pendientes):",
        ]

        dist = stats['confidence_distribution']
        lines.append(f"   🔴 Muy baja (0-50%): {dist['very_low_0_50']}")
        lines.append(f"   🟠 Baja (50-70%): {dist['low_50_70']}")
        lines.append(f"   🟡 Media (70-85%): {dist['medium_70_85']}")
        lines.append(f"   🟢 Alta (85-95%): {dist['high_85_95']}")
        lines.append(f"   🔵 Muy alta (95-100%): {dist['very_high_95_100']}")

        return "\n".join(lines)


# ==================== SINGLETON ====================

_review_service: Optional[HumanReviewService] = None


def get_review_service(data_dir: str = "data") -> HumanReviewService:
    """
    Obtiene la instancia singleton del servicio de revisión.

    Args:
        data_dir: Directorio de datos

    Returns:
        Instancia de HumanReviewService
    """
    global _review_service
    if _review_service is None:
        _review_service = HumanReviewService(data_dir)
    return _review_service
