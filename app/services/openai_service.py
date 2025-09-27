import requests
import os
import logging
import json
import re
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-3.5-turbo"
        self.whisper_model = "whisper-1"
        self.base_url = "https://api.openai.com/v1"
        
        if self.api_key:
            logger.info("✅ OpenAI API configurada correctamente")
        else:
            logger.warning("⚠️ OpenAI API Key no configurada")
    
    def is_available(self) -> bool:
        """Verifica si OpenAI está disponible"""
        return bool(self.api_key)
    
    def _make_request(self, messages: List[Dict], max_tokens: int = 300, temperature: float = 0.3) -> Optional[str]:
        """
        Hace una petición directa a la API de OpenAI usando requests
        """
        if not self.is_available():
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"❌ Error API OpenAI: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error en petición OpenAI: {str(e)}")
            return None
    
    def analyze_user_intent(self, message: str, context: Dict = None) -> Dict:
        """
        Analiza la intención del usuario usando GPT-4o mini
        """
        if not self.is_available():
            # Fallback con análisis básico de patrones
            return self._basic_intent_analysis(message)
        
        try:
            system_prompt = """
Eres un asistente especializado en análisis de solicitudes de exportación de camarón para BGR Export.

EXTRAE INFORMACIÓN ESPECÍFICA:

PRODUCTOS: HOSO, HLSO, P&D IQF, P&D BLOQUE, PuD-EUROPA, EZ PEEL, PuD-EEUU, COOKED, PRE-COCIDO, COCIDO SIN TRATAR
TALLAS: U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40, 40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90

DESTINOS USA (usan libras): Houston, Miami, Los Angeles, New York, Chicago, Dallas, etc.
OTROS DESTINOS (usan kilos): Europa, China, Japón, etc.

PARÁMETROS CRÍTICOS A EXTRAER (TODOS DINÁMICOS):
- Glaseo: "10 de glaseo", "glaseo 10%", "glaseo 0.15", "con 15 glaseo" → extraer valor decimal exacto
- Flete: "flete 0.25", "con flete 0.30", "flete Houston" → extraer valor numérico si se especifica
- Precio base: "precio base 5.50", "base 6.20", "precio 4.80" → extraer valor si se menciona
- Cantidad: "15000 lb", "10 toneladas", "5000 kilos" → extraer número y unidad
- Cliente: "para [nombre]", "cliente [nombre]", "empresa [nombre]"

REGLAS IMPORTANTES:
- El usuario puede especificar TODOS los valores: glaseo, flete, precio base
- Si menciona "proforma" o "cotización" → intent: "proforma"
- Si destino es USA → usar_libras: true, aplicar flete_base: 0.13 (0.29/2.2)
- Si destino NO es USA → usar_libras: false, aplicar flete_base: 0.29
- Extraer valores numéricos EXACTOS que mencione el usuario
- Si no especifica un valor → null (el sistema NO usará defaults fijos)

EJEMPLOS DE EXTRACCIÓN:
"Proforma 20/30 HOSO glaseo 10% flete Houston" → glaseo_factor: 0.10, usar_libras: true
"Cotización con glaseo 15% y flete 0.25" → glaseo_factor: 0.15, flete_custom: 0.25
"Precio base 5.50 con glaseo 0.12" → precio_base_custom: 5.50, glaseo_factor: 0.12
"HLSO 16/20 glaseo 8% flete 0.20" → glaseo_factor: 0.08, flete_custom: 0.20

Responde SOLO en formato JSON válido:
{
    "intent": "pricing|proforma|product_info|greeting|help|contact|other",
    "product": "producto exacto o null",
    "size": "talla exacta o null", 
    "quantity": "cantidad con unidad o null",
    "destination": "ciudad/país específico o null",
    "glaseo_factor": "valor decimal (ej: 0.10) o null",
    "flete_custom": "valor de flete personalizado o null",
    "precio_base_custom": "precio base personalizado o null",
    "usar_libras": true/false,
    "cliente_nombre": "nombre del cliente o null",
    "wants_proforma": true/false,
    "confidence": 0.95,
    "suggested_response": "respuesta sugerida"
}
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Mensaje: '{message}'"}
            ]
            
            result = self._make_request(messages, max_tokens=300, temperature=0.3)
            
            if result:
                # Intentar parsear como JSON
                try:
                    parsed_result = json.loads(result)
                    logger.info(f"🤖 Análisis OpenAI: {parsed_result}")
                    return parsed_result
                except json.JSONDecodeError:
                    logger.error(f"❌ Error parseando JSON de OpenAI: {result}")
                    return {"intent": "unknown", "confidence": 0}
            else:
                return {"intent": "unknown", "confidence": 0}
            
        except Exception as e:
            logger.error(f"❌ Error en análisis OpenAI: {str(e)}")
            return {"intent": "unknown", "confidence": 0}
    
    def generate_smart_response(self, user_message: str, context: Dict, price_data: Dict = None) -> Optional[str]:
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
- Para saludos: responde amigablemente Y pregunta qué producto necesita
- Solo pregunta información faltante si es absolutamente necesaria
- Si tienes producto y talla, di: "¡Perfecto! Generando tu proforma de [producto] [talla]..."
- Menciona que puedes generar cotizaciones con precios FOB actualizados
- Mantén respuestas bajo 150 caracteres para WhatsApp
- NO pidas cantidad si ya tienes producto y talla - genera la proforma directamente

REGLA CRÍTICA: Si detectas producto + talla en el mensaje, NUNCA pidas más información.

OBJETIVO: Generar proformas inmediatamente cuando tengas datos suficientes.
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_info}
            ]
            
            result = self._make_request(messages, max_tokens=200, temperature=0.7)
            
            if result:
                logger.info(f"🤖 Respuesta generada por OpenAI: {result}")
                return result
            else:
                return None
            
        except Exception as e:
            logger.error(f"❌ Error generando respuesta OpenAI: {str(e)}")
            return None
    
    def enhance_price_explanation(self, price_data: Dict) -> Optional[str]:
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
    
    def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio usando OpenAI Whisper
        """
        if not self.is_available():
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': audio_file,
                    'model': (None, self.whisper_model),
                    'language': (None, 'es')  # Español
                }
                
                response = requests.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                transcription = result.get('text', '').strip()
                logger.info(f"🎤 Audio transcrito: '{transcription}'")
                return transcription
            else:
                logger.error(f"❌ Error transcribiendo audio: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error en transcripción de audio: {str(e)}")
            return None
    
    def _basic_intent_analysis(self, message: str) -> Dict:
        """
        Análisis básico de intenciones sin IA como fallback
        """
        message_lower = message.lower().strip()
        
        # Patrones de saludo
        greeting_patterns = ['hola', 'hello', 'hi', 'buenos', 'buenas', 'como estas', 'que tal', 'q haces']
        if any(pattern in message_lower for pattern in greeting_patterns):
            return {
                "intent": "greeting",
                "product": None,
                "size": None,
                "quantity": None,
                "destination": None,
                "confidence": 0.8,
                "suggested_response": "Responder con saludo amigable y mostrar opciones"
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
            
            # Detectar productos con patrones más amplios
            product_patterns = {
                'HLSO': [
                    'sin cabeza', 'hlso', 'head less', 'headless', 'descabezado',
                    'sin cabezas', 'decapitado', 'tipo sin cabeza'
                ],
                'HOSO': [
                    'con cabeza', 'hoso', 'head on', 'entero', 'completo',
                    'con cabezas', 'tipo con cabeza'
                ],
                'P&D IQF': [
                    'p&d', 'pelado', 'peeled', 'deveined', 'limpio', 'procesado',
                    'pd', 'p d', 'pelado y desvenado'
                ]
            }
            
            # Buscar coincidencias de productos
            for prod_name, patterns in product_patterns.items():
                if any(pattern in message_lower for pattern in patterns):
                    product = prod_name
                    break
            
            # Si no se detectó producto específico pero menciona "producto" o "tipo", usar HLSO por defecto
            if not product and any(word in message_lower for word in ['producto', 'tipo', 'camaron', 'camarones']):
                product = 'HLSO'  # Más común
            
            # Detectar tallas
            size_match = re.search(r'(\d+/\d+)', message_lower)
            if size_match:
                size = size_match.group(1)
            
            # Detectar glaseo con patrones más amplios
            glaseo_patterns = [
                r'(\d+)\s*(?:de\s*)?glaseo',
                r'glaseo\s*(?:de\s*)?(\d+)',
                r'(\d+)\s*%\s*glaseo',
                r'glaseo\s*(\d+)\s*%',
                r'con\s*(\d+)\s*glaseo',
                r'(\d+)\s*porciento\s*glaseo'
            ]
            
            for pattern in glaseo_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    glaseo_factor = float(match.group(1)) / 100
                    break
            
            # Detectar destinos con patrones más amplios
            destination_patterns = {
                'Houston': ['houston', 'houton', 'huston'],
                'Miami': ['miami', 'maiami', 'florida'],
                'New York': ['new york', 'nueva york', 'ny', 'newyork'],
                'Los Angeles': ['los angeles', 'la', 'california'],
                'Chicago': ['chicago', 'chicaco'],
                'Dallas': ['dallas', 'dalas']
            }
            
            # Buscar destinos USA
            for dest_name, patterns in destination_patterns.items():
                if any(pattern in message_lower for pattern in patterns):
                    usar_libras = True  # Todas las ciudades USA usan libras
                    destination = dest_name
                    break
            
            # También detectar patrones de envío
            envio_patterns = [
                r'envio a (\w+)', r'enviar a (\w+)', r'destino (\w+)', 
                r'para (\w+)', r'shipping to (\w+)', r'con envio a (\w+)'
            ]
            
            if not destination:
                for pattern in envio_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        dest_word = match.group(1).lower()
                        # Verificar si es una ciudad USA conocida
                        for dest_name, patterns in destination_patterns.items():
                            if dest_word in patterns:
                                usar_libras = True
                                destination = dest_name
                                break
                        if not destination:
                            destination = dest_word.title()
                        break
            
            # Detectar nombre del cliente con patrones más amplios
            cliente_nombre = None
            cliente_patterns = [
                r'cliente\s+([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+para|\s+precio|$)',
                r'para\s+(?:el\s+cliente\s+)?([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)',
                r'proforma\s+para\s+(?:el\s+cliente\s+)?([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)',
                r'cotizacion\s+para\s+([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)',
                r'señor\s+([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)',
                r'sr\s+([a-záéíóúñ\w\s]+?)(?:\s+con|\s+de|\s+precio|$)'
            ]
            
            for pattern in cliente_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    cliente_nombre = match.group(1).strip()
                    # Limpiar palabras comunes que no son nombres
                    stop_words = [
                        'el', 'la', 'con', 'de', 'para', 'precio', 'tipo', 'glaseo', 
                        'flete', 'producto', 'talla', 'envio', 'destino', 'kilo', 'kilos'
                    ]
                    cliente_words = [word for word in cliente_nombre.split() if word not in stop_words]
                    if cliente_words and len(' '.join(cliente_words)) > 2:
                        cliente_nombre = ' '.join(cliente_words)
                        break
            
            # Detectar cantidad
            quantity = None
            quantity_patterns = [
                r'(\d+(?:,\d{3})*)\s*(?:libras?|lb|lbs)',
                r'(\d+(?:,\d{3})*)\s*(?:kilos?|kg|kgs)',
                r'(\d+(?:,\d{3})*)\s*(?:toneladas?|tons?)',
                r'(\d+(?:\.\d+)?)\s*(?:mil|thousand)',
                r'(\d+(?:,\d{3})*)\s*(?:pounds?)'
            ]
            
            for pattern in quantity_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    quantity = match.group(1)
                    break
            
            # Determinar confianza basada en información extraída
            confidence = 0.6  # Base
            if size: confidence += 0.2
            if product: confidence += 0.1
            if destination: confidence += 0.1
            if glaseo_factor: confidence += 0.1
            
            return {
                "intent": "proforma",
                "product": product,
                "size": size,
                "quantity": quantity,
                "destination": destination,
                "glaseo_factor": glaseo_factor,
                "usar_libras": usar_libras,
                "cliente_nombre": cliente_nombre,
                "wants_proforma": True,
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
    
    def get_smart_fallback_response(self, user_message: str, intent_data: Dict) -> Optional[str]:
        """
        Genera respuestas inteligentes sin IA basadas en patrones
        """
        intent = intent_data.get('intent', 'unknown')
        message_lower = user_message.lower().strip()
        
        if intent == 'greeting':
            responses = [
                "¡Hola! 🦐 Soy ShrimpBot de BGR Export. ¿Qué producto de camarón necesitas? Puedo generar tu proforma al instante 📋",
                "¡Excelente! 🤖 Te ayudo con cotizaciones de camarón premium. ¿HLSO, P&D IQF o qué producto te interesa? 💰",
                "¡Hola! 👋 Listo para crear tu proforma de camarón. ¿Qué talla necesitas? Escribe 'precios' para ver todas 📊"
            ]
            # Seleccionar respuesta basada en el hash del mensaje para consistencia
            return responses[hash(message_lower) % len(responses)]
        
        elif intent == 'pricing':
            return "💰 ¡Perfecto! ¿Qué producto necesitas? HLSO es muy popular. Escribe 'precios' para ver tallas y crear tu proforma 📋"
        
        elif intent == 'product_info':
            return "🦐 Tenemos HLSO, P&D IQF, HOSO y más. ¿Cuál te interesa? Te genero la cotización con precios FOB actualizados 💰"
        
        elif intent == 'help':
            return "🤖 Te ayudo a crear proformas de camarón:\n• Precios FOB actualizados\n• Todas las tallas disponibles\n• PDF profesional\n\n¿Qué producto necesitas? 🦐"
        
        else:
            return "🦐 ¡Hola! Soy ShrimpBot de BGR Export. ¿Qué camarón necesitas? Te genero la proforma al instante 📋💰"