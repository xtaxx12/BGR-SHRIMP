"""
Script para exportar datos de entrenamiento a formato JSONL para fine-tuning de OpenAI.

Uso:
    python scripts/export_for_finetune.py
    python scripts/export_for_finetune.py --min-confidence 0.9
    python scripts/export_for_finetune.py --aggressive-anonymization
"""
import argparse
import json
import logging
import random
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.session import session_manager
from app.services.training_pipeline import get_training_pipeline
from app.utils.anonymizer import anonymize, anonymize_conversation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def export_from_sessions(
    min_confidence: float = 0.85,
    train_split: float = 0.9,
    aggressive_anon: bool = False
) -> dict:
    """
    Exporta datos desde las sesiones activas.
    
    Args:
        min_confidence: Confianza mínima para incluir ejemplos
        train_split: Proporción para entrenamiento
        aggressive_anon: Si True, anonimiza nombres también
        
    Returns:
        Estadísticas de exportación
    """
    examples = []
    stats = {
        'total_sessions': 0,
        'sessions_with_consent': 0,
        'total_messages': 0,
        'valid_pairs': 0,
        'filtered_out': 0,
    }
    
    # Iterar sobre todas las sesiones
    for user_id, session in session_manager.sessions.items():
        stats['total_sessions'] += 1
        
        # Verificar consentimiento
        if not session.get('consent_for_training'):
            continue
        
        stats['sessions_with_consent'] += 1
        
        # Obtener historial
        history = session.get('conversation_history', [])
        stats['total_messages'] += len(history)
        
        # Extraer pares user → assistant
        for i in range(len(history) - 1):
            if history[i]['role'] == 'user' and history[i+1]['role'] == 'assistant':
                user_msg = history[i]['content'].strip()
                assistant_msg = history[i+1]['content'].strip()
                
                # Filtrar mensajes muy cortos
                if len(user_msg) < 5 or len(assistant_msg) < 5:
                    stats['filtered_out'] += 1
                    continue
                
                # Anonimizar
                user_msg = anonymize(user_msg, aggressive=aggressive_anon)
                assistant_msg = anonymize(assistant_msg, aggressive=aggressive_anon)
                
                # Crear ejemplo en formato nuevo de OpenAI (messages)
                example = {
                    "messages": [
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": assistant_msg}
                    ]
                }
                
                examples.append(example)
                stats['valid_pairs'] += 1
    
    if not examples:
        logger.warning("⚠️ No se encontraron ejemplos válidos para exportar")
        return stats
    
    # Mezclar y dividir
    random.shuffle(examples)
    split_idx = int(len(examples) * train_split)
    train_examples = examples[:split_idx]
    valid_examples = examples[split_idx:]
    
    # Crear directorio
    output_dir = Path("data/finetune")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Exportar
    train_path = output_dir / "train.jsonl"
    valid_path = output_dir / "valid.jsonl"
    
    with open(train_path, 'w', encoding='utf-8') as f:
        for ex in train_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')
    
    with open(valid_path, 'w', encoding='utf-8') as f:
        for ex in valid_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')
    
    stats['train_examples'] = len(train_examples)
    stats['valid_examples'] = len(valid_examples)
    stats['train_file'] = str(train_path)
    stats['valid_file'] = str(valid_path)
    
    logger.info(f"✅ Exportación completada:")
    logger.info(f"   📊 Sesiones totales: {stats['total_sessions']}")
    logger.info(f"   ✅ Con consentimiento: {stats['sessions_with_consent']}")
    logger.info(f"   💬 Mensajes totales: {stats['total_messages']}")
    logger.info(f"   📝 Pares válidos: {stats['valid_pairs']}")
    logger.info(f"   🚫 Filtrados: {stats['filtered_out']}")
    logger.info(f"   📚 Train: {stats['train_examples']} ejemplos → {train_path}")
    logger.info(f"   🧪 Valid: {stats['valid_examples']} ejemplos → {valid_path}")
    
    return stats


def export_from_pipeline(
    min_confidence: float = 0.85,
    train_split: float = 0.9
) -> dict:
    """
    Exporta datos desde el pipeline ETL.
    
    Args:
        min_confidence: Confianza mínima
        train_split: Proporción para entrenamiento
        
    Returns:
        Estadísticas de exportación
    """
    pipeline = get_training_pipeline()
    train_count, valid_count = pipeline.export_for_finetune(
        min_confidence=min_confidence,
        train_split=train_split
    )
    
    return {
        'train_examples': train_count,
        'valid_examples': valid_count,
        'total': train_count + valid_count
    }


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Exportar datos de entrenamiento a formato JSONL'
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.85,
        help='Confianza mínima para incluir ejemplos (default: 0.85)'
    )
    parser.add_argument(
        '--train-split',
        type=float,
        default=0.9,
        help='Proporción para entrenamiento (default: 0.9)'
    )
    parser.add_argument(
        '--aggressive-anonymization',
        action='store_true',
        help='Anonimizar nombres también'
    )
    parser.add_argument(
        '--source',
        choices=['sessions', 'pipeline', 'both'],
        default='both',
        help='Fuente de datos (default: both)'
    )
    
    args = parser.parse_args()
    
    logger.info("🚀 Iniciando exportación de datos de entrenamiento...")
    logger.info(f"   Confianza mínima: {args.min_confidence}")
    logger.info(f"   Train split: {args.train_split}")
    logger.info(f"   Anonimización agresiva: {args.aggressive_anonymization}")
    logger.info(f"   Fuente: {args.source}")
    
    results = {}
    
    # Exportar desde sesiones
    if args.source in ['sessions', 'both']:
        logger.info("\n📥 Exportando desde sesiones...")
        results['sessions'] = export_from_sessions(
            min_confidence=args.min_confidence,
            train_split=args.train_split,
            aggressive_anon=args.aggressive_anonymization
        )
    
    # Exportar desde pipeline
    if args.source in ['pipeline', 'both']:
        logger.info("\n📥 Exportando desde pipeline ETL...")
        results['pipeline'] = export_from_pipeline(
            min_confidence=args.min_confidence,
            train_split=args.train_split
        )
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("✅ EXPORTACIÓN COMPLETADA")
    logger.info("="*80)
    
    total_train = 0
    total_valid = 0
    
    for source, stats in results.items():
        if 'train_examples' in stats:
            total_train += stats['train_examples']
            total_valid += stats['valid_examples']
            logger.info(f"\n{source.upper()}:")
            logger.info(f"   Train: {stats['train_examples']}")
            logger.info(f"   Valid: {stats['valid_examples']}")
    
    logger.info(f"\nTOTAL:")
    logger.info(f"   Train: {total_train}")
    logger.info(f"   Valid: {total_valid}")
    logger.info(f"   Total: {total_train + total_valid}")
    logger.info("\n📁 Archivos generados en: data/finetune/")
    logger.info("="*80)


if __name__ == "__main__":
    main()
