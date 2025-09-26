import openai
import os
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"
        
        if self.api_key:
            openai.api_key = self.api_key
            logger.info("✅ OpenAI API configurada correctamente")
        else:
            logger.warning("⚠️ OpenAI API Key no configurada")
    
    def is_available(self) -> bool:
        """Verifica si OpenAI está disponible"""
        return bool(self.api_key)
    
    def analyze_user_intent(self, message: str, context: Dict = None) -> Dict:
        """
        Analiza la intención del usuario usando GPT-4o mini
        """
        if not self.is_available():
            return {"intent": "unknown", "confidence": 0}
        
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

            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Mensaje: '{message}'"}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            
            # Intentar parsear como JSON
            import json
            parsed_result = json.loads(result)
            
            logger.info(f"🤖 Análisis OpenAI: {parsed_result}")
            return parsed_result
            
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

            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context_info}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"🤖 Respuesta generada por OpenAI: {result}")
            return result
            
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

            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Datos de precio: {price_data}"}
                ],
                max_tokens=100,
                temperature=0.5
            )
            
            result = response.choices[0].message.content.strip()
            return result
            
        except Exception as e:
            logger.error(f"❌ Error mejorando explicación de precio: {str(e)}")
            return None