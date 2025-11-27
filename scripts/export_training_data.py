"""
Script para exportar mensajes aprobados a formato JSONL para fine-tuning de OpenAI.

Este script:
1. Lee mensajes aprobados de la base de datos
2. Crea pares user-assistant
3. Exporta a formato JSONL compatible con OpenAI
4. Opcionalmente sube el archivo a OpenAI

Uso:
    python scripts/export_training_data.py
    python scripts/export_training_data.py --upload
    python scripts/export_training_data.py --min-pairs 10
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.training_capture_db import get_capture_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def export_training_data(output_path: str = "data/finetune/train.jsonl", min_pairs: int = 5):
    """
    Exporta mensajes aprobados a formato JSONL.
    
    Args:
        output_path: Ruta del archivo de salida
        min_pairs: Mínimo de pares requeridos para exportar
        
    Returns:
        Número de pares exportados
    """
    logger.info("📦 Iniciando exportación de datos de entrenamiento...")
    
    # Obtener servicio de captura
    capture = get_capture_service()
    
    # Exportar
    num_pairs = capture.export_for_finetune(output_path)
    
    if num_pairs == 0:
        logger.warning("⚠️ No hay mensajes aprobados para exportar")
        logger.info("💡 Asegúrate de aprobar mensajes en el dashboard de revisión")
        return 0
    
    if num_pairs < min_pairs:
        logger.warning(f"⚠️ Solo se exportaron {num_pairs} pares, se recomienda al menos {min_pairs}")
        logger.info("💡 Continúa aprobando más mensajes para mejorar el entrenamiento")
    
    logger.info(f"✅ Exportados {num_pairs} pares de entrenamiento a {output_path}")
    
    # Mostrar preview
    logger.info("\n📄 Preview de los primeros 3 ejemplos:")
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                example = json.loads(line)
                logger.info(f"\n--- Ejemplo {i+1} ---")
                for msg in example['messages']:
                    role = msg['role'].upper()
                    content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                    logger.info(f"{role}: {content}")
    except Exception as e:
        logger.error(f"❌ Error mostrando preview: {str(e)}")
    
    return num_pairs


def upload_to_openai(file_path: str):
    """
    Sube el archivo de entrenamiento a OpenAI.
    
    Args:
        file_path: Ruta del archivo JSONL
    """
    import os
    import openai
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY no configurada")
        return False
    
    openai.api_key = api_key
    
    logger.info(f"📤 Subiendo archivo a OpenAI: {file_path}")
    
    try:
        with open(file_path, 'rb') as f:
            response = openai.files.create(
                file=f,
                purpose='fine-tune'
            )
        
        file_id = response.id
        logger.info(f"✅ Archivo subido exitosamente")
        logger.info(f"📋 File ID: {file_id}")
        logger.info(f"📊 Status: {response.status}")
        
        logger.info("\n🚀 Para crear un fine-tuning job, ejecuta:")
        logger.info(f"   openai api fine_tuning.jobs.create -t {file_id} -m gpt-3.5-turbo")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error subiendo archivo: {str(e)}")
        return False


def validate_jsonl(file_path: str):
    """
    Valida el formato del archivo JSONL.
    
    Args:
        file_path: Ruta del archivo a validar
        
    Returns:
        True si es válido
    """
    logger.info(f"🔍 Validando formato JSONL: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) == 0:
            logger.error("❌ Archivo vacío")
            return False
        
        errors = []
        for i, line in enumerate(lines, 1):
            try:
                data = json.loads(line)
                
                # Validar estructura
                if 'messages' not in data:
                    errors.append(f"Línea {i}: Falta campo 'messages'")
                    continue
                
                messages = data['messages']
                if not isinstance(messages, list) or len(messages) < 2:
                    errors.append(f"Línea {i}: 'messages' debe ser una lista con al menos 2 mensajes")
                    continue
                
                # Validar roles
                for msg in messages:
                    if 'role' not in msg or 'content' not in msg:
                        errors.append(f"Línea {i}: Mensaje sin 'role' o 'content'")
                        break
                    
                    if msg['role'] not in ['system', 'user', 'assistant']:
                        errors.append(f"Línea {i}: Rol inválido '{msg['role']}'")
                        break
                
            except json.JSONDecodeError as e:
                errors.append(f"Línea {i}: JSON inválido - {str(e)}")
        
        if errors:
            logger.error(f"❌ Se encontraron {len(errors)} errores:")
            for error in errors[:10]:  # Mostrar primeros 10
                logger.error(f"   {error}")
            return False
        
        logger.info(f"✅ Archivo válido: {len(lines)} ejemplos")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error validando archivo: {str(e)}")
        return False


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Exportar datos de entrenamiento desde mensajes aprobados'
    )
    parser.add_argument(
        '--output',
        default='data/finetune/train.jsonl',
        help='Ruta del archivo de salida'
    )
    parser.add_argument(
        '--min-pairs',
        type=int,
        default=5,
        help='Mínimo de pares requeridos'
    )
    parser.add_argument(
        '--upload',
        action='store_true',
        help='Subir archivo a OpenAI después de exportar'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Solo validar archivo existente sin exportar'
    )
    
    args = parser.parse_args()
    
    # Solo validar
    if args.validate_only:
        if not Path(args.output).exists():
            logger.error(f"❌ Archivo no existe: {args.output}")
            sys.exit(1)
        
        is_valid = validate_jsonl(args.output)
        sys.exit(0 if is_valid else 1)
    
    # Exportar
    num_pairs = export_training_data(args.output, args.min_pairs)
    
    if num_pairs == 0:
        logger.error("❌ No se exportaron datos")
        sys.exit(1)
    
    # Validar
    if not validate_jsonl(args.output):
        logger.error("❌ El archivo exportado no es válido")
        sys.exit(1)
    
    # Subir a OpenAI si se solicita
    if args.upload:
        logger.info("\n" + "="*60)
        success = upload_to_openai(args.output)
        if not success:
            sys.exit(1)
    else:
        logger.info("\n" + "="*60)
        logger.info("💡 Para subir a OpenAI, ejecuta:")
        logger.info(f"   python scripts/export_training_data.py --upload")
    
    logger.info("="*60)
    logger.info("✅ Proceso completado exitosamente")


if __name__ == "__main__":
    main()
