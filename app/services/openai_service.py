import json
import logging
import os
import re
import time
import hashlib
from typing import Optional, Dict, Any, List, Tuple

import requests

logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Servicio optimizado para interactuar con OpenAI GPT y Whisper.

    Características:
    - Sistema de caché para reducir costos de API
    - Reintentos automáticos con backoff exponencial
    - Validación robusta de respuestas
    - Prompts especializados por tipo de interacción
    - Métricas de uso y costos
    - Fallback inteligente sin IA

    Uso:
        service = OpenAIService()
        result = service.handle_any_request("HLSO 16/20 con glaseo 20%")
    """

    # Constantes para límites de caracteres en respuestas
    RESPONSE_LIMITS = {
        'greeting': 100,            # Saludos breves: "¡Hola! 🦐 ¿Qué producto necesitas?"
        'quick_question': 150,      # Preguntas rápidas: "¿Qué glaseo necesitas? (10%, 20%, 30%)"
        'confirmation': 200,        # Confirmaciones: "Perfecto! Generando proforma de HLSO 16/20..."
        'detailed_list': 300,       # Listados: Cuando se listan múltiples productos
        'price_explanation': 150,   # Explicaciones de precios
    }

    # Configuración de caché
    CACHE_TTL = 3600  # 1 hora en segundos
    CACHE_MAX_SIZE = 100  # Máximo 100 entradas en caché

    # Configuración de rate limiting
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1  # Segundos
    RATE_LIMIT_DELAY = 60  # Esperar 60 segundos si hay rate limit

    def __init__(self):
        """Inicializa el servicio OpenAI con configuración optimizada."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # 🆕 Modelo fine-tuned (configurable desde .env)
        # Si OPENAI_FINETUNED_MODEL está configurado, úsalo; si no, usa el modelo base
        self.model = os.getenv("OPENAI_FINETUNED_MODEL", "gpt-3.5-turbo")
        
        self.whisper_model = "whisper-1"
        self.base_url = "https://api.openai.com/v1"

        # Sistema de caché en memoria
        self._cache: Dict[str, Tuple[Any, float]] = {}  # {cache_key: (response, timestamp)}
        self._cache_hits = 0
        self._cache_misses = 0

        # Métricas de rate limiting
        self._rate_limit_hits = 0
        self._last_request_time = 0
        
        # 🆕 Log del modelo en uso
        if "ft:" in self.model:
            logger.info(f"🎯 Usando modelo FINE-TUNED: {self.model}")
        else:
            logger.info(f"🤖 Usando modelo BASE: {self.model}")


    def is_available(self) -> bool:
        """
        Verifica si OpenAI está disponible.

        Returns:
            bool: True si la API key está configurada
        """
        return bool(self.api_key)

    # ==================== SISTEMA DE CACHÉ ====================

    def _generate_cache_key(self, prompt: str, params: dict = None) -> str:
        """
        Genera una clave única para el caché basada en el prompt y parámetros.

        Args:
            prompt: Texto del prompt
            params: Parámetros adicionales (temperatura, max_tokens, etc.)

        Returns:
            str: Hash MD5 como clave de caché
        """
        cache_string = prompt
        if params:
            # Ordenar params para consistencia
            cache_string += str(sorted(params.items()))

        return hashlib.md5(cache_string.encode('utf-8')).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """
        Obtiene una respuesta del caché si existe y no ha expirado.

        Args:
            cache_key: Clave de caché

        Returns:
            Respuesta cacheada o None si no existe o expiró
        """
        if cache_key in self._cache:
            response, timestamp = self._cache[cache_key]

            # Verificar si no ha expirado
            if time.time() - timestamp < self.CACHE_TTL:
                self._cache_hits += 1
                logger.info(f"💾 Cache HIT (hits={self._cache_hits}, misses={self._cache_misses})")
                return response
            else:
                # Expirado, eliminar
                del self._cache[cache_key]
                logger.debug(f"🗑️ Cache entry expirada, eliminada")

        self._cache_misses += 1
        logger.debug(f"❌ Cache MISS (hits={self._cache_hits}, misses={self._cache_misses})")
        return None

    def _save_to_cache(self, cache_key: str, response: str) -> None:
        """
        Guarda una respuesta en el caché.

        Args:
            cache_key: Clave de caché
            response: Respuesta a cachear
        """
        # Limpiar caché si está lleno
        if len(self._cache) >= self.CACHE_MAX_SIZE:
            # Eliminar la entrada más antigua
            oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
            del self._cache[oldest_key]
            logger.debug(f"🗑️ Cache lleno, eliminada entrada más antigua")

        self._cache[cache_key] = (response, time.time())
        logger.debug(f"💾 Respuesta guardada en caché (total={len(self._cache)})")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.

        Returns:
            Dict con estadísticas: hits, misses, size, hit_rate
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'size': len(self._cache),
            'max_size': self.CACHE_MAX_SIZE,
            'hit_rate': f"{hit_rate:.1f}%",
            'total_requests': total_requests
        }

    def clear_cache(self) -> None:
        """Limpia todo el caché."""
        self._cache.clear()
        logger.info("🗑️ Caché limpiado completamente")

    # ==================== MANEJO DE RATE LIMITING ====================

    def _handle_rate_limit(self, response: requests.Response, attempt: int) -> bool:
        """
        Maneja errores de rate limiting de OpenAI.

        Args:
            response: Respuesta HTTP de la API
            attempt: Número de intento actual

        Returns:
            bool: True si se debe reintentar, False si no
        """
        if response.status_code == 429:  # Rate limit exceeded
            self._rate_limit_hits += 1

            # Verificar si hay header Retry-After
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                wait_time = int(retry_after)
            else:
                # Backoff exponencial: 2^attempt segundos
                wait_time = min(2 ** attempt, self.RATE_LIMIT_DELAY)

            logger.warning(
                f"⚠️ Rate limit alcanzado (total={self._rate_limit_hits}). "
                f"Esperando {wait_time}s antes de reintentar..."
            )
            time.sleep(wait_time)
            return True

        return False

    # ==================== MÉTODOS PRINCIPALES ====================

    def chat_with_context(self, user_message: str, conversation_history: list[dict] = None, session_data: dict = None, use_rag: bool = True) -> dict:
        """
        Conversación natural con GPT manteniendo contexto completo
        MANEJA CUALQUIER TIPO DE SOLICITUD DEL USUARIO

        Args:
            user_message: Mensaje actual del usuario
            conversation_history: Historial de mensajes previos
            session_data: Datos de la sesión actual (productos detectados, precios, etc.)
            use_rag: Si usar el sistema RAG para enriquecer contexto

        Returns:
            Dict con respuesta y acciones a realizar
        """
        if not self.is_available():
            # Fallback inteligente sin IA
            return self._intelligent_fallback(user_message, session_data)

        try:
            # Construir historial de conversación
            messages = [
                {"role": "system", "content": self._get_conversation_system_prompt()}
            ]

            # 🆕 RAG: Agregar contexto relevante recuperado
            if use_rag:
                rag_context = self._get_rag_context(user_message)
                if rag_context:
                    messages.append({
                        "role": "system",
                        "content": f"INFORMACIÓN RELEVANTE DE LA BASE DE CONOCIMIENTOS:\n{rag_context}\n\nUsa esta información para responder al usuario si es relevante."
                    })

            # Agregar contexto de sesión si existe
            if session_data:
                context_message = self._build_context_message(session_data)
                messages.append({"role": "system", "content": context_message})

            # Agregar historial de conversación
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Últimos 10 mensajes

            # Agregar mensaje actual
            messages.append({"role": "user", "content": user_message})

            # Hacer petición a GPT con reintentos (temperature baja para JSON consistente)
            result = self._make_request_with_retry(messages, max_tokens=500, temperature=0.3)

            if result:
                # Parsear respuesta para extraer acciones
                parsed = self._parse_gpt_response(result)
                return parsed
            else:
                # Fallback inteligente si falla la petición
                return self._intelligent_fallback(user_message, session_data)

        except Exception as e:
            logger.error(f"❌ Error en chat con contexto: {str(e)}")
            # Siempre retornar algo coherente
            return self._intelligent_fallback(user_message, session_data)

    def _get_conversation_system_prompt(self) -> str:
        """
        Prompt del sistema para conversación natural.
        Usa _get_base_context() como fuente de verdad para productos/tallas.
        """
        base = self._get_base_context()
        return f"""{base}

RECONOCIMIENTO DE TÉRMINOS:
- "Cocedero"/"Cocido" → Preguntar: COOKED, PRE-COCIDO o COCIDO SIN TRATAR
- "Inteiro"/"Entero" → HOSO o HLSO
- "Colas" (sin cocedero) → HLSO
- "Colas Cocedero"/"Colas Cocidas" → COOKED
- "CFR"/"CIF" + ciudad → Detectar destino, marcar flete
- "Cola X/X con flete" → HLSO con flete (FOB + Flete)

OBJETIVO: Ayudar al cliente a generar cotizaciones de camarón.

FLUJO:
1. Detectar productos y tallas
2. Preguntar glaseo si falta (0%, 10%, 20%, 30%)
3. Confirmar destino si menciona CFR/CIF
4. Confirmar datos antes de generar proforma

REGLAS:
- Respuestas concisas y directas
- Si detectas múltiples tallas, lista todas
- Si falta info crítica, pregunta de forma natural
- Si menciona "Cocedero", ofrece opciones específicas
- No pidas datos que ya tienes

FORMATO DE RESPUESTA (JSON):
{{
    "response": "Tu respuesta al usuario",
    "action": "detect_products|ask_glaseo|ask_product_type|ask_language|generate_proforma|none",
    "data": {{
        "products": [...],
        "glaseo": 20,
        "destination": "Lisboa",
        ...
    }}
}}

EJEMPLOS:
Usuario: "Hola"
{{
    "response": "Hola, soy el asistente de BGR Export. ¿Qué producto necesitas cotizar?",
    "action": "none",
    "data": {{}}
}}

Usuario: "Necesito precios de HLSO 16/20"
{{
    "response": "HLSO 16/20. ¿Qué glaseo necesitas? (10%, 20% o 30%)",
    "action": "ask_glaseo",
    "data": {{"products": [{{"product": "HLSO", "size": "16/20"}}]}}
}}

Usuario: "Lagostino Cocedero CFR Lisboa: Inteiro 20/30, 30/40. Colas 21/25, 31/35"
{{
    "response": "Cotización CFR Lisboa detectada.\\nInteiro: 20/30, 30/40\\nColas: 21/25, 31/35\\n\\n¿Qué glaseo necesitas? (10%, 20%, 30%)\\n¿Qué producto cocido prefieres? COOKED, PRE-COCIDO o COCIDO SIN TRATAR",
    "action": "ask_product_type",
    "data": {{
        "sizes_inteiro": ["20/30", "30/40"],
        "sizes_colas": ["21/25", "31/35"],
        "destination": "Lisboa",
        "product_category": "cocido"
    }}
}}"""

    def _get_rag_context(self, query: str, max_tokens: int = 1500) -> str:
        """
        Recupera contexto relevante del sistema RAG.

        Args:
            query: Consulta del usuario
            max_tokens: Límite aproximado de tokens para el contexto

        Returns:
            Contexto formateado o string vacío si no hay resultados
        """
        try:
            from app.services.rag_service import get_rag_service

            rag = get_rag_service()

            # Verificar si hay documentos indexados
            if not rag.documents:
                return ""

            # Recuperar contexto relevante
            context = rag.retrieve_context(
                query=query,
                top_k=3,
                max_tokens=max_tokens
            )

            if context:
                logger.debug(f"🔍 RAG: Contexto recuperado ({len(context)} chars)")

            return context

        except Exception as e:
            logger.warning(f"⚠️ Error recuperando contexto RAG: {str(e)}")
            return ""

    def _build_context_message(self, session_data: dict) -> str:
        """
        Construye mensaje de contexto con datos de la sesión
        """
        context_parts = ["CONTEXTO DE LA SESIÓN ACTUAL:"]

        if session_data.get('products'):
            products_list = ", ".join([f"{p['product']} {p['size']}" for p in session_data['products']])
            context_parts.append(f"- Productos detectados: {products_list}")

        if session_data.get('glaseo_percentage'):
            context_parts.append(f"- Glaseo especificado: {session_data['glaseo_percentage']}%")

        if session_data.get('destination'):
            context_parts.append(f"- Destino: {session_data['destination']}")

        if session_data.get('language'):
            context_parts.append(f"- Idioma preferido: {session_data['language']}")

        if session_data.get('state'):
            context_parts.append(f"- Estado actual: {session_data['state']}")

        return "\n".join(context_parts)

    def _parse_gpt_response(self, response: str) -> dict:
        """
        Parsea la respuesta de GPT para extraer JSON con validación de schema
        """
        try:
            # Intentar parsear como JSON
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)

                # Validar schema: campos requeridos
                required_fields = ['response', 'action', 'data']
                if not all(field in parsed for field in required_fields):
                    logger.warning(f"⚠️ Respuesta GPT incompleta. Campos presentes: {parsed.keys()}")
                    # Intentar recuperar con defaults
                    return self._get_default_response(
                        text=parsed.get('response', response),
                        action=parsed.get('action', 'none'),
                        data=parsed.get('data', {})
                    )

                # Validar action: debe ser uno de los permitidos
                valid_actions = [
                    'detect_products', 'ask_glaseo', 'ask_language', 'ask_product_type',
                    'generate_proforma', 'greeting', 'none', 'help',
                    'audio_info', 'product_list', 'price_inquiry', 'thanks',
                    'goodbye', 'size_detected', 'session_context', 'general_inquiry',
                    'emergency_fallback', 'empty_message', 'audio_transcription_failed',
                    'audio_processing_error'
                ]
                if parsed['action'] not in valid_actions:
                    logger.warning(f"⚠️ Action inválida: '{parsed['action']}'. Usando 'none'")
                    parsed['action'] = 'none'

                # Validar tipos de datos
                if not isinstance(parsed['response'], str):
                    logger.warning(f"⚠️ Campo 'response' no es string: {type(parsed['response'])}")
                    parsed['response'] = str(parsed['response'])

                if not isinstance(parsed['data'], dict):
                    logger.warning(f"⚠️ Campo 'data' no es dict: {type(parsed['data'])}")
                    parsed['data'] = {}

                return parsed
            else:
                # Si no hay JSON, retornar respuesta como texto
                logger.warning("⚠️ No se encontró JSON en la respuesta de GPT")
                return self._get_default_response(text=response)

        except json.JSONDecodeError as e:
            # Si falla el parseo, retornar respuesta como texto
            logger.error(f"❌ Error parseando JSON de GPT: {str(e)}")
            return self._get_default_response(text=response)
        except Exception as e:
            logger.error(f"❌ Error inesperado en _parse_gpt_response: {str(e)}")
            return self._get_default_response(text=response)

    def _get_default_response(self, text: str = None, action: str = "none", data: dict = None) -> dict:
        """
        Genera una respuesta por defecto válida cuando falla el parsing
        """
        return {
            "response": text if text else "🦐 ¿En qué puedo ayudarte hoy?",
            "action": action,
            "data": data if data is not None else {}
        }

    def _make_request(self, messages: list[dict], max_tokens: int = 300, temperature: float = 0.3, use_cache: bool = True, force_base_model: bool = False) -> str | None:
        """
        Hace una petición directa a la API de OpenAI con caché y rate limiting.

        Args:
            messages: Lista de mensajes para la conversación
            max_tokens: Número máximo de tokens en la respuesta
            temperature: Temperatura para generación (0.0-1.0)
            use_cache: Si debe usar el sistema de caché (default: True)
            force_base_model: Si True, usa gpt-3.5-turbo en lugar del modelo fine-tuned (para análisis JSON)

        Returns:
            Respuesta de la API o None si falla
        """
        if not self.is_available():
            logger.warning("⚠️ OpenAI API key no configurada")
            return None

        try:
            # Generar clave de caché
            if use_cache:
                prompt_text = json.dumps(messages, sort_keys=True)
                params = {'max_tokens': max_tokens, 'temperature': temperature, 'model': self.model}
                cache_key = self._generate_cache_key(prompt_text, params)

                # Intentar obtener del caché
                cached_response = self._get_from_cache(cache_key)
                if cached_response:
                    return cached_response

            # Preparar petición
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 🆕 Usar modelo base si se fuerza (para análisis JSON)
            model_to_use = "gpt-3.5-turbo" if force_base_model else self.model
            
            data = {
                "model": model_to_use,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            # Hacer petición con timeout
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )

            # Manejar respuesta exitosa
            if response.status_code == 200:
                result = response.json()
                response_text = result["choices"][0]["message"]["content"].strip()

                # Guardar en caché si está habilitado
                if use_cache:
                    self._save_to_cache(cache_key, response_text)

                return response_text

            # Manejar rate limiting
            elif response.status_code == 429:
                logger.warning(f"⚠️ Rate limit alcanzado. Headers: {response.headers}")
                # El método _make_request_with_retry se encarga de manejar esto
                return None

            # Otros errores
            else:
                error_detail = ""
                try:
                    error_json = response.json()
                    error_detail = error_json.get('error', {}).get('message', '')
                except:
                    error_detail = response.text[:200]

                logger.error(
                    f"❌ Error API OpenAI: {response.status_code} | "
                    f"Detalle: {error_detail}"
                )
                return None

        except requests.exceptions.Timeout:
            logger.error("❌ Timeout en petición a OpenAI (30s)")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Error de conexión con OpenAI: {str(e)}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de red en petición OpenAI: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error inesperado en petición OpenAI: {str(e)}")
            return None

    def analyze_user_intent(self, message: str, context: dict = None) -> dict:
        """
        Analiza la intención del usuario usando GPT-4o mini
        """
        if not self.is_available():
            # Fallback con análisis básico de patrones
            return self._basic_intent_analysis(message)

        try:
            system_prompt = """
Analiza solicitudes de exportación de camarón/langostino y extrae información estructurada.

PRODUCTOS VÁLIDOS: HOSO, HLSO, P&D IQF, P&D BLOQUE, EZ PEEL, PuD-EUROPA, PuD-EEUU, COOKED, PRE-COCIDO, COCIDO SIN TRATAR
TALLAS VÁLIDAS: U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40, 40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90

RECONOCIMIENTO DE TÉRMINOS (español/portugués/inglés):
IMPORTANTE: "Cocedero"/"Cocido" es la CALIDAD/PROCESAMIENTO, NO el producto final.

COMBINACIONES VÁLIDAS:
- "Inteiro Cocedero" / "Entero Cocido" → Solicitar aclaración (¿HOSO cocido? ¿COOKED entero?)
- "Colas Cocedero" / "Colas Cocidas" → COOKED (colas peladas cocidas)
- Solo "Cocedero" sin especificar → Solicitar tipo: COOKED, PRE-COCIDO, COCIDO SIN TRATAR
- "Inteiro" solo (sin cocedero) → HOSO (camarón entero crudo)
- "Colas" / "Cola" solo (sin cocedero) → HLSO (camarón sin cabeza, con cáscara)
- "Precio CFR de cola 20/30" → HLSO 20/30 con flete (NO es COOKED ni P&D IQF)

OTROS TÉRMINOS:
- "Lagostino", "Vannamei", "Camarón", "Shrimp" → Todos válidos
- "CFR [ciudad]", "CIF [ciudad]" → Detectar destino y marcar flete_solicitado: true
- "Contenedor" → Solicitud de cotización grande
- "BRINE", "Salmuera" → Tipo de procesamiento (extraer como processing_type)
- "NET", "Neto" → Peso neto (extraer porcentaje si está presente, ej: "100% NET")
- Cantidades con formato: "20k/caja", "10kg/caja", "5000kg", "10000lb"

FORMATOS DE TALLAS A RECONOCER:
- Con guión: "16-20", "21-25", "26-30" → Normalizar a "16/20", "21/25", "26/30"
- Con barra: "16/20", "21/25" → Mantener formato
- Separadas por espacios: "16 20" → Normalizar a "16/20"

EXTRAE (valores exactos o null):
- Intent: pricing|proforma|product_info|greeting|help|other
- Product: nombre exacto del producto (o null si necesita especificar entre COOKED/PRE-COCIDO/COCIDO SIN TRATAR)
- Size: talla exacta (o array de tallas si menciona múltiples)
- Sizes: array con TODAS las tallas detectadas (normalizar formato a X/X)
- Sizes_by_product: objeto agrupando tallas por producto {"HLSO": ["16/20", "21/25"], "HOSO": ["20/30"]}
- Glaseo: porcentaje (0, 10, 20, 30) → convertir a factor decimal
  * 0% = null (sin glaseo, CFR simple)
  * 10% = 0.90
  * 20% = 0.80
  * 30% = 0.70
- Destination: ciudad/país si menciona "CFR [lugar]", "CIF [lugar]", "flete a [lugar]", "envío a [lugar]"
- Flete: valor numérico si menciona "flete 0.30", "freight $0.25", etc.
- Cantidad: número + unidad (ej: "5000 kg", "10000 lb", "20k/caja")
- Processing_type: "BRINE", "SALMUERA", u otro tipo de procesamiento mencionado
- Net_weight_percentage: porcentaje de peso neto si menciona (ej: "100% NET" → 100)
- Cliente: nombre si menciona "cliente [nombre]", "para [nombre]"
- Language: "es" (español) o "en" (inglés)
- Multiple_sizes: true si detecta múltiples tallas en el mensaje
- Multiple_products: true si detecta múltiples productos diferentes

REGLAS IMPORTANTES:
1. Si menciona tallas (ej: 20/30, 21/25) → intent: "proforma" (incluso si empieza con saludo)
2. NORMALIZAR TODAS LAS TALLAS: "16-20" → "16/20", "21-25" → "21/25"
3. EXTRAER TODAS LAS TALLAS sin excepción, incluso si hay 10+ tallas
4. Si menciona CFR/CIF sin glaseo → flete_solicitado: true, glaseo_factor: null (cálculo CFR simple: FOB + Flete)
5. Si menciona CFR/CIF con glaseo (ej: "CFR con 15%") → flete_solicitado: true, glaseo_factor: 0.85
6. Si menciona "Cocedero" + "Inteiro" → multiple_presentations: true, needs_product_type: true, clarification_needed
7. Si menciona "Cocedero" + "Colas" → product: "COOKED" (colas cocidas)
8. Si menciona solo "Cocedero" → product: null, needs_product_type: true
9. Si menciona "Cola" o "Colas" SIN "Cocedero" → product: "HLSO" (camarón sin cabeza, con cáscara)
10. Si detecta múltiples tallas → multiple_sizes: true, listar TODAS en array
11. Si detecta "Inteiro" y "Colas" en el mismo mensaje → separar tallas: sizes_inteiro y sizes_colas
12. NO asumir valores por defecto - extraer solo lo que el usuario dice explícitamente
13. CFR sin glaseo = Precio FOB + Flete (simple, sin aplicar factor de glaseo)
14. CFR con glaseo = Precio FOB + Glaseo + Flete (completo)
15. "Precio CFR de cola 20/30 con 0.25 de flete" → product: "HLSO", size: "20/30", flete_custom: 0.25, glaseo_factor: null
16. Extraer "BRINE" como processing_type si está presente
17. Extraer "100% NET" como net_weight_percentage: 100
18. Extraer cantidades como "20k/caja" → cantidad: "20000 kg/caja"

EJEMPLOS:
Input: "HLSO 16/20 con 20% glaseo"
Output: {intent: "proforma", product: "HLSO", size: "16/20", sizes: ["16/20"], glaseo_factor: 0.80, destination: null, confidence: 0.9}

Input: "Hola Erick, como estas? podras ofertar otros tamaños de camaron? HLSO 16-20/ 21-25/26-30/31-35/36-40/41-50/51-60 HOSO 20-30/30-40/40-50 BRINE 100% NET 20k/caja"
Output: {intent: "proforma", product: null, multiple_products: true, multiple_sizes: true, sizes: ["16/20", "21/25", "26/30", "31/35", "36/40", "41/50", "51/60", "20/30", "30/40", "40/50"], sizes_by_product: {"HLSO": ["16/20", "21/25", "26/30", "31/35", "36/40", "41/50", "51/60"], "HOSO": ["20/30", "30/40", "40/50"]}, processing_type: "BRINE", net_weight_percentage: 100, cantidad: "20000 kg/caja", glaseo_factor: null, glaseo_percentage: null, confidence: 0.95}

Input: "Buenas Tardes. Necesito precios Lagostino Cocedero CFR Lisboa: Inteiro 0% 20/30, 30/40, 40/50. Colas 21/25, 31/35, 36/40, 41/50"
Output: {intent: "proforma", product: null, needs_product_type: true, product_category: "cocido", sizes_inteiro: ["20/30", "30/40", "40/50"], sizes_colas: ["21/25", "31/35", "36/40", "41/50"], sizes: ["20/30", "30/40", "40/50", "21/25", "31/35", "36/40", "41/50"], destination: "Lisboa", flete_solicitado: true, glaseo_factor: null, glaseo_percentage: 0, multiple_sizes: true, multiple_presentations: true, clarification_needed: "Cliente solicita 'Inteiro Cocedero' y 'Colas Cocedero'. Confirmar productos específicos.", confidence: 0.95}

Input: "Precio CFR Houston HLSO 16/20"
Output: {intent: "proforma", product: "HLSO", size: "16/20", sizes: ["16/20"], destination: "Houston", flete_solicitado: true, glaseo_factor: null, confidence: 0.9}

Input: "Precio CFR Houston HLSO 16/20 con 15% glaseo"
Output: {intent: "proforma", product: "HLSO", size: "16/20", sizes: ["16/20"], destination: "Houston", flete_solicitado: true, glaseo_factor: 0.85, glaseo_percentage: 15, confidence: 0.95}

Input: "Precio cfr de cola 20/30 con 0.25 de flete"
Output: {intent: "proforma", product: "HLSO", size: "20/30", sizes: ["20/30"], flete_custom: 0.25, flete_solicitado: true, glaseo_factor: null, glaseo_percentage: 0, confidence: 0.95}

Input: "Necesito precios CFR Lisboa Inteiro 0% 20/30, 30/40"
Output: {intent: "proforma", product: null, needs_product_type: true, sizes: ["20/30", "30/40"], destination: "Lisboa", flete_solicitado: true, glaseo_factor: null, glaseo_percentage: 0, confidence: 0.9}

Input: "Precio DDP Houston con flete 0.30"
Output: {intent: "proforma", destination: "Houston", flete_custom: 0.30, is_ddp: true, usar_libras: false, confidence: 0.9}

Input: "Hola, necesito cotización"
Output: {intent: "greeting", product: null, wants_proforma: true, confidence: 0.8}

Responde SOLO en JSON:
{
  "intent": "...",
  "product": null | "...",
  "size": null | "...",
  "sizes": null | [...],
  "sizes_by_product": null | {...},
  "sizes_inteiro": null | [...],
  "sizes_colas": null | [...],
  "multiple_sizes": false,
  "multiple_products": false,
  "multiple_presentations": false,
  "needs_product_type": false,
  "product_category": null | "cocido",
  "clarification_needed": null | "...",
  "glaseo_factor": null | number,
  "glaseo_percentage": null | number,
  "destination": null | "...",
  "flete_custom": null | number,
  "precio_base_custom": null | number,
  "flete_solicitado": false,
  "is_ddp": false,
  "usar_libras": false,
  "cantidad": null | "...",
  "processing_type": null | "...",
  "net_weight_percentage": null | number,
  "cliente_nombre": null | "...",
  "wants_proforma": false,
  "language": "es",
  "confidence": 0.0-1.0
}
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Mensaje: '{message}'"}
            ]

            # 🆕 Forzar modelo base para análisis JSON (el fine-tuned responde en texto)
            result = self._make_request(messages, max_tokens=300, temperature=0.3, force_base_model=True)

            if result:
                # Intentar parsear como JSON
                try:
                    parsed_result = json.loads(result)
                    logger.info(f"🤖 Análisis OpenAI: {parsed_result}")
                    return parsed_result
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Respuesta no es JSON (modelo fine-tuned?): {result[:100]}...")
                    # 🆕 Fallback: Si el modelo fine-tuned responde en texto, usar análisis básico
                    logger.info("🔄 Usando análisis básico como fallback")
                    return self._basic_intent_analysis(message)
            else:
                return {"intent": "unknown", "confidence": 0}

        except Exception as e:
            logger.error(f"❌ Error en análisis OpenAI: {str(e)}")
            return {"intent": "unknown", "confidence": 0}

    def generate_smart_response(self, user_message: str, context: dict, price_data: dict = None) -> str | None:
        """
        Genera una respuesta inteligente y personalizada
        """
        if not self.is_available():
            return None

        try:
            # Construir contexto para GPT
            context_info = f"""
Usuario: {user_message}
Estado actual: {context.get('state', 'unknown')}
Datos de sesión: {context.get('data', {})}
"""

            if price_data:
                context_info += f"\nDatos de precio disponibles: {price_data}"

            system_prompt = """
Eres ShrimpBot, el asistente comercial de BGR Export especializado en camarones premium. Tu objetivo principal es ayudar a los clientes a crear proformas y cotizaciones.

PERSONALIDAD:
- Profesional pero amigable y proactivo
- Experto comercial en productos de camarón
- Usa emojis apropiados (🦐, 💰, 📊, 📋, etc.)
- Siempre guía hacia la creación de proformas
- Enfocado en cerrar ventas y generar cotizaciones

PRODUCTOS DISPONIBLES:
- HOSO (Head On Shell On) - Camarón entero con cabeza
- HLSO (Head Less Shell On) - Sin cabeza, con cáscara  
- P&D IQF (Peeled & Deveined) - Pelado y desvenado individual
- P&D BLOQUE - Pelado y desvenado en bloque
- PuD-EUROPA - Calidad premium para Europa
- EZ PEEL - Fácil pelado
- PuD-EEUU - Calidad para Estados Unidos
- COOKED - Cocido listo para consumo
- PRE-COCIDO - Pre-cocido
- COCIDO SIN TRATAR - Cocido sin procesar

TALLAS DISPONIBLES: U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40, 40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90

INSTRUCCIONES CLAVE:
- Si el usuario ya especificó PRODUCTO y TALLA: NO pidas más información, confirma que generas la proforma
- Para saludos: máximo 100 caracteres
- Para preguntas rápidas: máximo 150 caracteres
- Para confirmaciones (con producto + talla): máximo 200 caracteres
- Si necesitas listar múltiples opciones: puedes usar hasta 300 caracteres
- Si tienes producto y talla, di: "¡Perfecto! Generando tu proforma de [producto] [talla]..."
- NO pidas cantidad si ya tienes producto y talla - genera la proforma directamente

REGLA CRÍTICA: Si detectas producto + talla en el mensaje, NUNCA pidas más información. Genera la proforma directamente.

OBJETIVO: Generar proformas inmediatamente cuando tengas datos suficientes.
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_info}
            ]

            result = self._make_request(messages, max_tokens=200, temperature=0.7)

            if result:
                # Limpiar emojis problemáticos que pueden causar errores de codificación
                cleaned_result = self._clean_problematic_emojis(result)
                logger.info(f"🤖 Respuesta generada por OpenAI: {cleaned_result}")
                return cleaned_result
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Error generando respuesta OpenAI: {str(e)}")
            return None

    def enhance_price_explanation(self, price_data: dict) -> str | None:
        """
        Mejora la explicación de precios usando IA
        """
        if not self.is_available() or not price_data:
            return None

        try:
            system_prompt = """
Eres un experto en explicar precios de camarón de manera clara y profesional.

Toma los datos de precio y genera una explicación breve y clara que incluya:
- Destacar el producto y talla
- Mencionar los diferentes tipos de precio (base, FOB, glaseo, final)
- Usar emojis apropiados
- Máximo 150 caracteres
- Tono profesional pero amigable

Formato de respuesta: texto directo sin JSON.
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Datos de precio: {price_data}"}
            ]

            result = self._make_request(messages, max_tokens=100, temperature=0.5)

            if result:
                return result
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Error mejorando explicación de precio: {str(e)}")
            return None

    # ==================== MÉTODOS ESPECIALIZADOS POR RESPONSABILIDAD ====================

    def _get_base_context(self) -> str:
        """
        Contexto base común para todos los prompts.
        Fuente de verdad para productos, tallas y tono.
        """
        return """Eres ShrimpBot, el asistente comercial de BGR Export.

PRODUCTOS: HOSO, HLSO, P&D IQF, P&D BLOQUE, EZ PEEL, PuD-EUROPA, PuD-EEUU, COOKED, PRE-COCIDO, COCIDO SIN TRATAR
TALLAS: U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40, 40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90

TONO: Profesional y directo. Respuestas concisas sin emojis excesivos. Máximo un emoji por mensaje si es necesario. Trato de tú."""

    def generate_greeting_response(self, user_name: str = None) -> str | None:
        """
        Genera respuesta específica para saludos
        Método especializado, rápido y eficiente
        """
        if not self.is_available():
            return None

        try:
            base = self._get_base_context()

            user_context = f"Usuario: {user_name}" if user_name else "Usuario nuevo"

            system_prompt = f"""{base}

TAREA: Responder a un saludo de forma amigable y directa.
LÍMITE: Máximo 100 caracteres.
OBJETIVO: Saludar Y preguntar qué producto necesita.

{user_context}
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Saluda al usuario"}
            ]

            result = self._make_request(messages, max_tokens=50, temperature=0.8)

            if result:
                logger.info(f"💬 Saludo generado: {result[:50]}...")
                return self._clean_problematic_emojis(result)

            return None

        except Exception as e:
            logger.error(f"❌ Error generando saludo: {str(e)}")
            return None

    def generate_confirmation_response(self, product: str, size: str, additional_info: dict = None) -> str | None:
        """
        Genera confirmación para generación de proforma
        Método especializado para confirmaciones
        """
        if not self.is_available():
            return None

        try:
            base = self._get_base_context()

            context = f"Producto: {product}, Talla: {size}"
            if additional_info:
                if additional_info.get('glaseo_percentage'):
                    context += f", Glaseo: {additional_info['glaseo_percentage']}%"
                if additional_info.get('destination'):
                    context += f", Destino: {additional_info['destination']}"

            system_prompt = f"""{base}

TAREA: Confirmar que vas a generar la proforma.
LÍMITE: Máximo 200 caracteres.
TONO: Entusiasta y profesional.
FORMATO: "¡Perfecto! Generando tu proforma de [producto] [talla]..."

Datos detectados: {context}
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Confirma generación de proforma"}
            ]

            result = self._make_request(messages, max_tokens=80, temperature=0.7)

            if result:
                logger.info(f"✅ Confirmación generada para {product} {size}")
                return self._clean_problematic_emojis(result)

            return None

        except Exception as e:
            logger.error(f"❌ Error generando confirmación: {str(e)}")
            return None

    def generate_question_response(self, question_type: str, context: dict = None) -> str | None:
        """
        Genera preguntas específicas según el tipo

        Args:
            question_type: 'glaseo', 'language', 'destination', 'product', 'size'
            context: Contexto adicional opcional
        """
        if not self.is_available():
            return None

        try:
            base = self._get_base_context()

            question_prompts = {
                'glaseo': {
                    'task': 'Preguntar qué porcentaje de glaseo necesita',
                    'options': 'Opciones: 10%, 20%, 30%',
                    'limit': 150
                },
                'language': {
                    'task': 'Preguntar en qué idioma quiere la proforma',
                    'options': 'Opciones: Español o English',
                    'limit': 150
                },
                'destination': {
                    'task': 'Preguntar a qué destino necesita envío',
                    'options': 'Menciona destinos comunes: Houston, Miami, China, etc.',
                    'limit': 150
                },
                'product': {
                    'task': 'Preguntar qué tipo de producto necesita',
                    'options': 'Opciones populares: HLSO (sin cabeza), HOSO (con cabeza), P&D IQF (pelado)',
                    'limit': 200
                },
                'size': {
                    'task': 'Preguntar qué talla necesita',
                    'options': 'Menciona tallas populares: 16/20, 21/25, 26/30, 31/35',
                    'limit': 150
                }
            }

            if question_type not in question_prompts:
                logger.warning(f"⚠️ Tipo de pregunta desconocido: {question_type}")
                return None

            q_config = question_prompts[question_type]
            context_str = f"\nContexto adicional: {context}" if context else ""

            system_prompt = f"""{base}

TAREA: {q_config['task']}
{q_config['options']}
LÍMITE: Máximo {q_config['limit']} caracteres.
TONO: Amigable y directo.{context_str}
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Pregunta sobre {question_type}"}
            ]

            result = self._make_request(messages, max_tokens=60, temperature=0.7)

            if result:
                logger.info(f"❓ Pregunta generada: tipo={question_type}")
                return self._clean_problematic_emojis(result)

            return None

        except Exception as e:
            logger.error(f"❌ Error generando pregunta: {str(e)}")
            return None

    def _estimate_tokens(self, text: str) -> int:
        """
        Estima el número de tokens en un texto
        Regla simple: ~4 caracteres = 1 token en español
        ~3 caracteres = 1 token en inglés
        """
        # Detectar idioma aproximadamente
        spanish_chars = sum(1 for c in text if c in 'áéíóúñ¿¡')
        ratio = 4 if spanish_chars > 3 else 3.5

        return int(len(text) / ratio)

    def _log_token_usage(self, prompt: str, response: str, method_name: str):
        """
        Registra el uso de tokens para métricas
        """
        prompt_tokens = self._estimate_tokens(prompt)
        response_tokens = self._estimate_tokens(response) if response else 0
        total_tokens = prompt_tokens + response_tokens

        # Calcular costo aproximado (GPT-3.5-turbo: $0.0015/1K prompt + $0.002/1K completion)
        cost = (prompt_tokens * 0.0015 / 1000) + (response_tokens * 0.002 / 1000)

        logger.info(
            f"📊 Tokens usados en {method_name}: "
            f"Prompt={prompt_tokens}, Response={response_tokens}, "
            f"Total={total_tokens}, Costo≈${cost:.6f}"
        )

    # ==================== SISTEMA DE EJEMPLOS DINÁMICOS (FEW-SHOT LEARNING) ====================

    def _get_relevant_examples(self, context_type: str, detected_data: dict = None) -> str:
        """
        Selecciona ejemplos relevantes basados en el contexto actual
        Few-shot learning dinámico para mejorar respuestas

        Args:
            context_type: 'greeting', 'product_query', 'proforma_complete', 'missing_info'
            detected_data: Datos detectados del usuario (productos, tallas, etc.)

        Returns:
            String con ejemplos relevantes formateados
        """
        examples = {
            'greeting': """
EJEMPLO RELEVANTE:
Usuario: "Hola"
Asistente: "¡Hola! 👋 Soy ShrimpBot. ¿Qué producto necesitas? 🦐"
""",
            'product_query': """
EJEMPLO RELEVANTE:
Usuario: "Necesito HLSO"
Asistente: "¡Perfecto! HLSO es muy popular. ¿Qué talla necesitas? 📊 Tenemos 16/20, 21/25, 26/30..."
""",
            'proforma_complete': """
EJEMPLO RELEVANTE:
Usuario: "HLSO 16/20 con glaseo 20%"
Asistente: "¡Excelente! 🦐 Generando proforma de HLSO 16/20 con glaseo 20%. Un momento..."
""",
            'missing_glaseo': """
EJEMPLO RELEVANTE:
Usuario: "HLSO 16/20"
Asistente: "¡Perfecto! HLSO 16/20. ¿Qué glaseo necesitas? (10%, 20% o 30%) ❄️"
""",
            'missing_language': """
EJEMPLO RELEVANTE:
Usuario: [tiene producto y talla]
Asistente: "Excelente. ¿En qué idioma quieres la proforma? 🌐 (Español/English)"
""",
            'missing_destination': """
EJEMPLO RELEVANTE:
Usuario: "Con flete"
Asistente: "¿A qué destino lo necesitas? 🌍 Houston, Miami, China..."
"""
        }

        # Seleccionar ejemplo base
        example = examples.get(context_type, "")

        # Personalizar ejemplo si hay datos detectados
        if detected_data:
            if detected_data.get('product') and detected_data.get('size'):
                prod = detected_data['product']
                size = detected_data['size']
                example = f"""
EJEMPLO SIMILAR A TU CASO:
Usuario: "{prod} {size}"
Asistente: "¡Perfecto! {prod} {size} es excelente. Generando tu proforma... 🦐"
"""

        return example

    def _build_contextual_system_prompt(self, base_prompt: str, context_type: str, detected_data: dict = None) -> str:
        """
        Construye un prompt con ejemplos dinámicos relevantes

        Args:
            base_prompt: Prompt base del sistema
            context_type: Tipo de contexto actual
            detected_data: Datos detectados

        Returns:
            Prompt enriquecido con ejemplos relevantes
        """
        relevant_examples = self._get_relevant_examples(context_type, detected_data)

        return f"""{base_prompt}

{relevant_examples}

APLICA EL MISMO ESTILO Y TONO QUE EN LOS EJEMPLOS."""

    def transcribe_audio(self, audio_file_path: str, language: str = 'es') -> str | None:
        """
        Transcribe audio usando OpenAI Whisper con manejo robusto
        Soporta múltiples idiomas y formatos de audio
        
        Args:
            audio_file_path: Ruta al archivo de audio
            language: Código de idioma (es, en, etc.) - None para detección automática
        
        Returns:
            Texto transcrito o None si falla
        """
        if not self.is_available():
            logger.warning("⚠️ OpenAI no disponible para transcripción de audio")
            return None

        try:
            # Verificar que el archivo existe
            if not os.path.exists(audio_file_path):
                logger.error(f"❌ Archivo de audio no encontrado: {audio_file_path}")
                return None

            # Verificar tamaño del archivo (máximo 25MB para Whisper)
            file_size = os.path.getsize(audio_file_path)
            if file_size > 25 * 1024 * 1024:  # 25MB
                logger.error(f"❌ Archivo de audio muy grande: {file_size / (1024*1024):.2f}MB")
                return None

            logger.info(f"🎤 Transcribiendo audio: {audio_file_path} ({file_size / 1024:.2f}KB)")

            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': audio_file,
                    'model': (None, self.whisper_model)
                }

                # Agregar idioma solo si se especifica
                if language:
                    files['language'] = (None, language)

                # Intentar transcripción con timeout extendido
                response = requests.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    timeout=60  # Timeout más largo para archivos grandes
                )

            if response.status_code == 200:
                result = response.json()
                transcription = result.get('text', '').strip()

                if transcription:
                    logger.info(f"✅ Audio transcrito exitosamente: '{transcription[:100]}...'")
                    return transcription
                else:
                    logger.warning("⚠️ Transcripción vacía")
                    return None
            else:
                logger.error(f"❌ Error API Whisper: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("❌ Timeout en transcripción de audio")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de red en transcripción: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error inesperado en transcripción de audio: {str(e)}")
            return None

    def detect_multiple_products(self, message: str) -> list[dict]:
        """
        Detecta múltiples productos en un mensaje
        Retorna lista de diccionarios con producto y talla
        Detecta patrones como "Inteiro" y "Colas" con múltiples tallas
        """
        if not message:
            return []

        message_upper = message.upper()
        products_found = []

        # PRIMERO: Detectar si menciona "Inteiro" y "Colas" (patrón especial)
        has_inteiro = any(term in message_upper for term in ['INTEIRO', 'ENTERO'])
        has_colas = any(term in message_upper for term in ['COLAS', 'COLA', 'TAILS', 'TAIL'])
        
        if has_inteiro or has_colas:
            # Buscar todas las tallas en el mensaje
            all_sizes = re.findall(r'(\d+)/(\d+)', message)
            
            if len(all_sizes) > 1:
                # Múltiples tallas detectadas con Inteiro/Colas
                # Retornar lista vacía para forzar el flujo de aclaración
                logger.info(f"🔍 Detectado patrón Inteiro/Colas con {len(all_sizes)} tallas → Requiere aclaración")
                # Retornar lista con marcador especial
                return [{'special': 'inteiro_colas', 'count': len(all_sizes)}]

        # Patrones para productos específicos
        product_patterns = {
            'HOSO': r'\bHOSO\b',
            'HLSO': r'\bHLSO\b',
            'P&D IQF': r'\b(?:P&D|PYD|P\s*&\s*D)\s*(?:IQF|TAIL\s*OFF)?\b',
            'P&D BLOQUE': r'\b(?:P&D|PYD)\s*(?:BLOQUE|BLOCK)\b',
            'EZ PEEL': r'\b(?:EZ\s*PEEL|EZPEEL)\b',
            'COOKED': r'\b(?:COOKED|COCIDO|COCEDERO)\b',
        }

        # Buscar todas las líneas del mensaje
        lines = message_upper.split('\n')

        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue

            # Buscar talla en la línea (formato XX/XX o XX-XX)
            size_match = re.search(r'(\d+)[/-](\d+)', line)
            if not size_match:
                continue

            size = f"{size_match.group(1)}/{size_match.group(2)}"

            # Buscar producto en la línea
            product_found = None
            for product_name, pattern in product_patterns.items():
                if re.search(pattern, line):
                    product_found = product_name
                    break

            # Si no se encontró producto específico, intentar inferir
            if not product_found:
                # Si tiene "BLOCK" o "BLOQUE", es P&D BLOQUE
                if 'BLOCK' in line or 'BLOQUE' in line:
                    product_found = 'P&D BLOQUE'
                # Si tiene "IQF", es P&D IQF
                elif 'IQF' in line:
                    product_found = 'P&D IQF'

            if product_found and size:
                products_found.append({
                    'product': product_found,
                    'size': size,
                    'line': line
                })

        return products_found

    def _detect_products_and_sizes(self, message: str) -> dict:
        """
        Detecta productos y agrupa tallas por producto
        
        Returns:
            dict con 'sizes_by_product' y 'multiple_products'
        """
        message_upper = message.upper()
        
        # Detectar productos mencionados
        products_found = []
        if 'HLSO' in message_upper:
            products_found.append('HLSO')
        if 'HOSO' in message_upper:
            products_found.append('HOSO')
        if 'P&D IQF' in message_upper or 'PD IQF' in message_upper:
            products_found.append('P&D IQF')
        if 'COOKED' in message_upper:
            products_found.append('COOKED')
        
        # Si no hay productos, retornar vacío
        if not products_found:
            return {'sizes_by_product': None, 'multiple_products': False}
        
        # Extraer todas las tallas del mensaje
        all_sizes = re.findall(r'(\d+)[/-](\d+)', message)
        all_sizes_normalized = [f"{s[0]}/{s[1]}" for s in all_sizes]
        
        if not all_sizes_normalized:
            return {'sizes_by_product': None, 'multiple_products': False}
        
        # Si solo hay un producto, asignar todas las tallas a ese producto
        if len(products_found) == 1:
            return {
                'sizes_by_product': {products_found[0]: all_sizes_normalized},
                'multiple_products': False
            }
        
        # Si hay múltiples productos, intentar agrupar tallas por producto
        sizes_by_product = {}
        
        # Buscar tallas cerca de cada producto
        for product in products_found:
            # Buscar el índice donde aparece el producto
            product_index = message_upper.find(product)
            if product_index == -1:
                continue
            
            # Buscar el siguiente producto (o fin del mensaje)
            next_product_index = len(message)
            for other_product in products_found:
                if other_product != product:
                    other_index = message_upper.find(other_product, product_index + len(product))
                    if other_index != -1 and other_index < next_product_index:
                        next_product_index = other_index
            
            # Extraer tallas entre este producto y el siguiente
            product_section = message[product_index:next_product_index]
            product_sizes = re.findall(r'(\d+)[/-](\d+)', product_section)
            product_sizes_normalized = [f"{s[0]}/{s[1]}" for s in product_sizes]
            
            if product_sizes_normalized:
                sizes_by_product[product] = product_sizes_normalized
        
        # Si no se pudieron agrupar, dividir equitativamente
        if not sizes_by_product:
            sizes_per_product = len(all_sizes_normalized) // len(products_found)
            for i, product in enumerate(products_found):
                start_idx = i * sizes_per_product
                end_idx = start_idx + sizes_per_product if i < len(products_found) - 1 else len(all_sizes_normalized)
                sizes_by_product[product] = all_sizes_normalized[start_idx:end_idx]
        
        return {
            'sizes_by_product': sizes_by_product,
            'multiple_products': len(products_found) > 1
        }
    
    def _basic_intent_analysis(self, message: str) -> dict:
        """
        Análisis básico de intenciones sin IA como fallback
        IMPORTANTE: Detectar cotizaciones ANTES que saludos para evitar falsos positivos
        """
        message_lower = message.lower().strip()

        # PRIMERO: Detectar si hay tallas (fuerte indicador de cotización)
        # Soporta formatos: 16/20, 16-20, 21/25, 21-25, etc.
        has_size = bool(re.search(r'\b\d+[/-]\d+\b', message_lower))
        
        # SEGUNDO: Detectar términos de cotización/precio
        proforma_keywords = [
            'proforma', 'cotizacion', 'cotizar', 'quote', 'precio', 'precios',
            'necesito', 'quiero', 'contenedor', 'cfr', 'cif', 'fob',
            'cocedero', 'cocido', 'lagostino', 'vannamei', 'inteiro', 'colas'
        ]
        has_quote_keywords = any(keyword in message_lower for keyword in proforma_keywords)
        
        # Si tiene tallas O términos de cotización, NO es solo un saludo
        # Continuar con el análisis de cotización
        is_likely_quote = has_size or has_quote_keywords
        
        # Patrones de saludo (con límites de palabra para evitar falsos positivos)
        # SOLO considerar saludo si NO tiene indicadores de cotización
        greeting_patterns = [r'\bhola\b', r'\bhello\b', r'\bhi\b', r'\bbuenos\b', r'\bbuenas\b',
                           r'\bcomo estas\b', r'\bque tal\b', r'\bq haces\b']
        has_greeting = any(re.search(pattern, message_lower) for pattern in greeting_patterns)
        
        if has_greeting and not is_likely_quote:
            return {
                "intent": "greeting",
                "product": None,
                "size": None,
                "quantity": None,
                "destination": None,
                "confidence": 0.8,
                "suggested_response": "Responder con saludo amigable y mostrar opciones"
            }

        # Detectar solicitudes de modificación de flete
        # IMPORTANTE: Solo detectar cuando hay verbos de modificación explícitos
        # NO detectar solicitudes nuevas que incluyen flete
        modify_flete_patterns = [
            r'\bmodifica.*flete', r'\bcambiar.*flete', r'\bactualizar.*flete',
            r'\bnuevo.*flete', r'\botro.*flete', r'\bflete.*diferente',
            r'\bmodify.*freight', r'\bchange.*freight', r'\bupdate.*freight',
        ]

        # Verificar que NO sea una solicitud nueva de cotización/proforma
        new_quote_keywords = ['cotizar', 'cotizacion', 'proforma', 'quote', 'quotation', 'contenedor']
        is_new_quote = any(keyword in message_lower for keyword in new_quote_keywords)

        is_flete_modification = (
            any(re.search(pattern, message_lower) for pattern in modify_flete_patterns) and
            not is_new_quote  # NO es modificación si es una solicitud nueva
        )

        if is_flete_modification:
            # Extraer el nuevo valor de flete
            flete_custom = None
            flete_patterns = [
                r'flete\s+a\s+(?:\$\s*)?(\d+\.?\d*)',  # "flete a 0.30"
                r'flete\s*(?:de\s*)?(?:\$\s*)?(\d+\.?\d*)',
                r'(\d+\.?\d*)\s*(?:centavos?\s*)?(?:de\s*)?flete',
                r'con\s*(\d+\.?\d*)\s*(?:de\s*)?flete',
                r'freight\s*(?:of\s*)?(?:\$\s*)?(\d+\.?\d*)',
                r'(\d+\.?\d*)\s*freight',
            ]

            for pattern in flete_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    try:
                        flete_custom = float(match.group(1))
                        break
                    except ValueError:
                        continue

            return {
                "intent": "modify_flete",
                "flete_custom": flete_custom,
                "confidence": 0.9,
                "suggested_response": "Modificar flete y regenerar proforma"
            }

        # Patrones de proforma/cotización (lenguaje natural amplio)
        proforma_patterns = [
            # Palabras clave directas
            'proforma', 'cotizacion', 'cotizar', 'quote', 'precio', 'precios',
            # Verbos de acción
            'creame', 'crear', 'generar', 'hazme', 'dame', 'quiero', 'necesito',
            # Consultas de precio
            'precio de', 'precio del', 'precio por', 'cuanto cuesta', 'cuanto vale',
            'cuanto es', 'cual es el precio', 'saber el precio', 'conocer el precio',
            # Variaciones comunes
            'cost', 'value', 'rate', 'tarifa', 'valor', 'costo',
            # Frases específicas
            'envio a', 'con envio', 'para enviar', 'destino', 'shipping'
        ]

        # Detectar si es una consulta de precio/proforma
        is_price_query = any(pattern in message_lower for pattern in proforma_patterns)

        # También detectar si menciona tallas específicas (fuerte indicador)
        has_size = bool(re.search(r'\b\d+/\d+\b', message_lower))

        # Si es consulta de precio O menciona tallas, procesar como proforma
        if is_price_query or has_size:
            # Extraer información básica
            product = None
            size = None
            glaseo_factor = None
            destination = None
            usar_libras = False

            # IMPORTANTE: Detectar si menciona "Cocedero" o "Cocido" como CALIDAD
            # Esto NO define el producto, sino el tipo de procesamiento
            menciona_cocedero = any(term in message_lower for term in ['cocedero', 'cocido', 'cooked', 'cozido'])
            
            # Detectar PRESENTACIÓN del producto (Inteiro vs Colas)
            menciona_inteiro = any(term in message_lower for term in ['inteiro', 'entero', 'whole'])
            menciona_colas = any(term in message_lower for term in ['colas', 'tails', 'tail', 'cola'])
            
            # Lógica inteligente de detección:
            # Si menciona "Cocedero" + "Inteiro" → NO es COOKED, es solicitud compleja
            # Si menciona "Cocedero" + "Colas" → COOKED
            # Si solo menciona "Cocedero" → Solicitar especificar
            
            product = None
            needs_clarification = False
            
            if menciona_cocedero:
                if menciona_inteiro and menciona_colas:
                    # Mensaje complejo con múltiples presentaciones
                    # No asumir producto, dejar que OpenAI lo maneje
                    product = None
                    needs_clarification = True
                elif menciona_inteiro:
                    # "Inteiro Cocedero" → Probablemente HOSO cocido (no común)
                    # Mejor solicitar aclaración
                    product = None
                    needs_clarification = True
                elif menciona_colas:
                    # "Colas Cocedero" → COOKED (colas cocidas)
                    product = 'COOKED'
                else:
                    # Solo "Cocedero" sin especificar presentación
                    product = None
                    needs_clarification = True
            else:
                # No menciona cocedero, usar lógica normal
                # IMPORTANTE: "cola" sin "cocedero" = HLSO (camarón sin cabeza, con cáscara)
                # Solo "cola cocedero" = COOKED (colas cocidas)
                product_patterns = {
                    'HLSO': [
                        'sin cabeza', 'hlso', 'head less', 'headless', 'descabezado',
                        'sin cabezas', 'tipo sin cabeza',
                        # AGREGADO: "cola" sin "cocedero" = HLSO (camarón sin cabeza)
                        'cola', 'colas', 'tail', 'tails'
                    ],
                    'HOSO': [
                        'con cabeza', 'hoso', 'head on', 'entero', 'completo',
                        'con cabezas', 'tipo con cabeza', 'inteiro', 'whole' , 'entero'
                    ],
                    'P&D IQF': [
                        'p&d iqf', 'pd iqf', 'p&d', 'pelado', 'peeled', 'deveined',
                        'limpio', 'procesado', 'pd', 'p d', 'pelado y desvenado',
                        
                    ],
                    'P&D BLOQUE': [
                        'p&d bloque', 'pd bloque', 'bloque', 'block', 'p&d block',
                        'pd block', 'pelado bloque'
                    ],
                    'PuD-EUROPA': [
                        'pud europa', 'pud-europa', 'europa', 'european', 'europeo'
                    ],
                    'EZ PEEL': [
                        'ez peel', 'ez', 'easy peel', 'facil pelado', 'fácil pelado'
                    ],
                    'PuD-EEUU': [
                        'pud eeuu', 'pud-eeuu', 'eeuu', 'usa', 'estados unidos'
                    ],
                    'COOKED': [
                        # REMOVIDO: 'colas', 'tails', 'tail' (ahora solo se detecta con "cocedero")
                        'cooked', 'cocinado', 'preparado'
                    ],
                    'PRE-COCIDO': [
                        'pre-cocido', 'pre cocido', 'precocido', 'pre-cooked', 'pre cooked'
                    ],
                    'COCIDO SIN TRATAR': [
                        'cocido sin tratar', 'sin tratar', 'untreated', 'natural cocido'
                    ]
                }

                # Buscar coincidencias de productos (orden específico para evitar conflictos)
                # IMPORTANTE: P&D IQF debe ir ANTES que COOKED para detectar "cola" correctamente
                specific_order = ['COCIDO SIN TRATAR', 'PRE-COCIDO', 'P&D IQF', 'P&D BLOQUE', 'PuD-EUROPA', 'PuD-EEUU', 'EZ PEEL', 'HLSO', 'HOSO', 'COOKED']

                for prod_name in specific_order:
                    if prod_name in product_patterns:
                        patterns = product_patterns[prod_name]
                        if any(pattern in message_lower for pattern in patterns):
                            product = prod_name
                            break

            # Detectar tallas PRIMERO (antes de la lógica de HOSO)
            size_patterns = [
                r'(\d+/\d+)',  # 21/25
                r'(\d+)\s*sobre\s*(\d+)',  # 21 sobre 25
                r'(\d+)\s*-\s*(\d+)',  # 21-25
                r'(\d+)\s+(\d+)'  # 21 25
            ]

            for pattern in size_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    if len(match.groups()) == 1:
                        size = match.group(1)
                    else:
                        size = f"{match.group(1)}/{match.group(2)}"
                    break

            # Si no se detectó producto pero hay talla específica, inferir por talla
            if not product and size:
                # Tallas que solo existen en HOSO según la tabla de precios
                hoso_exclusive_sizes = ['20/30', '30/40', '40/50', '50/60', '60/70', '70/80']
                if size in hoso_exclusive_sizes:
                    product = 'HOSO'

            # NO asumir producto por defecto para otras tallas - el usuario debe especificarlo

            # Detectar glaseo con patrones más amplios (español e inglés)
            # IMPORTANTE: Detectar también "0%" que significa SIN glaseo
            glaseo_patterns = [
                # Patrones en español
                r'(\d+)\s*(?:de\s*)?glaseo',
                r'glaseo\s*(?:de\s*)?(\d+)',
                r'(\d+)\s*%\s*glaseo',
                r'glaseo\s*(\d+)\s*%',
                r'con\s*(\d+)\s*glaseo',
                r'(\d+)\s*porciento\s*glaseo',
                # Patrones adicionales para "al X%" y "al X"
                r'al\s*(\d+)\s*%',  # "al 20%"
                r'al\s*(\d+)(?:\s|$)',  # "al 20" (sin %)
                r'(\d+)\s*%\s*de\s*glaseo',
                r'(\d+)\s*%\s*glaseo',
                # Patrón para "Inteiro 0%" o "0%" solo
                r'(?:inteiro|entero|colas?|tails?)\s+(\d+)\s*%',  # "Inteiro 0%"
                r'^\s*(\d+)\s*%',  # "0%" al inicio
                # Patrones en inglés
                r'(\d+)g?\s*(?:of\s*)?glaze',
                r'glaze\s*(?:of\s*)?(\d+)g?',
                r'(\d+)\s*%\s*glaze',
                r'glaze\s*(\d+)\s*%',
                r'with\s*(\d+)g?\s*glaze',
                r'(\d+)\s*percent\s*glaze',
                r'at\s*(\d+)\s*%',  # "at 20%"
                r'at\s*(\d+)(?:\s|$)'  # "at 20" (sin %)
            ]

            glaseo_percentage_original = None
            for pattern in glaseo_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    glaseo_percentage_original = int(match.group(1))
                    
                    # CASO ESPECIAL: 0% glaseo = Sin glaseo
                    if glaseo_percentage_original == 0:
                        glaseo_factor = None  # No aplicar glaseo
                        logger.info("🔍 Detectado 0% glaseo → Sin glaseo (CFR simple)")
                    else:
                        # Convertir porcentaje a factor usando fórmula general
                        # Factor = 1 - (percentage / 100)
                        # Ejemplo: 15% glaseo → factor = 1 - 0.15 = 0.85
                        glaseo_factor = 1 - (glaseo_percentage_original / 100)
                    break

            # Detectar si menciona DDP (precio que YA incluye flete)
            # DDP = Delivered Duty Paid (precio incluye todo: flete, impuestos, etc.)
            # IMPORTANTE: Si dice DDP, necesitamos el valor del flete para desglosar el precio
            ddp_patterns = [
                r'\bddp\b',  # DDP con límites de palabra
                r'ddp\s',    # DDP seguido de espacio
                r'\sddp',    # DDP precedido de espacio
                r'precio\s+ddp',
                r'ddp\s+price',
                r'delivered\s+duty\s+paid'
            ]
            menciona_ddp = any(re.search(pattern, message_lower) for pattern in ddp_patterns)

            # Detectar valores numéricos de flete
            flete_custom = None
            flete_patterns = [
                r'flete\s*(?:de\s*)?(?:\$\s*)?(\d+\.?\d*)',  # "flete de 0.20", "flete $0.20"
                r'(\d+\.?\d*)\s*(?:centavos?\s*)?(?:de\s*)?flete',  # "0.20 centavos de flete"
                r'con\s*(\d+\.?\d*)\s*(?:de\s*)?flete',  # "con 0.20 de flete"
                r'freight\s*(?:of\s*)?(?:\$\s*)?(\d+\.?\d*)',  # "freight 0.20", "freight $0.20"
                r'(\d+\.?\d*)\s*freight',  # "0.20 freight"
            ]

            # Extraer valor de flete si se menciona
            for pattern in flete_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    try:
                        flete_custom = float(match.group(1))
                        break
                    except ValueError:
                        continue

            # Detectar destinos si se menciona flete, DDP, CFR o CIF
            flete_keywords = ['flete', 'freight', 'envio', 'envío', 'shipping', 'transporte', 'ddp', 'cfr', 'cif', 'c&f']
            menciona_flete = any(keyword in message_lower for keyword in flete_keywords)

            if menciona_flete:
                destination_patterns = {
                    # Ciudades USA
                    'Houston': ['houston', 'houton', 'huston'],
                    'Miami': ['miami', 'maiami', 'florida'],
                    'New York': ['new york', 'nueva york', 'ny', 'newyork'],
                    'Los Angeles': ['los angeles', 'california'],  # Removido 'la' genérico
                    'Chicago': ['chicago', 'chicaco'],
                    'Dallas': ['dallas', 'dalas'],

                    # Ciudades Europa
                    'Lisboa': ['lisboa', 'lisbon', 'portugal'],
                    'Madrid': ['madrid', 'españa', 'spain'],
                    'Barcelona': ['barcelona'],
                    'Paris': ['paris', 'france', 'francia'],
                    'Londres': ['londres', 'london', 'uk', 'reino unido'],
                    'Roma': ['roma', 'rome', 'italy', 'italia'],
                    'Berlin': ['berlin', 'germany', 'alemania'],
                    'Amsterdam': ['amsterdam', 'netherlands', 'holanda'],

                    # Países y regiones
                    'China': ['china', 'beijing', 'shanghai'],
                    'Japón': ['japon', 'japón', 'japan', 'tokyo', 'nippon'],
                    'Europa': ['europa', 'europe'],
                    'Brasil': ['brasil', 'brazil', 'sao paulo', 'rio'],
                    'México': ['mexico', 'méxico', 'guadalajara', 'monterrey'],
                    'Canadá': ['canada', 'toronto', 'vancouver'],
                    'Australia': ['australia', 'sydney', 'melbourne'],
                    'Corea': ['corea', 'korea', 'seoul'],
                    'India': ['india', 'mumbai', 'delhi'],
                    'Tailandia': ['tailandia', 'thailand', 'bangkok'],
                    'Vietnam': ['vietnam', 'ho chi minh'],
                    'Singapur': ['singapur', 'singapore'],
                    'Filipinas': ['filipinas', 'philippines', 'manila'],
                    'Indonesia': ['indonesia', 'jakarta'],
                    'Malasia': ['malasia', 'malaysia', 'kuala lumpur']
                }

                # Buscar destinos USA solo si menciona flete
                for dest_name, patterns in destination_patterns.items():
                    if any(pattern in message_lower for pattern in patterns):
                        if dest_name == 'Houston':
                            usar_libras = False  # Houston es excepción: USA pero usa kilos
                        else:
                            usar_libras = True  # Otras ciudades USA usan libras
                        destination = dest_name
                        break

            # También detectar patrones de envío específicos (solo si ya menciona flete)
            if menciona_flete and not destination:
                # Patrones más específicos para detectar destinos (incluyendo CFR/CIF)
                envio_specific_patterns = [
                    r'cfr\s+([a-záéíóúñ\w\s]+?)(?:\s+para|\s+con|\s+de|$)',        # "CFR Lisboa"
                    r'cif\s+([a-záéíóúñ\w\s]+?)(?:\s+para|\s+con|\s+de|$)',        # "CIF Lisboa"
                    r'c&f\s+([a-záéíóúñ\w\s]+?)(?:\s+para|\s+con|\s+de|$)',        # "C&F Lisboa"
                    r'flete\s+a\s+([a-záéíóúñ\w\s]+?)(?:\s+para|\s+con|\s+de|$)',  # "flete a japón"
                    r'envio\s+a\s+([a-záéíóúñ\w\s]+?)(?:\s+para|\s+con|\s+de|$)',  # "envío a china"
                    r'hacia\s+([a-záéíóúñ\w\s]+?)(?:\s+para|\s+con|\s+de|$)',      # "hacia europa"
                    r'shipping\s+to\s+([a-zA-Z\s]+?)(?:\s+for|\s+with|$)',         # "shipping to japan"
                ]

                for pattern in envio_specific_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        dest_detected = match.group(1).strip()

                        # Verificar si coincide con algún destino conocido
                        for dest_name, patterns in destination_patterns.items():
                            if any(p in dest_detected for p in patterns):
                                destination = dest_name
                                # Configurar usar_libras según el destino
                                if dest_name in ['Houston', 'Miami', 'New York', 'Los Angeles', 'Chicago', 'Dallas']:
                                    usar_libras = True if dest_name != 'Houston' else False
                                else:
                                    usar_libras = False  # Países internacionales usan kilos
                                break

                        # Si no coincide con destinos conocidos, usar el texto detectado
                        if not destination:
                            destination = dest_detected.title()
                            usar_libras = False  # Por defecto kilos para destinos desconocidos
                        break
                envio_patterns = [
                    r'flete a ([a-zA-Z\s]+)', r'envio a ([a-zA-Z\s]+)', r'enviar a ([a-zA-Z\s]+)',
                    r'shipping to ([a-zA-Z\s]+)', r'con flete a ([a-zA-Z\s]+)'
                ]

                destination_patterns = {
                    'Houston': ['houston', 'houton', 'huston'],
                    'Miami': ['miami', 'maiami', 'florida'],
                    'New York': ['new york', 'nueva york', 'ny', 'newyork'],
                    'Los Angeles': ['los angeles', 'la', 'california'],
                    'Chicago': ['chicago', 'chicaco'],
                    'Dallas': ['dallas', 'dalas']
                }

                for pattern in envio_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        dest_word = match.group(1).lower().strip()
                        # Verificar si es una ciudad USA conocida
                        for dest_name, patterns in destination_patterns.items():
                            if any(p in dest_word for p in patterns):
                                if dest_name == 'Houston':
                                    usar_libras = False  # Houston usa kilos
                                else:
                                    usar_libras = True  # Otras ciudades USA usan libras
                                destination = dest_name
                                break
                        if not destination:
                            destination = dest_word.title()
                        break

            # Detectar nombre del cliente con patrones más amplios (español e inglés)
            cliente_nombre = None
            cliente_patterns = [
                # Patrones en español
                r'cliente\s+([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+para|\s+precio|$)',
                r'para\s+(?:el\s+cliente\s+)?([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)',
                r'proforma\s+para\s+(?:el\s+cliente\s+)?([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)',
                r'cotizacion\s+para\s+([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)',
                r'señor\s+([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)',
                r'sr\s+([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)',
                # Patrones en inglés
                r'client\s+([a-záéíóúñ\w\s]+?)(?:\s+with|\s+for|\s+price|$)',
                r'for\s+(?:the\s+client\s+)?([a-záéíóúñ\w\s]+?)(?:\s+with|\s+for|\s+price|$)',
                r'proforma\s+for\s+(?:the\s+client\s+)?([a-záéíóúñ\w\s]+?)(?:\s+with|\s+for|\s+price|$)',
                r'quote\s+for\s+([a-záéíóúñ\w\s]+?)(?:\s+with|\s+for|\s+price|$)',
                r'mr\s+([a-záéíóúñ\w\s]+?)(?:\s+with|\s+for|\s+price|$)',
                r'mrs\s+([a-záéíóúñ\w\s]+?)(?:\s+with|\s+for|\s+price|$)'
            ]

            for pattern in cliente_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    cliente_nombre = match.group(1).strip()
                    # Limpiar palabras comunes que no son nombres (español e inglés)
                    stop_words = [
                        'el', 'la', 'con', 'de', 'para', 'precio', 'tipo', 'glaseo',
                        'flete', 'producto', 'talla', 'envio', 'destino', 'kilo', 'kilos',
                        'the', 'with', 'for', 'price', 'type', 'glaze', 'freight',
                        'product', 'size', 'shipping', 'destination'
                    ]
                    cliente_words = [word for word in cliente_nombre.split() if word not in stop_words]
                    if cliente_words and len(' '.join(cliente_words)) > 2:
                        cliente_nombre = ' '.join(cliente_words)
                        break

            # Detectar idioma
            english_keywords = ['quote', 'price', 'cost', 'freight', 'shipping', 'quotation', 'shrimp', 'product']
            spanish_keywords = ['proforma', 'cotizacion', 'precio', 'flete', 'envio', 'camaron', 'producto', 'glaseo']

            english_count = sum(1 for keyword in english_keywords if keyword in message_lower)
            spanish_count = sum(1 for keyword in spanish_keywords if keyword in message_lower)

            language = "en" if english_count > spanish_count else "es"

            # Detectar tipo de procesamiento (BRINE, etc.)
            processing_type = None
            processing_patterns = {
                'BRINE': ['brine', 'salmuera', 'salmoura'],
                'IQF': ['iqf', 'individual', 'individually'],
                'BLOCK': ['bloque', 'block', 'bloques']
            }
            
            for proc_type, patterns in processing_patterns.items():
                if any(pattern in message_lower for pattern in patterns):
                    processing_type = proc_type
                    break
            
            # Detectar porcentaje de peso neto (NET)
            net_weight_percentage = None
            net_patterns = [
                r'(\d+)\s*%\s*net',  # "100% NET"
                r'net\s*(\d+)\s*%',  # "NET 100%"
                r'(\d+)\s*%\s*neto',  # "100% neto"
                r'neto\s*(\d+)\s*%',  # "neto 100%"
            ]
            
            for pattern in net_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    net_weight_percentage = int(match.group(1))
                    break
            
            # Detectar cantidad con formatos variados
            quantity = None
            quantity_patterns = [
                r'(\d+(?:,\d{3})*)\s*(?:libras?|lb|lbs)',
                r'(\d+(?:,\d{3})*)\s*(?:kilos?|kg|kgs)',
                r'(\d+(?:,\d{3})*)\s*(?:toneladas?|tons?)',
                r'(\d+(?:\.\d+)?)\s*(?:mil|thousand)',
                r'(\d+(?:,\d{3})*)\s*(?:pounds?)',
                r'(\d+)k/caja',  # "20k/caja"
                r'(\d+)kg/caja',  # "20kg/caja"
            ]

            for pattern in quantity_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    quantity_value = match.group(1)
                    # Si es formato "20k/caja", convertir a kg
                    if 'k/caja' in message_lower or 'kg/caja' in message_lower:
                        quantity = f"{int(quantity_value) * 1000} kg/caja"
                    else:
                        quantity = quantity_value
                    break

            # Detectar múltiples productos y agrupar tallas
            products_detection = self._detect_products_and_sizes(message)
            sizes_by_product = products_detection.get('sizes_by_product')
            multiple_products = products_detection.get('multiple_products', False)
            
            # Determinar confianza basada en información extraída
            confidence = 0.6  # Base
            if size: confidence += 0.2
            if product: confidence += 0.1
            if destination: confidence += 0.1
            if glaseo_factor: confidence += 0.1
            if sizes_by_product: confidence += 0.1

            return {
                "intent": "proforma",
                "product": product,
                "size": size,
                "sizes_by_product": sizes_by_product,  # Tallas agrupadas por producto
                "multiple_products": multiple_products,  # Flag de múltiples productos
                "quantity": quantity,
                "destination": destination,
                "glaseo_factor": glaseo_factor,
                "glaseo_percentage": glaseo_percentage_original,  # Porcentaje original solicitado
                "flete_custom": flete_custom,  # Valor de flete personalizado detectado
                "is_ddp": menciona_ddp,  # Flag para indicar que es precio DDP (ya incluye flete)
                "usar_libras": usar_libras,
                "cliente_nombre": cliente_nombre,
                "processing_type": processing_type,  # Tipo de procesamiento (BRINE, IQF, etc.)
                "net_weight_percentage": net_weight_percentage,  # Porcentaje de peso neto
                "wants_proforma": True,
                "language": language,  # Idioma detectado
                "confidence": min(confidence, 0.95),  # Máximo 0.95
                "suggested_response": "Procesar proforma con datos extraídos"
            }

        # Patrones de productos
        product_patterns = ['producto', 'productos', 'camaron', 'camarones', 'hlso', 'hoso', 'p&d']
        if any(pattern in message_lower for pattern in product_patterns):
            return {
                "intent": "product_info",
                "product": None,
                "size": None,
                "quantity": None,
                "destination": None,
                "confidence": 0.7,
                "suggested_response": "Mostrar información de productos"
            }

        # Patrones de ayuda
        help_patterns = ['ayuda', 'help', 'como', 'que puedes', 'opciones', '?']
        if any(pattern in message_lower for pattern in help_patterns):
            return {
                "intent": "help",
                "product": None,
                "size": None,
                "quantity": None,
                "destination": None,
                "confidence": 0.8,
                "suggested_response": "Mostrar menú de ayuda"
            }

        return {
            "intent": "unknown",
            "product": None,
            "size": None,
            "quantity": None,
            "destination": None,
            "confidence": 0.3,
            "suggested_response": "Mostrar menú principal"
        }

    def get_smart_fallback_response(self, user_message: str, intent_data: dict) -> str | None:
        """
        Genera respuestas inteligentes sin IA basadas en patrones
        """
        intent = intent_data.get('intent', 'unknown')
        message_lower = user_message.lower().strip()

        if intent == 'greeting':
            # Respuesta rápida y directa para saludos
            return "¡Hola! 🦐 ¿Qué producto de camarón necesitas? Te genero la cotización al instante 💰"

        elif intent == 'pricing':
            return "💰 ¡Perfecto! ¿Qué producto necesitas? HLSO es muy popular. Escribe 'precios' para ver tallas y crear tu proforma 📋"

        elif intent == 'product_info':
            return "🦐 Tenemos HLSO, P&D IQF, HOSO y más. ¿Cuál te interesa? Te genero la cotización con precios FOB actualizados 💰"

        elif intent == 'help':
            return "🤖 Te ayudo a crear proformas de camarón:\n• Precios FOB actualizados\n• Todas las tallas disponibles\n• PDF profesional\n\n¿Qué producto necesitas? 🦐"

        else:
            return "🦐 ¡Hola! Soy ShrimpBot de BGR Export. ¿Qué camarón necesitas? Te genero la proforma al instante 📋💰"

    def _clean_problematic_emojis(self, text: str) -> str:
        """
        Limpia emojis que pueden causar problemas de codificación en WhatsApp
        """
        # Lista de emojis problemáticos y sus reemplazos
        problematic_emojis = {
            '🤑': '💰',  # Reemplazar cara con dinero por bolsa de dinero
            '🤖': '🦐',  # Reemplazar robot por camarón
            '💸': '💰',  # Reemplazar dinero volando por bolsa de dinero
            '🤔': '🤝',  # Reemplazar cara pensando por apretón de manos
        }

        cleaned_text = text
        for problematic, replacement in problematic_emojis.items():
            cleaned_text = cleaned_text.replace(problematic, replacement)

        return cleaned_text

    def _make_request_with_retry(self, messages: list[dict], max_tokens: int = 300, temperature: float = 0.3, max_retries: int = 3) -> str | None:
        """
        Hace petición a OpenAI con reintentos automáticos
        """
        for attempt in range(max_retries):
            try:
                result = self._make_request(messages, max_tokens, temperature)
                if result:
                    return result

                # Si falla, esperar un poco antes de reintentar
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1 * (attempt + 1))  # Backoff exponencial

            except Exception as e:
                logger.warning(f"⚠️ Intento {attempt + 1}/{max_retries} falló: {str(e)}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1 * (attempt + 1))

        return None

    def _intelligent_fallback(self, user_message: str, session_data: dict = None) -> dict:
        """
        Fallback inteligente que SIEMPRE responde algo coherente
        Maneja cualquier tipo de solicitud del usuario
        """
        message_lower = user_message.lower().strip()

        # Detectar saludos
        greeting_patterns = [r'\bhola\b', r'\bhello\b', r'\bhi\b', r'\bbuenos\b', r'\bbuenas\b',
                           r'\bhey\b', r'\bqué tal\b', r'\bcómo estás\b']
        if any(re.search(pattern, message_lower) for pattern in greeting_patterns):
            return {
                "response": "¡Hola! 👋 Soy ShrimpBot de BGR Export 🦐\n\n¿Qué producto necesitas? Te ayudo a crear tu cotización al instante 💰",
                "action": "greeting",
                "data": {}
            }

        # Detectar solicitudes de audio/voz
        audio_patterns = ['audio', 'voz', 'voice', 'nota de voz', 'mensaje de voz', 'grabación']
        if any(pattern in message_lower for pattern in audio_patterns):
            return {
                "response": "🎤 ¡Claro! Puedes enviarme notas de voz y las procesaré automáticamente.\n\nSolo envía tu audio y te responderé con la información que necesites 🦐",
                "action": "audio_info",
                "data": {}
            }

        # Detectar preguntas sobre productos
        product_patterns = ['producto', 'productos', 'qué tienen', 'qué venden', 'catálogo', 'opciones']
        if any(pattern in message_lower for pattern in product_patterns):
            return {
                "response": "🦐 Productos disponibles:\n\n• HLSO (sin cabeza)\n• HOSO (con cabeza)\n• P&D IQF (pelado)\n• P&D BLOQUE\n• EZ PEEL\n• PuD-EUROPA\n• COOKED\n\n¿Cuál te interesa? 💰",
                "action": "product_list",
                "data": {}
            }

        # Detectar preguntas sobre precios
        price_patterns = ['precio', 'precios', 'cuánto', 'cuanto', 'costo', 'cost', 'value']
        if any(pattern in message_lower for pattern in price_patterns):
            return {
                "response": "💰 Te genero cotizaciones con precios FOB actualizados.\n\n¿Qué producto y talla necesitas?\nEjemplo: HLSO 16/20 🦐",
                "action": "price_inquiry",
                "data": {}
            }

        # Detectar solicitudes de ayuda
        help_patterns = ['ayuda', 'help', 'cómo', 'como funciona', 'qué puedes', 'opciones']
        if any(pattern in message_lower for pattern in help_patterns):
            return {
                "response": "🤖 Te ayudo a crear proformas de camarón:\n\n✅ Precios FOB actualizados\n✅ Todas las tallas\n✅ PDF profesional\n✅ Cálculo de glaseo\n✅ Flete incluido\n\n¿Qué producto necesitas? 🦐",
                "action": "help",
                "data": {}
            }

        # Detectar agradecimientos
        thanks_patterns = ['gracias', 'thanks', 'thank you', 'muchas gracias', 'te agradezco']
        if any(pattern in message_lower for pattern in thanks_patterns):
            return {
                "response": "¡De nada! 😊 Estoy aquí para ayudarte.\n\n¿Necesitas algo más? 🦐",
                "action": "thanks",
                "data": {}
            }

        # Detectar despedidas
        goodbye_patterns = ['adiós', 'adios', 'bye', 'chao', 'hasta luego', 'nos vemos']
        if any(pattern in message_lower for pattern in goodbye_patterns):
            return {
                "response": "¡Hasta pronto! 👋 Cuando necesites cotizaciones, aquí estaré 🦐💰",
                "action": "goodbye",
                "data": {}
            }

        # Detectar tallas específicas (intento de cotización)
        if re.search(r'\d+/\d+', message_lower):
            return {
                "response": "📊 Detecté una talla en tu mensaje.\n\n¿Qué producto necesitas?\n• HLSO (sin cabeza)\n• HOSO (con cabeza)\n• P&D IQF (pelado)\n\nEscribe el producto para generar tu cotización 🦐",
                "action": "size_detected",
                "data": {}
            }

        # Si tiene contexto de sesión, usar eso
        if session_data and session_data.get('products'):
            products = session_data['products']
            products_str = ", ".join([f"{p['product']} {p['size']}" for p in products])
            return {
                "response": f"📋 Tienes en tu sesión: {products_str}\n\n¿Quieres generar la proforma o modificar algo? 🦐",
                "action": "session_context",
                "data": session_data
            }

        # Respuesta genérica pero útil para CUALQUIER otra cosa
        return {
            "response": "🦐 Soy ShrimpBot de BGR Export.\n\nTe ayudo a crear cotizaciones de camarón premium.\n\n¿Qué producto necesitas?\nEjemplo: HLSO 16/20 💰",
            "action": "general_inquiry",
            "data": {}
        }

    def process_audio_message(self, audio_file_path: str, session_data: dict = None, conversation_history: list[dict] = None) -> dict:
        """
        Procesa un mensaje de audio completo: transcribe y responde
        
        Args:
            audio_file_path: Ruta al archivo de audio
            session_data: Datos de la sesión actual
            conversation_history: Historial de conversación
        
        Returns:
            Dict con transcripción, respuesta y acciones
        """
        try:
            # Transcribir audio
            transcription = self.transcribe_audio(audio_file_path)

            if not transcription:
                return {
                    "response": "🎤 No pude entender el audio. ¿Podrías enviarlo de nuevo o escribir tu mensaje? 🦐",
                    "action": "audio_transcription_failed",
                    "data": {},
                    "transcription": None
                }

            logger.info(f"✅ Audio transcrito: '{transcription}'")

            # Procesar el mensaje transcrito
            result = self.handle_any_request(transcription, session_data, conversation_history)

            # Agregar transcripción al resultado
            result['transcription'] = transcription
            result['input_type'] = 'audio'

            return result

        except Exception as e:
            logger.error(f"❌ Error procesando audio: {str(e)}")
            return {
                "response": "🎤 Hubo un problema con el audio. Por favor intenta de nuevo o escribe tu mensaje 🦐",
                "action": "audio_processing_error",
                "data": {},
                "transcription": None
            }

    def handle_any_request(self, user_message: str, session_data: dict = None, conversation_history: list[dict] = None) -> dict:
        """
        MÉTODO PRINCIPAL: Maneja CUALQUIER tipo de solicitud del usuario
        Garantiza que siempre haya una respuesta coherente
        
        Args:
            user_message: Mensaje del usuario (texto o transcripción de audio)
            session_data: Datos de la sesión actual
            conversation_history: Historial de conversación
        
        Returns:
            Dict con respuesta garantizada y acciones
        """
        try:
            # Validar entrada
            if not user_message or not user_message.strip():
                return {
                    "response": "🤔 No recibí ningún mensaje. ¿Podrías escribir o enviar audio de nuevo? 🦐",
                    "action": "empty_message",
                    "data": {}
                }

            # Limpiar mensaje
            user_message = user_message.strip()

            # Intentar con IA primero
            if self.is_available():
                try:
                    result = self.chat_with_context(user_message, conversation_history, session_data)
                    if result and result.get('response'):
                        return result
                except Exception as e:
                    logger.warning(f"⚠️ Error en IA, usando fallback: {str(e)}")

            # Si falla IA o no está disponible, usar fallback inteligente
            return self._intelligent_fallback(user_message, session_data)

        except Exception as e:
            logger.error(f"❌ Error crítico en handle_any_request: {str(e)}")
            # Última línea de defensa: respuesta de emergencia
            return {
                "response": "🦐 Soy ShrimpBot de BGR Export.\n\n¿Qué producto de camarón necesitas? Te ayudo a crear tu cotización 💰",
                "action": "emergency_fallback",
                "data": {}
            }
