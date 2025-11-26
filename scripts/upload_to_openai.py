"""
Script para subir archivos de entrenamiento a OpenAI.

Uso:
    python scripts/upload_to_openai.py
    python scripts/upload_to_openai.py --validate-only
"""
import argparse
import json
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from openai import OpenAI
except ImportError:
    print("❌ Error: openai no está instalado")
    print("   Instala con: pip install openai")
    sys.exit(1)

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def validate_jsonl_file(file_path: Path) -> tuple[bool, list]:
    """
    Valida que el archivo JSONL tenga el formato correcto.
    
    Returns:
        Tupla (es_válido, errores)
    """
    errors = []
    
    if not file_path.exists():
        return False, [f"Archivo no existe: {file_path}"]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) == 0:
            return False, ["Archivo vacío"]
        
        for i, line in enumerate(lines, 1):
            try:
                data = json.loads(line)
                
                # Validar estructura (formato nuevo: messages)
                if 'messages' not in data:
                    errors.append(f"Línea {i}: Falta campo 'messages'")
                    continue
                
                messages = data.get('messages', [])
                
                # Validar que tenga al menos 2 mensajes
                if len(messages) < 2:
                    errors.append(f"Línea {i}: Debe tener al menos 2 mensajes (user y assistant)")
                
                # Validar estructura de cada mensaje
                for j, msg in enumerate(messages):
                    if 'role' not in msg:
                        errors.append(f"Línea {i}, mensaje {j+1}: Falta campo 'role'")
                    if 'content' not in msg:
                        errors.append(f"Línea {i}, mensaje {j+1}: Falta campo 'content'")
                    if msg.get('content', '').strip() == '':
                        errors.append(f"Línea {i}, mensaje {j+1}: 'content' está vacío")
                
            except json.JSONDecodeError as e:
                errors.append(f"Línea {i}: JSON inválido - {str(e)}")
        
        return len(errors) == 0, errors
        
    except Exception as e:
        return False, [f"Error leyendo archivo: {str(e)}"]


def count_examples(file_path: Path) -> int:
    """Cuenta el número de ejemplos en un archivo JSONL."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0


def upload_file_to_openai(file_path: Path, purpose: str = "fine-tune") -> dict:
    """
    Sube un archivo a OpenAI.
    
    Args:
        file_path: Ruta al archivo JSONL
        purpose: Propósito del archivo (default: "fine-tune")
        
    Returns:
        Información del archivo subido
    """
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY no está configurada en .env")
    
    client = OpenAI(api_key=api_key)
    
    print(f"\n📤 Subiendo {file_path.name} a OpenAI...")
    
    with open(file_path, 'rb') as f:
        response = client.files.create(
            file=f,
            purpose=purpose
        )
    
    return {
        'id': response.id,
        'filename': response.filename,
        'bytes': response.bytes,
        'created_at': response.created_at,
        'purpose': response.purpose,
        'status': response.status
    }


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Subir archivos de entrenamiento a OpenAI'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Solo validar archivos sin subirlos'
    )
    parser.add_argument(
        '--train-file',
        type=str,
        default='data/finetune/train.jsonl',
        help='Ruta al archivo de entrenamiento'
    )
    parser.add_argument(
        '--valid-file',
        type=str,
        default='data/finetune/valid.jsonl',
        help='Ruta al archivo de validación'
    )
    
    args = parser.parse_args()
    
    train_path = Path(args.train_file)
    valid_path = Path(args.valid_file)
    
    print("=" * 80)
    print("📤 SUBIDA DE ARCHIVOS A OPENAI")
    print("=" * 80)
    
    # 1. Validar archivos
    print("\n1️⃣ Validando archivos...")
    
    train_valid, train_errors = validate_jsonl_file(train_path)
    valid_valid, valid_errors = validate_jsonl_file(valid_path)
    
    train_count = count_examples(train_path)
    valid_count = count_examples(valid_path)
    
    print(f"\n📚 Train ({train_path}):")
    print(f"   - Ejemplos: {train_count}")
    print(f"   - Válido: {'✅' if train_valid else '❌'}")
    if train_errors:
        for error in train_errors[:5]:  # Mostrar solo primeros 5 errores
            print(f"   - {error}")
    
    print(f"\n🧪 Valid ({valid_path}):")
    print(f"   - Ejemplos: {valid_count}")
    print(f"   - Válido: {'✅' if valid_valid else '❌'}")
    if valid_errors:
        for error in valid_errors[:5]:
            print(f"   - {error}")
    
    # 2. Verificar requisitos mínimos
    print("\n2️⃣ Verificando requisitos...")
    
    total_examples = train_count + valid_count
    
    if total_examples < 10:
        print(f"   ⚠️ ADVERTENCIA: Solo tienes {total_examples} ejemplos")
        print(f"   📊 OpenAI recomienda:")
        print(f"      - Mínimo: 10 ejemplos")
        print(f"      - Recomendado: 50-100 ejemplos")
        print(f"      - Ideal: 500+ ejemplos")
        print(f"\n   💡 Acumula más conversaciones antes de hacer fine-tuning")
    else:
        print(f"   ✅ Tienes {total_examples} ejemplos (suficiente para empezar)")
    
    if not train_valid or not valid_valid:
        print("\n   ❌ Los archivos tienen errores. Corrígelos antes de subir.")
        return
    
    # 3. Subir archivos (si no es solo validación)
    if args.validate_only:
        print("\n✅ Validación completada (modo --validate-only)")
        return
    
    if total_examples < 10:
        print("\n⚠️ ¿Quieres continuar con menos de 10 ejemplos? (s/n): ", end='')
        response = input().lower()
        if response != 's':
            print("❌ Subida cancelada")
            return
    
    print("\n3️⃣ Subiendo archivos a OpenAI...")
    
    try:
        # Subir archivo de entrenamiento
        if train_count > 0:
            train_info = upload_file_to_openai(train_path)
            print(f"\n✅ Train subido:")
            print(f"   - ID: {train_info['id']}")
            print(f"   - Tamaño: {train_info['bytes']} bytes")
            print(f"   - Estado: {train_info['status']}")
        else:
            print("\n⚠️ Train vacío, no se sube")
            train_info = None
        
        # Subir archivo de validación
        if valid_count > 0:
            valid_info = upload_file_to_openai(valid_path)
            print(f"\n✅ Valid subido:")
            print(f"   - ID: {valid_info['id']}")
            print(f"   - Tamaño: {valid_info['bytes']} bytes")
            print(f"   - Estado: {valid_info['status']}")
        else:
            print("\n⚠️ Valid vacío, no se sube")
            valid_info = None
        
        # 4. Mostrar siguiente paso
        print("\n" + "=" * 80)
        print("✅ ARCHIVOS SUBIDOS EXITOSAMENTE")
        print("=" * 80)
        
        print("\n📝 SIGUIENTE PASO: Crear job de fine-tuning")
        print("\nEjecuta:")
        print("```python")
        print("from openai import OpenAI")
        print("client = OpenAI()")
        print()
        if train_info:
            print(f"# Crear job de fine-tuning")
            print(f"job = client.fine_tuning.jobs.create(")
            print(f"    training_file='{train_info['id']}',")
            if valid_info:
                print(f"    validation_file='{valid_info['id']}',")
            print(f"    model='gpt-3.5-turbo'")
            print(f")")
            print()
            print(f"# Ver estado")
            print(f"print(job.id)")
            print(f"print(job.status)")
        print("```")
        
        print("\n💡 O usa la interfaz web de OpenAI:")
        print("   https://platform.openai.com/finetune")
        
    except Exception as e:
        print(f"\n❌ Error subiendo archivos: {str(e)}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
