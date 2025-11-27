"""
Sistema RAG (Retrieval-Augmented Generation) para BGR Shrimp Bot.

Este módulo implementa:
1. Generación de embeddings con OpenAI (text-embedding-3-small)
2. Vector store local con FAISS para búsqueda semántica
3. Indexación de documentos (precios, FAQs, conversaciones)
4. Recuperación de contexto relevante para consultas

Uso:
    from app.services.rag_service import get_rag_service

    rag = get_rag_service()
    rag.index_document("Información sobre precios de camarón HLSO...")
    context = rag.retrieve("¿Cuál es el precio del HLSO 16/20?")
"""
import json
import logging
import os
import pickle
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

import requests
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Representa un documento indexado en el sistema RAG."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """Convierte el documento a diccionario."""
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at,
        }


class RAGService:
    """
    Servicio RAG para mejorar respuestas con contexto relevante.

    Características:
    - Embeddings con OpenAI text-embedding-3-small
    - Vector store en memoria con persistencia a disco
    - Búsqueda por similitud coseno
    - Indexación de múltiples tipos de documentos
    """

    # Configuración
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    DEFAULT_TOP_K = 3
    MIN_SIMILARITY_THRESHOLD = 0.7

    # Tipos de documentos soportados
    DOC_TYPES = ['price', 'faq', 'conversation', 'product', 'policy', 'general']

    def __init__(self, data_dir: str = "data/rag"):
        """
        Inicializa el servicio RAG.

        Args:
            data_dir: Directorio para almacenar índices y documentos
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"

        # Directorios
        self.data_dir = Path(data_dir)
        self.index_dir = self.data_dir / "index"
        self.docs_dir = self.data_dir / "documents"

        # Crear directorios
        for dir_path in [self.data_dir, self.index_dir, self.docs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Vector store en memoria
        self.documents: Dict[str, Document] = {}
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.doc_ids: List[str] = []

        # Estadísticas
        self._stats = {
            'documents_indexed': 0,
            'queries_processed': 0,
            'embeddings_generated': 0,
            'cache_hits': 0,
            'avg_retrieval_time_ms': 0,
        }

        # Caché de embeddings
        self._embedding_cache: Dict[str, List[float]] = {}

        # Cargar índice existente
        self._load_index()

        logger.info(f"🔍 RAG Service inicializado con {len(self.documents)} documentos")

    def is_available(self) -> bool:
        """Verifica si el servicio está disponible."""
        return bool(self.api_key)

    # ==================== EMBEDDINGS ====================

    def _generate_embedding(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        """
        Genera embedding para un texto usando OpenAI.

        Args:
            text: Texto para generar embedding
            use_cache: Si usar caché de embeddings

        Returns:
            Lista de floats representando el embedding
        """
        if not self.api_key:
            logger.warning("⚠️ API key de OpenAI no configurada")
            return None

        # Normalizar texto
        text = text.strip()[:8000]  # Límite de tokens

        # Verificar caché
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if use_cache and cache_key in self._embedding_cache:
            self._stats['cache_hits'] += 1
            return self._embedding_cache[cache_key]

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.EMBEDDING_MODEL,
                "input": text,
            }

            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                embedding = data['data'][0]['embedding']

                # Guardar en caché
                self._embedding_cache[cache_key] = embedding
                self._stats['embeddings_generated'] += 1

                return embedding
            else:
                logger.error(f"❌ Error generando embedding: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Error en API de embeddings: {str(e)}")
            return None

    def _batch_generate_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Genera embeddings para múltiples textos en batch.

        Args:
            texts: Lista de textos

        Returns:
            Lista de embeddings
        """
        if not self.api_key or not texts:
            return [None] * len(texts)

        try:
            # Normalizar textos
            normalized_texts = [t.strip()[:8000] for t in texts]

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.EMBEDDING_MODEL,
                "input": normalized_texts,
            }

            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                embeddings = [item['embedding'] for item in data['data']]
                self._stats['embeddings_generated'] += len(embeddings)
                return embeddings
            else:
                logger.error(f"❌ Error en batch embeddings: {response.status_code}")
                return [None] * len(texts)

        except Exception as e:
            logger.error(f"❌ Error en batch embeddings: {str(e)}")
            return [None] * len(texts)

    # ==================== INDEXACIÓN ====================

    def index_document(
        self,
        content: str,
        doc_type: str = "general",
        metadata: Optional[Dict] = None,
        doc_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Indexa un documento en el vector store.

        Args:
            content: Contenido del documento
            doc_type: Tipo de documento (price, faq, conversation, etc.)
            metadata: Metadatos adicionales
            doc_id: ID personalizado (se genera automáticamente si no se proporciona)

        Returns:
            ID del documento indexado o None si falla
        """
        if not content or not content.strip():
            logger.warning("⚠️ Contenido vacío, no se indexa")
            return None

        # Generar ID
        if not doc_id:
            doc_id = hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:16]

        # Generar embedding
        embedding = self._generate_embedding(content)
        if embedding is None:
            logger.error(f"❌ No se pudo generar embedding para documento {doc_id}")
            return None

        # Crear documento
        doc = Document(
            id=doc_id,
            content=content,
            metadata={
                'type': doc_type,
                **(metadata or {})
            },
            embedding=embedding
        )

        # Agregar al store
        self.documents[doc_id] = doc
        self._rebuild_matrix()
        self._stats['documents_indexed'] += 1

        # Persistir
        self._save_index()

        logger.info(f"📄 Documento indexado: {doc_id} (tipo: {doc_type})")
        return doc_id

    def index_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Indexa múltiples documentos en batch (más eficiente).

        Args:
            documents: Lista de dicts con 'content', 'type', 'metadata'

        Returns:
            Lista de IDs de documentos indexados
        """
        if not documents:
            return []

        # Extraer contenidos
        contents = [d.get('content', '') for d in documents]

        # Generar embeddings en batch
        embeddings = self._batch_generate_embeddings(contents)

        indexed_ids = []

        for i, doc_data in enumerate(documents):
            if embeddings[i] is None:
                continue

            doc_id = hashlib.md5(f"{doc_data.get('content', '')}{time.time()}{i}".encode()).hexdigest()[:16]

            doc = Document(
                id=doc_id,
                content=doc_data.get('content', ''),
                metadata={
                    'type': doc_data.get('type', 'general'),
                    **(doc_data.get('metadata') or {})
                },
                embedding=embeddings[i]
            )

            self.documents[doc_id] = doc
            indexed_ids.append(doc_id)

        # Reconstruir matriz y guardar
        self._rebuild_matrix()
        self._save_index()
        self._stats['documents_indexed'] += len(indexed_ids)

        logger.info(f"📚 Batch indexado: {len(indexed_ids)} documentos")
        return indexed_ids

    def delete_document(self, doc_id: str) -> bool:
        """
        Elimina un documento del índice.

        Args:
            doc_id: ID del documento

        Returns:
            True si se eliminó exitosamente
        """
        if doc_id not in self.documents:
            return False

        del self.documents[doc_id]
        self._rebuild_matrix()
        self._save_index()

        logger.info(f"🗑️ Documento eliminado: {doc_id}")
        return True

    # ==================== BÚSQUEDA ====================

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        doc_type: Optional[str] = None,
        min_similarity: float = None
    ) -> List[Dict]:
        """
        Recupera documentos relevantes para una consulta.

        Args:
            query: Consulta del usuario
            top_k: Número de documentos a recuperar
            doc_type: Filtrar por tipo de documento
            min_similarity: Umbral mínimo de similitud

        Returns:
            Lista de documentos relevantes con scores
        """
        start_time = time.time()

        top_k = top_k or self.DEFAULT_TOP_K
        min_similarity = min_similarity or self.MIN_SIMILARITY_THRESHOLD

        if not self.documents:
            logger.warning("⚠️ No hay documentos indexados")
            return []

        # Generar embedding de la consulta
        query_embedding = self._generate_embedding(query)
        if query_embedding is None:
            logger.error("❌ No se pudo generar embedding para la consulta")
            return []

        # Calcular similitudes
        query_vector = np.array(query_embedding)
        similarities = self._cosine_similarity(query_vector, self.embeddings_matrix)

        # Ordenar por similitud
        sorted_indices = np.argsort(similarities)[::-1]

        results = []
        for idx in sorted_indices:
            if len(results) >= top_k:
                break

            doc_id = self.doc_ids[idx]
            doc = self.documents[doc_id]
            similarity = float(similarities[idx])

            # Filtrar por similitud mínima
            if similarity < min_similarity:
                continue

            # Filtrar por tipo si se especifica
            if doc_type and doc.metadata.get('type') != doc_type:
                continue

            results.append({
                'id': doc_id,
                'content': doc.content,
                'metadata': doc.metadata,
                'similarity': similarity,
            })

        # Actualizar estadísticas
        elapsed_ms = (time.time() - start_time) * 1000
        self._stats['queries_processed'] += 1
        self._stats['avg_retrieval_time_ms'] = (
            (self._stats['avg_retrieval_time_ms'] * (self._stats['queries_processed'] - 1) + elapsed_ms)
            / self._stats['queries_processed']
        )

        logger.info(f"🔍 Recuperados {len(results)} documentos en {elapsed_ms:.1f}ms")
        return results

    def retrieve_context(
        self,
        query: str,
        top_k: int = 3,
        max_tokens: int = 2000
    ) -> str:
        """
        Recupera contexto formateado para incluir en prompts de LLM.

        Args:
            query: Consulta del usuario
            top_k: Número de documentos a recuperar
            max_tokens: Límite aproximado de tokens (caracteres / 4)

        Returns:
            Contexto formateado como string
        """
        results = self.retrieve(query, top_k=top_k)

        if not results:
            return ""

        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Aproximación de tokens

        for i, result in enumerate(results, 1):
            content = result['content']
            doc_type = result['metadata'].get('type', 'general')

            # Verificar límite de caracteres
            if total_chars + len(content) > max_chars:
                # Truncar si es necesario
                remaining = max_chars - total_chars
                if remaining > 100:
                    content = content[:remaining] + "..."
                else:
                    break

            context_parts.append(f"[{doc_type.upper()}] {content}")
            total_chars += len(content)

        return "\n\n".join(context_parts)

    # ==================== UTILIDADES ====================

    def _cosine_similarity(self, query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        """Calcula similitud coseno entre query y matriz de embeddings."""
        # Normalizar
        query_norm = query / (np.linalg.norm(query) + 1e-10)
        matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
        matrix_normalized = matrix / matrix_norms

        # Producto punto = similitud coseno (vectores normalizados)
        similarities = np.dot(matrix_normalized, query_norm)
        return similarities

    def _rebuild_matrix(self):
        """Reconstruye la matriz de embeddings desde los documentos."""
        if not self.documents:
            self.embeddings_matrix = None
            self.doc_ids = []
            return

        self.doc_ids = list(self.documents.keys())
        embeddings = [self.documents[doc_id].embedding for doc_id in self.doc_ids]
        self.embeddings_matrix = np.array(embeddings)

    def _save_index(self):
        """Guarda el índice a disco."""
        try:
            # Guardar documentos (sin embeddings para JSON legible)
            docs_path = self.docs_dir / "documents.json"
            docs_data = {
                doc_id: doc.to_dict()
                for doc_id, doc in self.documents.items()
            }
            with open(docs_path, 'w', encoding='utf-8') as f:
                json.dump(docs_data, f, ensure_ascii=False, indent=2)

            # Guardar embeddings en formato binario
            if self.embeddings_matrix is not None:
                embeddings_path = self.index_dir / "embeddings.pkl"
                with open(embeddings_path, 'wb') as f:
                    pickle.dump({
                        'matrix': self.embeddings_matrix,
                        'doc_ids': self.doc_ids,
                        'embeddings': {
                            doc_id: self.documents[doc_id].embedding
                            for doc_id in self.doc_ids
                        }
                    }, f)

            logger.debug(f"💾 Índice guardado: {len(self.documents)} documentos")

        except Exception as e:
            logger.error(f"❌ Error guardando índice: {str(e)}")

    def _load_index(self):
        """Carga el índice desde disco."""
        try:
            docs_path = self.docs_dir / "documents.json"
            embeddings_path = self.index_dir / "embeddings.pkl"

            if not docs_path.exists():
                logger.info("📂 No hay índice previo, iniciando vacío")
                return

            # Cargar documentos
            with open(docs_path, 'r', encoding='utf-8') as f:
                docs_data = json.load(f)

            # Cargar embeddings
            embeddings_data = {}
            if embeddings_path.exists():
                with open(embeddings_path, 'rb') as f:
                    embeddings_data = pickle.load(f)

            # Reconstruir documentos
            for doc_id, doc_dict in docs_data.items():
                embedding = embeddings_data.get('embeddings', {}).get(doc_id)
                self.documents[doc_id] = Document(
                    id=doc_id,
                    content=doc_dict['content'],
                    metadata=doc_dict.get('metadata', {}),
                    embedding=embedding,
                    created_at=doc_dict.get('created_at', datetime.now().isoformat())
                )

            # Reconstruir matriz
            self._rebuild_matrix()

            logger.info(f"📂 Índice cargado: {len(self.documents)} documentos")

        except Exception as e:
            logger.error(f"❌ Error cargando índice: {str(e)}")

    # ==================== INDEXACIÓN DE FUENTES ESPECÍFICAS ====================

    def index_prices_from_sheets(self, google_sheets_service) -> int:
        """
        Indexa información de precios desde Google Sheets.

        Args:
            google_sheets_service: Instancia de GoogleSheetsService

        Returns:
            Número de documentos indexados
        """
        if not google_sheets_service or not google_sheets_service.prices_data:
            logger.warning("⚠️ No hay datos de precios disponibles")
            return 0

        documents = []

        for product, sizes in google_sheets_service.prices_data.items():
            for size, price_info in sizes.items():
                # Crear documento descriptivo
                content = f"""
Producto: {product}
Talla: {size}
Precio base FOB: ${price_info.get('precio_fob', 'N/A')}/kg
Precio con glaseo estándar: ${price_info.get('precio_glaseo', 'N/A')}/kg
Factor de conversión: {price_info.get('factor', 'N/A')}
Disponibilidad: {price_info.get('disponibilidad', 'Disponible')}
                """.strip()

                documents.append({
                    'content': content,
                    'type': 'price',
                    'metadata': {
                        'product': product,
                        'size': size,
                        'price_fob': price_info.get('precio_fob'),
                        'source': 'google_sheets'
                    }
                })

        indexed_ids = self.index_documents_batch(documents)
        logger.info(f"💰 Indexados {len(indexed_ids)} documentos de precios")
        return len(indexed_ids)

    def index_faqs(self, faqs: List[Dict[str, str]]) -> int:
        """
        Indexa preguntas frecuentes.

        Args:
            faqs: Lista de dicts con 'question' y 'answer'

        Returns:
            Número de FAQs indexadas
        """
        documents = []

        for faq in faqs:
            content = f"""
Pregunta: {faq.get('question', '')}
Respuesta: {faq.get('answer', '')}
            """.strip()

            documents.append({
                'content': content,
                'type': 'faq',
                'metadata': {
                    'question': faq.get('question'),
                    'category': faq.get('category', 'general')
                }
            })

        indexed_ids = self.index_documents_batch(documents)
        logger.info(f"❓ Indexadas {len(indexed_ids)} FAQs")
        return len(indexed_ids)

    def index_conversation(
        self,
        user_message: str,
        assistant_response: str,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Indexa una conversación exitosa como ejemplo.

        Args:
            user_message: Mensaje del usuario
            assistant_response: Respuesta del asistente
            metadata: Metadatos adicionales

        Returns:
            ID del documento o None
        """
        content = f"""
Usuario: {user_message}
Asistente: {assistant_response}
        """.strip()

        return self.index_document(
            content=content,
            doc_type='conversation',
            metadata={
                'user_message_length': len(user_message),
                'response_length': len(assistant_response),
                **(metadata or {})
            }
        )

    # ==================== ESTADÍSTICAS ====================

    def get_stats(self) -> Dict:
        """Obtiene estadísticas del servicio RAG."""
        return {
            **self._stats,
            'total_documents': len(self.documents),
            'documents_by_type': self._count_by_type(),
            'index_size_mb': self._get_index_size_mb(),
            'embedding_cache_size': len(self._embedding_cache),
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Cuenta documentos por tipo."""
        counts = {}
        for doc in self.documents.values():
            doc_type = doc.metadata.get('type', 'general')
            counts[doc_type] = counts.get(doc_type, 0) + 1
        return counts

    def _get_index_size_mb(self) -> float:
        """Calcula el tamaño aproximado del índice en MB."""
        if self.embeddings_matrix is None:
            return 0.0
        return self.embeddings_matrix.nbytes / (1024 * 1024)

    def clear_index(self):
        """Limpia todo el índice."""
        self.documents = {}
        self.embeddings_matrix = None
        self.doc_ids = []
        self._embedding_cache = {}

        # Eliminar archivos
        for file_path in [
            self.docs_dir / "documents.json",
            self.index_dir / "embeddings.pkl"
        ]:
            if file_path.exists():
                file_path.unlink()

        logger.info("🗑️ Índice RAG limpiado")


# ==================== SINGLETON ====================

_rag_service: Optional[RAGService] = None


def get_rag_service(data_dir: str = "data/rag") -> RAGService:
    """
    Obtiene la instancia singleton del servicio RAG.

    Args:
        data_dir: Directorio de datos

    Returns:
        Instancia de RAGService
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(data_dir)
    return _rag_service
