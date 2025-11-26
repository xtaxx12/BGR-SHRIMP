"""
Módulo de anonimización de datos para proteger información sensible
antes de usar mensajes para entrenamiento.

Cumple con GDPR y mejores prácticas de privacidad.
"""
import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class Anonymizer:
    """
    Anonimiza información sensible en mensajes de usuarios.
    
    Reemplaza:
    - Números de teléfono
    - Emails
    - Direcciones
    - Números de identificación
    - Nombres propios (opcional)
    - Números de cuenta/tarjeta
    """
    
    # Patrones de detección
    PATTERNS = {
        'phone': [
            r'\+?\d[\d\-\s\(\)]{6,}\d',  # +1 (555) 123-4567, +593 999 999 999
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 555-123-4567
            r'\b\d{10,}\b',  # 5551234567
        ],
        'email': [
            r'[\w\.-]+@[\w\.-]+\.\w+',  # user@example.com
        ],
        'address': [
            r'\b(av|avenida|calle|cra|cl|transv|carrera|diagonal)\.?\s+[^\n,]{3,}',
            r'\b(street|avenue|road|blvd|boulevard)\s+[^\n,]{3,}',
        ],
        'id_number': [
            r'\b\d{6,12}\b',  # Números largos que podrían ser IDs
        ],
        'account': [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Números de tarjeta
            r'\baccount\s*#?\s*\d+',
            r'\bcuenta\s*#?\s*\d+',
        ],
        'name': [
            # Patrones para detectar nombres propios (después de "cliente", "señor", etc.)
            r'(?:cliente|señor|sr|sra|señora|mr|mrs|ms)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
            r'(?:para|de)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
        ]
    }
    
    # Reemplazos
    REPLACEMENTS = {
        'phone': '[PHONE]',
        'email': '[EMAIL]',
        'address': '[ADDRESS]',
        'id_number': '[ID]',
        'account': '[ACCOUNT]',
        'name': '[NAME]',
    }
    
    # Lista de términos que NO deben ser anonimizados (productos, tallas, etc.)
    WHITELIST = [
        'HLSO', 'HOSO', 'P&D', 'IQF', 'BLOQUE', 'COOKED', 'PRE-COCIDO',
        'BRINE', 'NET', 'CFR', 'CIF', 'FOB', 'DDP',
        # Tallas
        r'\d+/\d+', r'\d+-\d+', 'U15',
        # Ciudades comunes (no son PII)
        'Houston', 'Miami', 'Lisboa', 'Madrid', 'Barcelona',
        # Términos comerciales
        'glaseo', 'flete', 'precio', 'cotizacion', 'proforma',
    ]
    
    def __init__(self, aggressive: bool = False):
        """
        Inicializa el anonimizador.
        
        Args:
            aggressive: Si True, anonimiza más agresivamente (incluye nombres)
        """
        self.aggressive = aggressive
        self._stats = {
            'total_processed': 0,
            'phones_found': 0,
            'emails_found': 0,
            'addresss_found': 0,  # Nota: 'address' + 's' = 'addresss'
            'id_numbers_found': 0,
            'accounts_found': 0,
            'names_found': 0,
        }
    
    def anonymize(self, text: str) -> str:
        """
        Anonimiza un texto completo.
        
        Args:
            text: Texto a anonimizar
            
        Returns:
            Texto anonimizado
        """
        if not text or not isinstance(text, str):
            return text
        
        self._stats['total_processed'] += 1
        result = text
        
        # Aplicar cada patrón
        for category, patterns in self.PATTERNS.items():
            # Saltar nombres si no es modo agresivo
            if category == 'name' and not self.aggressive:
                continue
            
            for pattern in patterns:
                matches = re.findall(pattern, result, re.IGNORECASE)
                if matches:
                    # Verificar que no esté en whitelist
                    for match in matches:
                        match_str = match if isinstance(match, str) else match[0]
                        if not self._is_whitelisted(match_str):
                            result = re.sub(
                                re.escape(match_str),
                                self.REPLACEMENTS[category],
                                result,
                                flags=re.IGNORECASE
                            )
                            self._stats[f'{category}s_found'] += 1
        
        return result
    
    def _is_whitelisted(self, text: str) -> bool:
        """
        Verifica si un texto está en la whitelist.
        
        Args:
            text: Texto a verificar
            
        Returns:
            True si está en whitelist
        """
        text_upper = text.upper()
        for pattern in self.WHITELIST:
            if isinstance(pattern, str):
                if pattern in text_upper:
                    return True
            else:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        return False
    
    def anonymize_batch(self, texts: List[str]) -> List[str]:
        """
        Anonimiza múltiples textos.
        
        Args:
            texts: Lista de textos
            
        Returns:
            Lista de textos anonimizados
        """
        return [self.anonymize(text) for text in texts]
    
    def anonymize_conversation(self, conversation: List[Dict]) -> List[Dict]:
        """
        Anonimiza una conversación completa.
        
        Args:
            conversation: Lista de mensajes con formato {"role": "...", "content": "..."}
            
        Returns:
            Conversación anonimizada
        """
        result = []
        for message in conversation:
            anonymized = message.copy()
            if 'content' in anonymized:
                anonymized['content'] = self.anonymize(anonymized['content'])
            result.append(anonymized)
        return result
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas de anonimización.
        
        Returns:
            Diccionario con estadísticas
        """
        return self._stats.copy()
    
    def reset_stats(self):
        """Reinicia las estadísticas."""
        for key in self._stats:
            self._stats[key] = 0


# Instancia global para uso fácil
_anonymizer = Anonymizer()


def anonymize(text: str, aggressive: bool = False) -> str:
    """
    Función helper para anonimizar texto rápidamente.
    
    Args:
        text: Texto a anonimizar
        aggressive: Si True, anonimiza nombres también
        
    Returns:
        Texto anonimizado
    """
    if aggressive:
        anon = Anonymizer(aggressive=True)
        return anon.anonymize(text)
    return _anonymizer.anonymize(text)


def anonymize_conversation(conversation: List[Dict], aggressive: bool = False) -> List[Dict]:
    """
    Función helper para anonimizar conversaciones.
    
    Args:
        conversation: Lista de mensajes
        aggressive: Si True, anonimiza nombres también
        
    Returns:
        Conversación anonimizada
    """
    if aggressive:
        anon = Anonymizer(aggressive=True)
        return anon.anonymize_conversation(conversation)
    return _anonymizer.anonymize_conversation(conversation)


def get_anonymization_stats() -> Dict:
    """
    Obtiene estadísticas globales de anonimización.
    
    Returns:
        Diccionario con estadísticas
    """
    return _anonymizer.get_stats()
