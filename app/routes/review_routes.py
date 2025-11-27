"""
Rutas de administración para Revisión Humana de datos de entrenamiento.

Endpoints:
- GET /review/pending - Listar items pendientes de revisión
- GET /review/item/{item_id} - Obtener detalle de un item
- GET /review/stats - Estadísticas de revisión
- POST /review/approve/{item_id} - Aprobar un item
- POST /review/reject/{item_id} - Rechazar un item
- POST /review/edit/{item_id} - Editar un item
- POST /review/reanalyze/{item_id} - Re-analizar con OpenAI
- POST /review/batch/approve - Aprobar múltiples items
- POST /review/batch/reject - Rechazar múltiples items
- POST /review/auto-approve - Auto-aprobar items con alta confianza
"""
import logging
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.services.human_review import get_review_service

logger = logging.getLogger(__name__)

review_router = APIRouter(prefix="/review", tags=["review"])


# ==================== DASHBOARD WEB ====================

@review_router.get("/dashboard", response_class=HTMLResponse)
async def review_dashboard():
    """
    Dashboard web para revisión de mensajes.
    
    Returns:
        Página HTML con interfaz de revisión
    """
    try:
        template_path = Path("app/templates/review_dashboard.html")
        
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Template no encontrado")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"❌ Error cargando dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MODELOS ====================

class ApproveRequest(BaseModel):
    """Modelo para aprobar un item."""
    reviewer: str = Field(default="admin", description="Nombre del revisor")
    notes: str = Field(default="", description="Notas de aprobación")


class RejectRequest(BaseModel):
    """Modelo para rechazar un item."""
    reviewer: str = Field(default="admin", description="Nombre del revisor")
    reason: str = Field(default="", description="Razón del rechazo")


class EditRequest(BaseModel):
    """Modelo para editar un item."""
    reviewer: str = Field(default="admin", description="Nombre del revisor")
    new_content: Optional[str] = Field(default=None, description="Nuevo contenido")
    new_analysis: Optional[dict] = Field(default=None, description="Nuevo análisis")


class BatchApproveRequest(BaseModel):
    """Modelo para aprobar múltiples items."""
    item_ids: List[str] = Field(..., min_items=1, description="Lista de IDs")
    reviewer: str = Field(default="admin", description="Nombre del revisor")


class BatchRejectRequest(BaseModel):
    """Modelo para rechazar múltiples items."""
    item_ids: List[str] = Field(..., min_items=1, description="Lista de IDs")
    reviewer: str = Field(default="admin", description="Nombre del revisor")
    reason: str = Field(default="Rechazado en batch", description="Razón del rechazo")


class AutoApproveRequest(BaseModel):
    """Modelo para auto-aprobar items."""
    min_confidence: float = Field(default=0.90, ge=0.5, le=1.0, description="Confianza mínima")
    reviewer: str = Field(default="auto", description="Nombre del revisor")


# ==================== ENDPOINTS ====================

@review_router.get("/pending")
async def get_pending_reviews(
    limit: int = Query(default=50, ge=1, le=200, description="Máximo de items"),
    offset: int = Query(default=0, ge=0, description="Offset para paginación"),
    sort_by: str = Query(default="captured_at", description="Campo para ordenar"),
    sort_desc: bool = Query(default=True, description="Orden descendente")
):
    """
    Lista items pendientes de revisión.

    Returns:
        Lista paginada de items con status='needs_review'
    """
    try:
        # 🆕 Usar el nuevo sistema de captura con base de datos
        from app.services.training_capture_db import get_capture_service
        
        capture = get_capture_service()
        items, total = capture.get_pending_reviews(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc
        )

        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items
        }
    except Exception as e:
        logger.error(f"❌ Error listando items pendientes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.get("/messages")
async def get_all_messages(
    status: str = Query(default="all", description="Filtrar por status (all, needs_review, approved, rejected)"),
    limit: int = Query(default=100, ge=1, le=500, description="Máximo de items"),
    offset: int = Query(default=0, ge=0, description="Offset para paginación"),
    sort_by: str = Query(default="captured_at", description="Campo para ordenar"),
    sort_desc: bool = Query(default=True, description="Orden descendente")
):
    """
    Lista todos los mensajes con filtros opcionales.

    Returns:
        Lista paginada de mensajes
    """
    try:
        from app.services.training_capture_db import get_capture_service
        
        capture = get_capture_service()
        
        # Obtener mensajes según el filtro
        if status == "all":
            messages, total = capture.get_all_messages(
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_desc=sort_desc
            )
        else:
            messages, total = capture.get_messages_by_status(
                status=status,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_desc=sort_desc
            )

        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "status_filter": status,
            "items": messages
        }
    except Exception as e:
        logger.error(f"❌ Error listando mensajes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.get("/item/{item_id}")
async def get_review_item(item_id: str):
    """
    Obtiene detalle de un item específico.

    Args:
        item_id: ID del item

    Returns:
        Detalle completo del item
    """
    try:
        review = get_review_service()
        item = review.get_review_item(item_id)

        if item is None:
            raise HTTPException(status_code=404, detail=f"Item {item_id} no encontrado")

        return {
            "success": True,
            "item": item.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.get("/stats")
async def get_review_stats():
    """
    Obtiene estadísticas de revisión.

    Returns:
        Estadísticas completas del sistema de revisión
    """
    try:
        # 🆕 Usar el nuevo sistema de captura con base de datos
        from app.services.training_capture_db import get_capture_service
        
        capture = get_capture_service()
        stats = capture.get_stats()
        
        # Crear resumen
        summary = f"""📊 RESUMEN DE REVISIÓN DE DATOS
========================================
📋 Pendientes de revisión: {stats['by_status'].get('needs_review', 0)}
✅ Aprobados: {stats['by_status'].get('approved', 0)}
❌ Rechazados: {stats['by_status'].get('rejected', 0)}
📊 Total de mensajes: {stats['total_messages']}

👤 Por rol:
   Usuario: {stats['by_role'].get('user', 0)}
   Asistente: {stats['by_role'].get('assistant', 0)}
"""

        return {
            "success": True,
            "stats": {
                "pending_reviews": stats['by_status'].get('needs_review', 0),
                "approved": stats['by_status'].get('approved', 0),
                "rejected": stats['by_status'].get('rejected', 0),
                "total_messages": stats['total_messages'],
                "by_status": stats['by_status'],
                "by_role": stats['by_role']
            },
            "summary": summary
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/approve/{item_id}")
async def approve_item(item_id: str, request: ApproveRequest):
    """
    Aprueba un item para entrenamiento.

    Args:
        item_id: ID del item
        request: Datos de aprobación

    Returns:
        Confirmación de aprobación
    """
    try:
        # 🆕 Usar el nuevo sistema de captura con base de datos
        from app.services.training_capture_db import get_capture_service
        
        capture = get_capture_service()
        success, message = capture.approve_message(
            message_id=int(item_id),
            reviewer=request.reviewer,
            notes=request.notes
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "item_id": item_id,
            "status": "approved",
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error aprobando item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/reject/{item_id}")
async def reject_item(item_id: str, request: RejectRequest):
    """
    Rechaza un item para entrenamiento.

    Args:
        item_id: ID del item
        request: Datos de rechazo

    Returns:
        Confirmación de rechazo
    """
    try:
        # 🆕 Usar el nuevo sistema de captura con base de datos
        from app.services.training_capture_db import get_capture_service
        
        capture = get_capture_service()
        success, message = capture.reject_message(
            message_id=int(item_id),
            reviewer=request.reviewer,
            reason=request.reason
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "item_id": item_id,
            "status": "rejected",
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error rechazando item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/edit/{item_id}")
async def edit_item(item_id: str, request: EditRequest):
    """
    Edita un item antes de aprobarlo.

    Args:
        item_id: ID del item
        request: Datos de edición

    Returns:
        Confirmación de edición
    """
    try:
        review = get_review_service()
        success, message = review.edit_item(
            item_id=item_id,
            new_content=request.new_content,
            new_analysis=request.new_analysis,
            reviewer=request.reviewer
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Obtener item actualizado
        updated_item = review.get_review_item(item_id)

        return {
            "success": True,
            "item_id": item_id,
            "message": message,
            "item": updated_item.to_dict() if updated_item else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error editando item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/reanalyze/{item_id}")
async def reanalyze_item(item_id: str):
    """
    Re-analiza un item con OpenAI.

    Args:
        item_id: ID del item

    Returns:
        Nuevo análisis y estado actualizado
    """
    try:
        review = get_review_service()

        # Importar servicio de OpenAI
        from app.services.openai_service import OpenAIService
        openai_service = OpenAIService()

        success, message, new_analysis = review.reanalyze_item(
            item_id=item_id,
            openai_service=openai_service
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Obtener item actualizado
        updated_item = review.get_review_item(item_id)

        return {
            "success": True,
            "item_id": item_id,
            "message": message,
            "new_analysis": new_analysis,
            "item": updated_item.to_dict() if updated_item else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error re-analizando item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/batch/approve")
async def batch_approve(request: BatchApproveRequest):
    """
    Aprueba múltiples items en batch.

    Args:
        request: Lista de IDs y datos de aprobación

    Returns:
        Resultados del batch
    """
    try:
        review = get_review_service()
        results = review.approve_batch(
            item_ids=request.item_ids,
            reviewer=request.reviewer
        )

        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        logger.error(f"❌ Error en batch approve: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/batch/reject")
async def batch_reject(request: BatchRejectRequest):
    """
    Rechaza múltiples items en batch.

    Args:
        request: Lista de IDs y datos de rechazo

    Returns:
        Resultados del batch
    """
    try:
        review = get_review_service()
        results = review.reject_batch(
            item_ids=request.item_ids,
            reviewer=request.reviewer,
            reason=request.reason
        )

        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        logger.error(f"❌ Error en batch reject: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/auto-approve")
async def auto_approve(request: AutoApproveRequest):
    """
    Auto-aprueba items con alta confianza.

    Args:
        request: Configuración de auto-aprobación

    Returns:
        Resultados de auto-aprobación
    """
    try:
        review = get_review_service()
        results = review.auto_approve_high_confidence(
            min_confidence=request.min_confidence,
            reviewer=request.reviewer
        )

        return {
            "success": True,
            "min_confidence": request.min_confidence,
            "results": results
        }
    except Exception as e:
        logger.error(f"❌ Error en auto-approve: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.get("/summary")
async def get_review_summary():
    """
    Obtiene un resumen legible del estado de revisión.

    Returns:
        Resumen en texto formateado
    """
    try:
        review = get_review_service()
        summary = review.get_review_summary()

        return {
            "success": True,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo resumen: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/export")
async def export_training_data():
    """
    Exporta mensajes aprobados a formato JSONL para fine-tuning.
    
    Returns:
        Información sobre la exportación
    """
    try:
        from app.services.training_capture_db import get_capture_service
        
        capture = get_capture_service()
        output_path = "data/finetune/train.jsonl"
        
        num_pairs = capture.export_for_finetune(output_path)
        
        if num_pairs == 0:
            return {
                "success": False,
                "message": "No hay mensajes aprobados para exportar",
                "num_pairs": 0
            }
        
        return {
            "success": True,
            "message": f"Exportados {num_pairs} pares de entrenamiento",
            "num_pairs": num_pairs,
            "output_path": output_path
        }
    except Exception as e:
        logger.error(f"❌ Error exportando datos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/upload-to-openai")
async def upload_to_openai():
    """
    Sube el archivo de entrenamiento a OpenAI para fine-tuning.
    
    Returns:
        Información sobre la subida y el file ID
    """
    try:
        import os
        import openai
        from pathlib import Path
        
        # Verificar API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="OPENAI_API_KEY no configurada en variables de entorno"
            )
        
        # Verificar que existe el archivo
        file_path = Path("data/finetune/train.jsonl")
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="No hay archivo de entrenamiento. Primero exporta los datos."
            )
        
        # Contar ejemplos
        with open(file_path, 'r', encoding='utf-8') as f:
            num_examples = len(f.readlines())
        
        if num_examples < 10:
            return {
                "success": False,
                "message": f"Solo tienes {num_examples} ejemplos. OpenAI recomienda al menos 10 para fine-tuning efectivo.",
                "num_examples": num_examples,
                "can_upload": False
            }
        
        # Configurar OpenAI
        openai.api_key = api_key
        
        # Subir archivo
        logger.info(f"📤 Subiendo archivo a OpenAI: {file_path}")
        
        with open(file_path, 'rb') as f:
            response = openai.files.create(
                file=f,
                purpose='fine-tune'
            )
        
        file_id = response.id
        file_status = response.status
        
        logger.info(f"✅ Archivo subido exitosamente: {file_id}")
        
        return {
            "success": True,
            "message": f"Archivo subido exitosamente a OpenAI",
            "file_id": file_id,
            "status": file_status,
            "num_examples": num_examples,
            "next_steps": f"Ahora puedes crear un fine-tuning job con: openai api fine_tuning.jobs.create -t {file_id} -m gpt-3.5-turbo"
        }
        
    except openai.OpenAIError as e:
        logger.error(f"❌ Error de OpenAI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error de OpenAI: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error subiendo a OpenAI: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.post("/create-finetuning-job")
async def create_finetuning_job(file_id: str = None):
    """
    Crea un job de fine-tuning en OpenAI.
    
    Args:
        file_id: ID del archivo subido a OpenAI
        
    Returns:
        Información sobre el job creado
    """
    try:
        import os
        import openai
        
        # Verificar API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="OPENAI_API_KEY no configurada"
            )
        
        if not file_id:
            raise HTTPException(
                status_code=400,
                detail="Se requiere file_id. Primero sube el archivo a OpenAI."
            )
        
        # Configurar OpenAI
        openai.api_key = api_key
        
        # Crear job de fine-tuning
        logger.info(f"🚀 Creando job de fine-tuning con archivo {file_id}")
        
        job = openai.fine_tuning.jobs.create(
            training_file=file_id,
            model="gpt-3.5-turbo"
        )
        
        job_id = job.id
        job_status = job.status
        
        logger.info(f"✅ Job de fine-tuning creado: {job_id}")
        
        return {
            "success": True,
            "message": "Job de fine-tuning creado exitosamente",
            "job_id": job_id,
            "status": job_status,
            "model": "gpt-3.5-turbo",
            "next_steps": "El entrenamiento tomará entre 10-30 minutos. Puedes monitorear el progreso en el dashboard de OpenAI."
        }
        
    except openai.OpenAIError as e:
        logger.error(f"❌ Error de OpenAI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error de OpenAI: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error creando job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@review_router.get("/debug/filesystem")
async def debug_filesystem():
    """
    Endpoint de debug para verificar el estado del filesystem.
    
    Returns:
        Información sobre directorios y archivos
    """
    try:
        from pathlib import Path
        import os
        
        data_dir = Path("data")
        
        info = {
            "data_dir_exists": data_dir.exists(),
            "data_dir_path": str(data_dir.absolute()),
            "subdirectories": {},
            "total_files": 0,
        }
        
        # Verificar subdirectorios
        subdirs = ["etl_queue", "processed", "rejected", "approved"]
        for subdir in subdirs:
            subdir_path = data_dir / subdir
            if subdir_path.exists():
                files = list(subdir_path.glob("*.json"))
                info["subdirectories"][subdir] = {
                    "exists": True,
                    "path": str(subdir_path.absolute()),
                    "file_count": len(files),
                    "files": [f.name for f in files[:10]]  # Primeros 10
                }
                info["total_files"] += len(files)
            else:
                info["subdirectories"][subdir] = {
                    "exists": False,
                    "path": str(subdir_path.absolute())
                }
        
        # Verificar permisos de escritura
        try:
            test_file = data_dir / "test_write.txt"
            test_file.write_text("test")
            test_file.unlink()
            info["writable"] = True
        except Exception as e:
            info["writable"] = False
            info["write_error"] = str(e)
        
        return {
            "success": True,
            "filesystem_info": info
        }
    except Exception as e:
        logger.error(f"❌ Error en debug filesystem: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
