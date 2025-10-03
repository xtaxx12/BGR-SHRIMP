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
- Flete: SOLO si menciona explícitamente "flete", "freight", "envío" → extraer valor numérico
- Precio base: "precio base 5.50", "base 6.20", "precio 4.80" → extraer valor si se menciona
- Cantidad: "15000 lb", "10 toneladas", "5000 kilos" → extraer número y unidad
- Cliente: "para [nombre]", "cliente [nombre]", "empresa [nombre]"
- Idioma: Detectar si el mensaje está en inglés o español

REGLAS IMPORTANTES:
- El usuario puede especificar TODOS los valores: glaseo, flete, precio base
- Si menciona "proforma" o "cotización" → intent: "proforma"
- IMPORTANTE: Solo extraer "destination" si menciona EXPLÍCITAMENTE flete/envío
- NO asumir destino automáticamente - solo si dice "flete a [lugar]" o "envío a [lugar]"
- Extraer valores numéricos EXACTOS que mencione el usuario
- Si no especifica un valor → null (el sistema NO usará defaults fijos)

FACTORES DE GLASEO ESTÁNDAR:
- 10% glaseo → glaseo_factor: 0.90
- 20% glaseo → glaseo_factor: 0.80  
- 30% glaseo → glaseo_factor: 0.70

EJEMPLOS DE EXTRACCIÓN:
"Proforma 20/30 HOSO glaseo 10% flete Houston" → glaseo_factor: 0.90, destination: "Houston", usar_libras: true
"Cotización con glaseo 20% y flete 0.25" → glaseo_factor: 0.80, flete_custom: 0.25
"Precio base 5.50 con glaseo 30%" → precio_base_custom: 5.50, glaseo_factor: 0.70, destination: null
"HLSO 16/20 glaseo 20%" → glaseo_factor: 0.80, destination: null, flete_custom: null
"16/20 sin cabeza con 20 de glaseo" → glaseo_factor: 0.80, destination: null, flete_custom: null

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
    "language": "es|en",
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
                # Limpiar emojis problemáticos que pueden causar errores de codificación
                cleaned_result = self._clean_problematic_emojis(result)
                logger.info(f"🤖 Respuesta generada por OpenAI: {cleaned_result}")
                return cleaned_result
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
        
        # Patrones de saludo (con límites de palabra para evitar falsos positivos)
        greeting_patterns = [r'\bhola\b', r'\bhello\b', r'\bhi\b', r'\bbuenos\b', r'\bbuenas\b', 
                           r'\bcomo estas\b', r'\bque tal\b', r'\bq haces\b']
        if any(re.search(pattern, message_lower) for pattern in greeting_patterns):
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
                    'sin cabezas', 'tipo sin cabeza', 'cola'
                ],
                'HOSO': [
                    'con cabeza', 'hoso', 'head on', 'entero', 'completo',
                    'con cabezas', 'tipo con cabeza'
                ],
                'P&D IQF': [
                    'p&d iqf', 'pd iqf', 'p&d', 'pelado', 'peeled', 'deveined', 
                    'limpio', 'procesado', 'pd', 'p d', 'pelado y desvenado'
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
                    'cooked', 'cocinado', 'cocido', 'preparado'
                ],
                'PRE-COCIDO': [
                    'pre-cocido', 'pre cocido', 'precocido', 'pre-cooked', 'pre cooked'
                ],
                'COCIDO SIN TRATAR': [
                    'cocido sin tratar', 'sin tratar', 'untreated', 'natural cocido'
                ]
            }
            
            # Buscar coincidencias de productos (orden específico para evitar conflictos)
            # Primero buscar patrones más específicos
            specific_order = ['COCIDO SIN TRATAR', 'PRE-COCIDO', 'COOKED', 'P&D IQF', 'P&D BLOQUE', 'PuD-EUROPA', 'PuD-EEUU', 'EZ PEEL', 'HLSO', 'HOSO']
            
            for prod_name in specific_order:
                if prod_name in product_patterns:
                    patterns = product_patterns[prod_name]
                    if any(pattern in message_lower for pattern in patterns):
                        product = prod_name
                        break
            
            # Si no se encontró en el orden específico, buscar en el resto
            if not product:
                for prod_name, patterns in product_patterns.items():
                    if prod_name not in specific_order:
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
            
            # Lógica inteligente: Si no se detectó producto pero hay talla específica de HOSO, asumir HOSO
            if not product and size:
                # Tallas que solo existen en HOSO según la tabla de precios
                hoso_exclusive_sizes = ['20/30', '30/40', '40/50', '50/60', '60/70', '70/80']
                if size in hoso_exclusive_sizes:
                    product = 'HOSO'
            
            # NO asumir producto por defecto para otras tallas - el usuario debe especificarlo
            
            # Detectar glaseo con patrones más amplios (español e inglés)
            glaseo_patterns = [
                # Patrones en español
                r'(\d+)\s*(?:de\s*)?glaseo',
                r'glaseo\s*(?:de\s*)?(\d+)',
                r'(\d+)\s*%\s*glaseo',
                r'glaseo\s*(\d+)\s*%',
                r'con\s*(\d+)\s*glaseo',
                r'(\d+)\s*porciento\s*glaseo',
                # Patrones adicionales para "al X%"
                r'al\s*(\d+)\s*%',  # "al 20%"
                r'(\d+)\s*%\s*de\s*glaseo',
                r'(\d+)\s*%\s*glaseo',
                # Patrones en inglés
                r'(\d+)g?\s*(?:of\s*)?glaze',
                r'glaze\s*(?:of\s*)?(\d+)g?',
                r'(\d+)\s*%\s*glaze',
                r'glaze\s*(\d+)\s*%',
                r'with\s*(\d+)g?\s*glaze',
                r'(\d+)\s*percent\s*glaze',
                r'at\s*(\d+)\s*%'  # "at 20%"
            ]
            
            glaseo_percentage_original = None
            for pattern in glaseo_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    glaseo_percentage_original = int(match.group(1))
                    # Convertir porcentaje a factor según reglas del negocio
                    if glaseo_percentage_original == 10:
                        glaseo_factor = 0.90
                    elif glaseo_percentage_original == 20:
                        glaseo_factor = 0.80
                    elif glaseo_percentage_original == 30:
                        glaseo_factor = 0.70
                    else:
                        glaseo_factor = glaseo_percentage_original / 100  # Para otros valores
                    break
            
            # Solo detectar destinos si se menciona flete explícitamente
            flete_keywords = ['flete', 'freight', 'envio', 'envío', 'shipping', 'transporte']
            menciona_flete = any(keyword in message_lower for keyword in flete_keywords)
            
            if menciona_flete:
                destination_patterns = {
                    'Houston': ['houston', 'houton', 'huston'],
                    'Miami': ['miami', 'maiami', 'florida'],
                    'New York': ['new york', 'nueva york', 'ny', 'newyork'],
                    'Los Angeles': ['los angeles', 'la', 'california'],
                    'Chicago': ['chicago', 'chicaco'],
                    'Dallas': ['dallas', 'dalas'],
                    'China': ['china', 'beijing', 'shanghai'],
                    'Europa': ['europa', 'europe', 'spain', 'italy', 'france'],
                    'Japón': ['japon', 'japan', 'tokyo']
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
            
            # También detectar patrones de envío (solo si ya menciona flete)
            if menciona_flete and not destination:
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
                "glaseo_percentage": glaseo_percentage_original,  # Porcentaje original solicitado
                "usar_libras": usar_libras,
                "cliente_nombre": cliente_nombre,
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
    
    def get_smart_fallback_response(self, user_message: str, intent_data: Dict) -> Optional[str]:
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