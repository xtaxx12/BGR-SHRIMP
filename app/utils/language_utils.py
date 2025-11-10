"""
Utilidades para detección de idioma y conversión de glaseo.
"""


def glaseo_percentage_to_factor(percentage: int) -> float:
    """
    Convierte porcentaje de glaseo a factor
    Fórmula: Factor = 1 - (percentage / 100)

    Ejemplos:
    - 10% glaseo → factor = 1 - 0.10 = 0.90
    - 15% glaseo → factor = 1 - 0.15 = 0.85
    - 20% glaseo → factor = 1 - 0.20 = 0.80
    - 25% glaseo → factor = 1 - 0.25 = 0.75
    """
    return 1 - (percentage / 100)


def detect_language(message: str, ai_analysis: dict = None) -> str:
    """Detecta idioma preferido del usuario.
    - Primero usa el resultado del análisis de IA si viene con 'language'.
    - Si no, usa una heurística simple basada en palabras comunes en cada idioma.
    Retorna 'es' o 'en'.
    """
    if ai_analysis:
        lang = ai_analysis.get('language')
        if lang in ('es', 'en'):
            return lang

    text = (message or "").lower()
    # Palabras comunes para cada idioma
    english_words = ['please', 'hello', 'hi', 'thanks', 'thank', 'price', 'quote', 'proforma', 'ddp', 'cif', 'fob']
    spanish_words = ['por favor', 'hola', 'gracias', 'precio', 'precios', 'proforma', 'cotización', 'cotizacion', 'ddp', 'flete']

    en_score = sum(text.count(w) for w in english_words)
    es_score = sum(text.count(w) for w in spanish_words)

    return 'en' if en_score > es_score else 'es'
