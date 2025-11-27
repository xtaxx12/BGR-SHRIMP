"""
Rutas de administración para el sistema RAG (Retrieval-Augmented Generation).

Endpoints:
- GET /rag/stats - Estadísticas del índice
- GET /rag/health - Estado del servicio
- POST /rag/index - Indexar un documento
- POST /rag/index/batch - Indexar múltiples documentos
- POST /rag/index/prices - Indexar precios desde Google Sheets
- POST /rag/index/faqs - Indexar FAQs
- POST /rag/query - Consultar documentos relevantes
- GET /rag/documents - Listar documentos indexados
- DELETE /rag/documents/{doc_id} - Eliminar documento
- DELETE /rag/clear - Limpiar todo el índice
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

rag_router = APIRouter(prefix="/rag", tags=["rag"])


# ==================== MODELOS ====================

class IndexDocumentRequest(BaseModel):
    """Modelo para indexar un documento."""
    content: str = Field(..., min_length=10, description="Contenido del documento")
    doc_type: str = Field(default="general", description="Tipo de documento")
    metadata: Optional[dict] = Field(default=None, description="Metadatos adicionales")
    doc_id: Optional[str] = Field(default=None, description="ID personalizado")


class BatchIndexRequest(BaseModel):
    """Modelo para indexar múltiples documentos."""
    documents: List[dict] = Field(..., min_items=1, description="Lista de documentos")


class FAQItem(BaseModel):
    """Modelo para una FAQ."""
    question: str = Field(..., min_length=5)
    answer: str = Field(..., min_length=10)
    category: Optional[str] = Field(default="general")


class IndexFAQsRequest(BaseModel):
    """Modelo para indexar FAQs."""
    faqs: List[FAQItem] = Field(..., min_items=1)


class QueryRequest(BaseModel):
    """Modelo para consulta RAG."""
    query: str = Field(..., min_length=3, description="Consulta del usuario")
    top_k: int = Field(default=3, ge=1, le=10, description="Número de resultados")
    doc_type: Optional[str] = Field(default=None, description="Filtrar por tipo")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)
    return_context: bool = Field(default=False, description="Retornar contexto formateado")


class IndexConversationRequest(BaseModel):
    """Modelo para indexar una conversación."""
    user_message: str = Field(..., min_length=5)
    assistant_response: str = Field(..., min_length=10)
    metadata: Optional[dict] = None


# ==================== ENDPOINTS ====================

@rag_router.get("/stats")
async def get_rag_stats():
    """
    Obtiene estadísticas del sistema RAG.

    Returns:
        Estadísticas completas del índice
    """
    try:
        rag = get_rag_service()
        stats = rag.get_stats()

        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.get("/health")
async def rag_health():
    """
    Verifica el estado del servicio RAG.

    Returns:
        Estado del servicio
    """
    try:
        rag = get_rag_service()
        stats = rag.get_stats()

        return {
            "status": "healthy" if rag.is_available() else "degraded",
            "api_available": rag.is_available(),
            "total_documents": stats['total_documents'],
            "documents_by_type": stats['documents_by_type'],
            "index_size_mb": round(stats['index_size_mb'], 2),
            "message": "Sistema RAG operativo" if rag.is_available() else "API key no configurada"
        }
    except Exception as e:
        logger.error(f"❌ Error en health check RAG: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@rag_router.post("/index")
async def index_document(request: IndexDocumentRequest):
    """
    Indexa un documento en el sistema RAG.

    Args:
        request: Datos del documento

    Returns:
        ID del documento indexado
    """
    try:
        rag = get_rag_service()

        if not rag.is_available():
            raise HTTPException(
                status_code=503,
                detail="Servicio RAG no disponible - API key no configurada"
            )

        doc_id = rag.index_document(
            content=request.content,
            doc_type=request.doc_type,
            metadata=request.metadata,
            doc_id=request.doc_id
        )

        if doc_id is None:
            raise HTTPException(status_code=500, detail="Error indexando documento")

        return {
            "success": True,
            "doc_id": doc_id,
            "message": "Documento indexado exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error indexando documento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/index/batch")
async def index_documents_batch(request: BatchIndexRequest):
    """
    Indexa múltiples documentos en batch.

    Args:
        request: Lista de documentos

    Returns:
        Lista de IDs indexados
    """
    try:
        rag = get_rag_service()

        if not rag.is_available():
            raise HTTPException(
                status_code=503,
                detail="Servicio RAG no disponible - API key no configurada"
            )

        indexed_ids = rag.index_documents_batch(request.documents)

        return {
            "success": True,
            "indexed_count": len(indexed_ids),
            "doc_ids": indexed_ids,
            "message": f"{len(indexed_ids)} documentos indexados"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en batch indexing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/index/prices")
async def index_prices():
    """
    Indexa precios desde Google Sheets.

    Returns:
        Número de documentos de precios indexados
    """
    try:
        rag = get_rag_service()

        if not rag.is_available():
            raise HTTPException(
                status_code=503,
                detail="Servicio RAG no disponible - API key no configurada"
            )

        # Importar servicio de Google Sheets
        from app.services.google_sheets import get_google_sheets_service

        gs_service = get_google_sheets_service()
        count = rag.index_prices_from_sheets(gs_service)

        return {
            "success": True,
            "indexed_count": count,
            "message": f"{count} documentos de precios indexados"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error indexando precios: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/index/faqs")
async def index_faqs(request: IndexFAQsRequest):
    """
    Indexa preguntas frecuentes.

    Args:
        request: Lista de FAQs

    Returns:
        Número de FAQs indexadas
    """
    try:
        rag = get_rag_service()

        if not rag.is_available():
            raise HTTPException(
                status_code=503,
                detail="Servicio RAG no disponible - API key no configurada"
            )

        faqs_data = [faq.model_dump() for faq in request.faqs]
        count = rag.index_faqs(faqs_data)

        return {
            "success": True,
            "indexed_count": count,
            "message": f"{count} FAQs indexadas"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error indexando FAQs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/index/conversation")
async def index_conversation(request: IndexConversationRequest):
    """
    Indexa una conversación exitosa como ejemplo.

    Args:
        request: Datos de la conversación

    Returns:
        ID del documento
    """
    try:
        rag = get_rag_service()

        if not rag.is_available():
            raise HTTPException(
                status_code=503,
                detail="Servicio RAG no disponible - API key no configurada"
            )

        doc_id = rag.index_conversation(
            user_message=request.user_message,
            assistant_response=request.assistant_response,
            metadata=request.metadata
        )

        if doc_id is None:
            raise HTTPException(status_code=500, detail="Error indexando conversación")

        return {
            "success": True,
            "doc_id": doc_id,
            "message": "Conversación indexada exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error indexando conversación: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/query")
async def query_rag(request: QueryRequest):
    """
    Consulta documentos relevantes en el índice RAG.

    Args:
        request: Parámetros de consulta

    Returns:
        Documentos relevantes con scores de similitud
    """
    try:
        rag = get_rag_service()

        if not rag.is_available():
            raise HTTPException(
                status_code=503,
                detail="Servicio RAG no disponible - API key no configurada"
            )

        # Recuperar documentos
        results = rag.retrieve(
            query=request.query,
            top_k=request.top_k,
            doc_type=request.doc_type,
            min_similarity=request.min_similarity
        )

        response = {
            "success": True,
            "query": request.query,
            "results_count": len(results),
            "results": results
        }

        # Agregar contexto formateado si se solicita
        if request.return_context:
            response["context"] = rag.retrieve_context(
                query=request.query,
                top_k=request.top_k
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en consulta RAG: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.get("/documents")
async def list_documents(
    doc_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Lista documentos indexados.

    Args:
        doc_type: Filtrar por tipo
        limit: Máximo de resultados
        offset: Offset para paginación

    Returns:
        Lista de documentos
    """
    try:
        rag = get_rag_service()

        # Filtrar documentos
        all_docs = list(rag.documents.values())

        if doc_type:
            all_docs = [d for d in all_docs if d.metadata.get('type') == doc_type]

        # Paginar
        total = len(all_docs)
        paginated = all_docs[offset:offset + limit]

        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "documents": [
                {
                    'id': doc.id,
                    'content': doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                    'type': doc.metadata.get('type', 'general'),
                    'metadata': doc.metadata,
                    'created_at': doc.created_at
                }
                for doc in paginated
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error listando documentos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    Elimina un documento del índice.

    Args:
        doc_id: ID del documento

    Returns:
        Confirmación de eliminación
    """
    try:
        rag = get_rag_service()

        if doc_id not in rag.documents:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        success = rag.delete_document(doc_id)

        if not success:
            raise HTTPException(status_code=500, detail="Error eliminando documento")

        return {
            "success": True,
            "doc_id": doc_id,
            "message": "Documento eliminado exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error eliminando documento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.delete("/clear")
async def clear_index():
    """
    Limpia todo el índice RAG.

    Returns:
        Confirmación de limpieza
    """
    try:
        rag = get_rag_service()
        rag.clear_index()

        return {
            "success": True,
            "message": "Índice RAG limpiado completamente"
        }
    except Exception as e:
        logger.error(f"❌ Error limpiando índice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
