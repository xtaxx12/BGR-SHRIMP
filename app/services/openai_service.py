import requests
import os
import logging
import json
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"
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
Eres un asistente especializado en análisis de intenciones para un bot de WhatsApp de BGR Export (empresa de camarones).

Analiza el mensaje del usuario y determina:
1. La intención principal (pricing, product_info, greeting, help, etc.)
2. Si menciona productos específicos (HOSO, HLSO, P&D IQF, etc.)
3. Si menciona tallas (16/20, 21/25, etc.)
4. Si menciona cantidades o destinos
5. Nivel de confianza (0-1)

Responde SOLO en formato JSON válido:
{
    "intent": "pricing|product_info|greeting|help|contact|other",
    "product": "producto mencionado o null",
    "size": "talla mencionada o null", 
    "quantity": "cantidad mencionada o null",
    "destination": "destino mencionado o null",
    "confidence": 0.95,
    "suggested_response": "sugerencia de respuesta breve"
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
Eres ShrimpBot, el asistente virtual de BGR Export especializado en camarones premium.

PERSONALIDAD:
- Profesional pero amigable
- Experto en productos de camarón
- Usa emojis apropiados (🦐, 💰, 📊, etc.)
- Respuestas concisas y útiles
- Siempre orientado a ayudar con precios y productos

PRODUCTOS DISPONIBLES:
- HOSO (Head On Shell On)
- HLSO (Head Less Shell On) 
- P&D IQF (Peeled & Deveined Individual Quick Frozen)
- P&D BLOQUE (Peeled & Deveined Block)
- PuD-EUROPA (Peeled Deveined Europa Quality)
- EZ PEEL (Easy Peel)
- PuD-EEUU (Peeled Deveined USA)
- COOKED (Cocido)
- PRE-COCIDO (Pre-cooked)
- COCIDO SIN TRATAR (Untreated Cooked)

TALLAS: U15, 16/20, 20/30, 21/25, 26/30, 30/40, 31/35, 36/40, 40/50, 41/50, 50/60, 51/60, 60/70, 61/70, 70/80, 71/90

INSTRUCCIONES:
- Si el usuario pregunta por precios, guíalo al menú de precios
- Si menciona productos/tallas específicas, confirma y ofrece cotización
- Mantén respuestas bajo 200 caracteres para WhatsApp
- Usa el contexto para personalizar la respuesta
- Siempre incluye opciones de navegación (menu, precios, etc.)

Genera una respuesta apropiada y útil.
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
        
        # Patrones de precios
        price_patterns = ['precio', 'precios', 'cotizar', 'cotizacion', 'cuanto', 'cuesta', 'cost']
        if any(pattern in message_lower for pattern in price_patterns):
            return {
                "intent": "pricing",
                "product": None,
                "size": None,
                "quantity": None,
                "destination": None,
                "confidence": 0.9,
                "suggested_response": "Dirigir al menú de precios"
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
                "¡Hola! 🦐 Soy ShrimpBot de BGR Export. ¿Te ayudo con precios de camarón? Escribe 'precios' para empezar.",
                "¡Buen día! 🤖 Estoy aquí para ayudarte con cotizaciones de camarón premium. ¿Qué necesitas?",
                "¡Hola! 👋 Soy tu asistente para precios de camarón BGR Export. Escribe 'menu' para ver opciones."
            ]
            # Seleccionar respuesta basada en el hash del mensaje para consistencia
            return responses[hash(message_lower) % len(responses)]
        
        elif intent == 'pricing':
            return "💰 Perfecto! Te ayudo con precios de camarón. Escribe 'precios' para ver todas las tallas disponibles."
        
        elif intent == 'product_info':
            return "🦐 Tenemos camarones premium: HLSO, P&D IQF, HOSO y más. Escribe 'productos' para ver la lista completa."
        
        elif intent == 'help':
            return "🤖 Puedo ayudarte con:\n• Precios de camarón\n• Información de productos\n• Contacto comercial\n\nEscribe 'menu' para empezar."
        
        else:
            return "🦐 ¡Hola! Soy ShrimpBot de BGR Export. ¿Te ayudo con precios de camarón? Escribe 'menu' para ver opciones."