"""
Rutas de administración para el sistema de entrenamiento.

Endpoints:
- GET /training/stats - Estadísticas del pipeline
- POST /training/process - Procesar cola ETL
- POST /training/export - Exportar datos para fine-tuning
- POST /training/consent/{user_id} - Establecer consentimiento
- GET /training/consent/{user_id} - Obtener consentimiento
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.session import session_manager
from app.services.training_pipeline import get_training_pipeline
from app.utils.anonymizer import get_anonymization_stats

logger = logging.getLogger(__name__)

training_router = APIRouter(prefix="/training", tags=["training"])


class ConsentRequest(BaseModel):
    """Modelo para solicitud de consentimiento."""
    consent: bool


class ProcessRequest(BaseModel):
    """Modelo para solicitud de procesamiento."""
    max_items: int = 100


class ExportRequest(BaseModel):
    """Modelo para solicitud de exportación."""
    min_confidence: float = 0.85
    train_split: float = 0.9


@training_router.get("/stats")
async def get_training_stats():
    """
    Obtiene estadísticas del sistema de entrenamiento.
    
    Returns:
        Estadísticas completas del pipeline y anonimización
    """
    try:
        pipeline = get_training_pipeline()
        pipeline_stats = pipeline.get_stats()
        anon_stats = get_anonymization_stats()
        
        # Contar sesiones con consentimiento
        total_sessions = len(session_manager.sessions)
        consented_sessions = sum(
            1 for s in session_manager.sessions.values()
            if s.get('consent_for_training')
        )
        
        return {
            "success": True,
            "pipeline": pipeline_stats,
            "anonymization": anon_stats,
            "sessions": {
                "total": total_sessions,
                "with_consent": consented_sessions,
                "consent_rate": f"{(consented_sessions/total_sessions*100):.1f}%" if total_sessions > 0 else "0%"
            }
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@training_router.post("/process")
async def process_training_queue(request: ProcessRequest):
    """
    Procesa la cola ETL de mensajes pendientes.
    
    Args:
        request: Configuración de procesamiento
        
    Returns:
        Resultados del procesamiento
    """
    try:
        # Importar servicios
        from app.services.openai_service import OpenAIService
        from app.services.quality_assurance import QualityAssuranceService
        
        pipeline = get_training_pipeline()
        openai_service = OpenAIService()
        qa_service = QualityAssuranceService()
        
        # Procesar cola
        results = pipeline.process_queue(
            openai_service=openai_service,
            qa_service=qa_service,
            max_items=request.max_items
        )
        
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        logger.error(f"❌ Error procesando cola: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@training_router.post("/export")
async def export_training_data(request: ExportRequest):
    """
    Exporta datos aprobados a formato JSONL para fine-tuning.
    
    Args:
        request: Configuración de exportación
        
    Returns:
        Estadísticas de exportación
    """
    try:
        pipeline = get_training_pipeline()
        train_count, valid_count = pipeline.export_for_finetune(
            min_confidence=request.min_confidence,
            train_split=request.train_split
        )
        
        return {
            "success": True,
            "train_examples": train_count,
            "valid_examples": valid_count,
            "total": train_count + valid_count,
            "files": {
                "train": "data/finetune/train.jsonl",
                "valid": "data/finetune/valid.jsonl"
            }
        }
    except Exception as e:
        logger.error(f"❌ Error exportando datos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@training_router.post("/consent/{user_id}")
async def set_training_consent(user_id: str, request: ConsentRequest):
    """
    Establece el consentimiento de un usuario para usar sus mensajes en entrenamiento.
    
    Args:
        user_id: ID del usuario
        request: Consentimiento
        
    Returns:
        Confirmación
    """
    try:
        session_manager.set_training_consent(user_id, request.consent)
        
        return {
            "success": True,
            "user_id": user_id,
            "consent": request.consent,
            "message": f"Consentimiento {'otorgado' if request.consent else 'revocado'} exitosamente"
        }
    except Exception as e:
        logger.error(f"❌ Error estableciendo consentimiento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@training_router.get("/consent/{user_id}")
async def get_training_consent(user_id: str):
    """
    Obtiene el consentimiento de un usuario.
    
    Args:
        user_id: ID del usuario
        
    Returns:
        Estado del consentimiento
    """
    try:
        consent = session_manager.get_training_consent(user_id)
        session = session_manager.get_session(user_id)
        
        return {
            "success": True,
            "user_id": user_id,
            "consent": consent,
            "consent_timestamp": session.get('consent_timestamp')
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo consentimiento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@training_router.get("/health")
async def training_health():
    """
    Verifica el estado del sistema de entrenamiento.
    
    Returns:
        Estado del sistema
    """
    try:
        pipeline = get_training_pipeline()
        stats = pipeline.get_stats()
        
        # Verificar directorios
        import os
        dirs_ok = all([
            os.path.exists("data/etl_queue"),
            os.path.exists("data/processed"),
            os.path.exists("data/rejected"),
            os.path.exists("data/finetune"),
        ])
        
        return {
            "status": "healthy" if dirs_ok else "degraded",
            "directories_ok": dirs_ok,
            "queue_size": stats.get('queue_size', 0),
            "processed_size": stats.get('processed_size', 0),
            "message": "Sistema de entrenamiento operativo" if dirs_ok else "Algunos directorios no existen"
        }
    except Exception as e:
        logger.error(f"❌ Error en health check: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
