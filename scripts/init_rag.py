"""
Script para inicializar el sistema RAG con datos básicos.

Uso:
    python scripts/init_rag.py
    python scripts/init_rag.py --include-prices
    python scripts/init_rag.py --clear-first
"""
import argparse
import logging
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

from app.services.rag_service import get_rag_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# FAQs predeterminadas sobre BGR Export y productos de camarón
DEFAULT_FAQS = [
    {
        "question": "¿Qué productos de camarón ofrece BGR Export?",
        "answer": """BGR Export ofrece una amplia variedad de productos de camarón premium:
- HOSO (Head On Shell On): Camarón entero con cabeza y cáscara
- HLSO (Head Less Shell On): Sin cabeza, con cáscara - ideal para colas
- P&D IQF (Peeled & Deveined): Pelado y desvenado congelado individualmente
- P&D BLOQUE: Pelado y desvenado congelado en bloque
- EZ PEEL: Fácil pelado, con corte en el lomo
- PuD-EUROPA: Calidad premium específica para mercado europeo
- PuD-EEUU: Especificaciones para mercado estadounidense
- COOKED: Cocido listo para consumo
- PRE-COCIDO: Pre-cocido para procesamiento posterior""",
        "category": "productos"
    },
    {
        "question": "¿Qué tallas de camarón están disponibles?",
        "answer": """Las tallas disponibles son (camarones por libra):
- U15: Under 15 (menos de 15 camarones por libra) - Jumbo
- 16/20: 16 a 20 camarones por libra - Extra Large
- 21/25: 21 a 25 camarones por libra - Large
- 26/30: 26 a 30 camarones por libra - Medium Large
- 31/35: 31 a 35 camarones por libra - Medium
- 36/40: 36 a 40 camarones por libra
- 40/50, 41/50: 40 a 50 camarones por libra
- 50/60, 51/60: 50 a 60 camarones por libra
- 60/70, 61/70: 60 a 70 camarones por libra
- 70/80: 70 a 80 camarones por libra
- 71/90: 71 a 90 camarones por libra - Pequeño""",
        "category": "productos"
    },
    {
        "question": "¿Qué es el glaseo y cómo afecta el precio?",
        "answer": """El glaseo es una capa de agua congelada que se aplica al camarón para protegerlo durante el almacenamiento y transporte.

Porcentajes comunes:
- 10% glaseo: Mínimo, producto más "seco"
- 20% glaseo: Estándar, balance entre protección y peso neto
- 30% glaseo: Mayor protección, común para exportación

El glaseo afecta el precio porque se paga por peso bruto pero el producto neto es menor. Por ejemplo, con 20% de glaseo, 1 kg bruto contiene 800g de camarón neto.

La fórmula de conversión es: Precio Neto = Precio FOB × (1 - Glaseo%)""",
        "category": "precios"
    },
    {
        "question": "¿Cuál es la diferencia entre precio FOB y CFR?",
        "answer": """FOB (Free On Board) y CFR (Cost and Freight) son términos de comercio internacional (Incoterms):

FOB (Puerto de origen):
- El vendedor entrega la mercancía en el puerto de embarque
- El comprador paga el flete marítimo
- Precio base sin incluir transporte internacional

CFR (Puerto de destino):
- El vendedor paga el flete hasta el puerto de destino
- Precio = FOB + Flete marítimo
- Más conveniente para el comprador

Ejemplo: Si FOB = $5.00/kg y Flete = $0.35/kg, entonces CFR = $5.35/kg""",
        "category": "precios"
    },
    {
        "question": "¿Cómo puedo solicitar una cotización?",
        "answer": """Para solicitar una cotización necesitas proporcionar:

1. Producto: HLSO, HOSO, P&D, etc.
2. Talla: 16/20, 21/25, etc.
3. Glaseo: 10%, 20%, 30%
4. Cantidad: En kilogramos o libras
5. Destino: Puerto o ciudad de destino (para calcular CFR)

Puedes simplemente escribir tu solicitud de forma natural, por ejemplo:
- "Necesito precio para HLSO 16/20 con 20% glaseo"
- "Cotización de 1000 kg de P&D 21/25 CFR Miami"
- "Precios para varias tallas de camarón cocido"

El sistema analizará tu mensaje y te guiará si falta información.""",
        "category": "proceso"
    },
    {
        "question": "¿Qué significa 100% NET en los precios?",
        "answer": """100% NET significa que el precio es por peso neto de camarón, sin incluir el glaseo.

Cuando ves un precio "100% NET":
- Es el precio real del producto de camarón
- No incluye el peso del glaseo (capa de hielo protectora)
- Es útil para comparar precios entre diferentes proveedores

Conversión: Si el precio es $5.00/kg al 100% NET y quieres aplicar 20% de glaseo:
Precio con glaseo = $5.00 × 0.80 = $4.00/kg (precio por kg bruto)

Este ajuste es importante porque el comprador paga por peso bruto pero recibe menos producto neto.""",
        "category": "precios"
    },
    {
        "question": "¿Cuáles son los métodos de pago aceptados?",
        "answer": """BGR Export acepta los siguientes métodos de pago:

1. Transferencia bancaria internacional (Wire Transfer)
   - Método más común para exportaciones
   - Se requiere información bancaria completa

2. Carta de crédito (Letter of Credit - L/C)
   - Para pedidos grandes
   - Mayor seguridad para ambas partes

3. Pago anticipado (Advance Payment)
   - Puede aplicarse a nuevos clientes
   - Generalmente parcial (30-50% adelanto)

Los términos específicos se negocian según el volumen y la relación comercial.""",
        "category": "proceso"
    },
    {
        "question": "¿Cuál es el tiempo de entrega típico?",
        "answer": """Los tiempos de entrega varían según el destino:

Producción: 1-2 semanas después de confirmar pedido

Tránsito marítimo aproximado:
- Estados Unidos (costa este): 10-14 días
- Estados Unidos (costa oeste): 18-21 días
- Europa (España, Portugal): 18-25 días
- Asia: 25-35 días

El tiempo total desde pedido hasta entrega es aproximadamente 3-5 semanas dependiendo del destino.

Para pedidos urgentes, se puede considerar transporte aéreo con costo adicional.""",
        "category": "logistica"
    },
    {
        "question": "¿Qué certificaciones tiene BGR Export?",
        "answer": """BGR Export cuenta con las siguientes certificaciones y estándares:

- HACCP: Sistema de análisis de peligros y puntos críticos de control
- BRC: British Retail Consortium - Estándar global de seguridad alimentaria
- BAP: Best Aquaculture Practices - Prácticas responsables de acuacultura
- FDA Registered: Registrado con la FDA de Estados Unidos

Todas las instalaciones cumplen con estándares internacionales de calidad y trazabilidad del producto desde el cultivo hasta el embarque.""",
        "category": "empresa"
    },
    {
        "question": "¿Cuál es el pedido mínimo?",
        "answer": """El pedido mínimo depende del tipo de envío:

Contenedor completo (FCL):
- 20' container: ~18-20 toneladas métricas
- 40' container: ~25-28 toneladas métricas
- Mejor precio por kilogramo

Carga consolidada (LCL):
- Mínimo: 1-2 toneladas métricas
- Precio ligeramente mayor por kg
- Ideal para pruebas de mercado

Para muestras comerciales, contáctenos directamente para coordinar envíos especiales.""",
        "category": "logistica"
    }
]


# Información general sobre la empresa
COMPANY_INFO = [
    {
        "content": """BGR Export es una empresa ecuatoriana líder en exportación de camarón premium (Litopenaeus vannamei).
Ubicada en Puerto Jeli, Santa Rosa, Ecuador, BGR Export se especializa en productos de camarón de alta calidad
para mercados internacionales incluyendo Estados Unidos, Europa y Asia.
La empresa mantiene los más altos estándares de calidad con certificaciones HACCP, BRC y BAP.
Contacto comercial: amerino@bgrexport.com, WhatsApp: +593 98-805-7425""",
        "type": "general",
        "metadata": {"topic": "empresa", "source": "info_general"}
    },
    {
        "content": """Horarios de atención de BGR Export:
- Lunes a Viernes: 8:00 AM - 6:00 PM (GMT-5, hora de Ecuador)
- Sábados: 9:00 AM - 1:00 PM
- Domingos y feriados: Cerrado (emergencias vía WhatsApp)

Para consultas urgentes fuera de horario, el equipo comercial puede responder vía WhatsApp.""",
        "type": "general",
        "metadata": {"topic": "horarios", "source": "info_general"}
    },
    {
        "content": """El camarón ecuatoriano (Litopenaeus vannamei) es reconocido mundialmente por su calidad superior.
Ecuador es uno de los principales exportadores de camarón del mundo, con aguas cálidas ideales para el cultivo.
Las características del camarón ecuatoriano incluyen:
- Sabor dulce y textura firme
- Alto contenido proteico
- Cultivo sostenible y responsable
- Trazabilidad completa desde la granja hasta el embarque""",
        "type": "product",
        "metadata": {"topic": "calidad", "source": "info_producto"}
    }
]


def init_faqs(rag_service):
    """Inicializa las FAQs en el sistema RAG."""
    logger.info("📝 Indexando FAQs...")
    count = rag_service.index_faqs(DEFAULT_FAQS)
    logger.info(f"✅ {count} FAQs indexadas")
    return count


def init_company_info(rag_service):
    """Inicializa información de la empresa."""
    logger.info("🏢 Indexando información de la empresa...")
    indexed = rag_service.index_documents_batch(COMPANY_INFO)
    logger.info(f"✅ {len(indexed)} documentos de empresa indexados")
    return len(indexed)


def init_prices(rag_service):
    """Inicializa precios desde Google Sheets."""
    logger.info("💰 Indexando precios desde Google Sheets...")
    try:
        from app.services.google_sheets import get_google_sheets_service
        gs_service = get_google_sheets_service()
        count = rag_service.index_prices_from_sheets(gs_service)
        logger.info(f"✅ {count} documentos de precios indexados")
        return count
    except Exception as e:
        logger.warning(f"⚠️ No se pudieron indexar precios: {str(e)}")
        return 0


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Inicializar sistema RAG con datos básicos'
    )
    parser.add_argument(
        '--include-prices',
        action='store_true',
        help='Incluir precios desde Google Sheets'
    )
    parser.add_argument(
        '--clear-first',
        action='store_true',
        help='Limpiar índice existente antes de inicializar'
    )
    parser.add_argument(
        '--faqs-only',
        action='store_true',
        help='Solo indexar FAQs'
    )

    args = parser.parse_args()

    logger.info("🚀 Iniciando configuración del sistema RAG...")

    # Obtener servicio RAG
    rag = get_rag_service()

    # Verificar disponibilidad
    if not rag.is_available():
        logger.error("❌ API key de OpenAI no configurada. El sistema RAG requiere OPENAI_API_KEY.")
        logger.info("💡 Configura la variable de entorno OPENAI_API_KEY y vuelve a ejecutar.")
        sys.exit(1)

    # Limpiar si se solicita
    if args.clear_first:
        logger.info("🗑️ Limpiando índice existente...")
        rag.clear_index()

    # Mostrar estado inicial
    stats = rag.get_stats()
    logger.info(f"📊 Estado inicial: {stats['total_documents']} documentos indexados")

    # Inicializar datos
    total_indexed = 0

    if args.faqs_only:
        total_indexed += init_faqs(rag)
    else:
        total_indexed += init_faqs(rag)
        total_indexed += init_company_info(rag)

        if args.include_prices:
            total_indexed += init_prices(rag)

    # Mostrar resumen
    final_stats = rag.get_stats()

    logger.info("\n" + "=" * 60)
    logger.info("✅ INICIALIZACIÓN COMPLETADA")
    logger.info("=" * 60)
    logger.info(f"📊 Documentos totales: {final_stats['total_documents']}")
    logger.info(f"📁 Por tipo: {final_stats['documents_by_type']}")
    logger.info(f"💾 Tamaño del índice: {final_stats['index_size_mb']:.2f} MB")
    logger.info("=" * 60)

    # Probar una consulta
    logger.info("\n🔍 Probando consulta de ejemplo...")
    results = rag.retrieve("¿Qué productos tienen disponibles?", top_k=2)

    if results:
        logger.info(f"✅ Consulta exitosa - {len(results)} resultados encontrados")
        for i, r in enumerate(results, 1):
            logger.info(f"   {i}. [{r['metadata'].get('type', 'N/A')}] Similitud: {r['similarity']:.3f}")
    else:
        logger.warning("⚠️ No se encontraron resultados para la consulta de prueba")


if __name__ == "__main__":
    main()
