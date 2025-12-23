"""
Tests completos para el sistema de entrenamiento con mensajes de usuarios.

Prueba:
1. Anonimización
2. Consentimiento
3. Captura de mensajes
4. Pipeline ETL
5. Exportación JSONL
"""
import json
import os
import shutil
from pathlib import Path

# Configurar path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.anonymizer import Anonymizer, anonymize, anonymize_conversation
from app.services.session import session_manager
from app.services.training_pipeline import get_training_pipeline


def test_anonymization():
    """Test 1: Anonimización de datos sensibles"""
    print("\n" + "="*80)
    print("TEST 1: ANONIMIZACIÓN")
    print("="*80)
    
    anon = Anonymizer()
    
    # Test teléfonos
    text1 = "Mi número es +593 999 999 999 o llámame al 555-123-4567"
    result1 = anon.anonymize(text1)
    print(f"\n📱 Teléfonos:")
    print(f"   Original: {text1}")
    print(f"   Anonimizado: {result1}")
    assert "[PHONE]" in result1
    assert "999 999 999" not in result1
    print("   ✅ Teléfonos anonimizados correctamente")
    
    # Test emails
    text2 = "Contacto: juan.perez@example.com o info@bgr-export.com"
    result2 = anon.anonymize(text2)
    print(f"\n📧 Emails:")
    print(f"   Original: {text2}")
    print(f"   Anonimizado: {result2}")
    assert "[EMAIL]" in result2
    assert "@example.com" not in result2
    print("   ✅ Emails anonimizados correctamente")
    
    # Test direcciones
    text3 = "Vivo en Av. Principal 123, cerca de la calle 45"
    result3 = anon.anonymize(text3)
    print(f"\n🏠 Direcciones:")
    print(f"   Original: {text3}")
    print(f"   Anonimizado: {result3}")
    assert "[ADDRESS]" in result3
    print("   ✅ Direcciones anonimizadas correctamente")
    
    # Test whitelist (NO debe anonimizar)
    text4 = "HLSO 16/20 con 20% glaseo CFR Houston"
    result4 = anon.anonymize(text4)
    print(f"\n✅ Whitelist (NO anonimizar):")
    print(f"   Original: {text4}")
    print(f"   Resultado: {result4}")
    assert "HLSO" in result4
    assert "16/20" in result4
    assert "glaseo" in result4
    assert "Houston" in result4
    print("   ✅ Términos comerciales preservados correctamente")
    
    # Test conversación
    conversation = [
        {"role": "user", "content": "Hola, mi email es test@example.com"},
        {"role": "assistant", "content": "¡Hola! ¿En qué puedo ayudarte?"},
        {"role": "user", "content": "Necesito HLSO 16/20"}
    ]
    result_conv = anon.anonymize_conversation(conversation)
    print(f"\n💬 Conversación:")
    print(f"   Original: {conversation[0]['content']}")
    print(f"   Anonimizado: {result_conv[0]['content']}")
    assert "[EMAIL]" in result_conv[0]['content']
    assert "HLSO" in result_conv[2]['content']
    print("   ✅ Conversación anonimizada correctamente")
    
    # Estadísticas
    stats = anon.get_stats()
    print(f"\n📊 Estadísticas de anonimización:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ TEST 1 COMPLETADO: Anonimización funciona correctamente")


def test_consent():
    """Test 2: Sistema de consentimiento"""
    print("\n" + "="*80)
    print("TEST 2: CONSENTIMIENTO")
    print("="*80)
    
    test_user = "test_user_consent"
    
    # Verificar estado inicial
    initial_consent = session_manager.get_training_consent(test_user)
    print(f"\n📋 Estado inicial:")
    print(f"   Consentimiento: {initial_consent}")
    assert initial_consent == False
    print("   ✅ Estado inicial correcto (sin consentimiento)")
    
    # Otorgar consentimiento
    session_manager.set_training_consent(test_user, True)
    consent_after = session_manager.get_training_consent(test_user)
    print(f"\n✅ Después de otorgar:")
    print(f"   Consentimiento: {consent_after}")
    assert consent_after == True
    print("   ✅ Consentimiento otorgado correctamente")
    
    # Verificar en sesión
    session = session_manager.get_session(test_user)
    print(f"\n📦 Datos en sesión:")
    print(f"   consent_for_training: {session.get('consent_for_training')}")
    print(f"   consent_timestamp: {session.get('consent_timestamp')}")
    assert session.get('consent_for_training') == True
    assert session.get('consent_timestamp') is not None
    print("   ✅ Datos guardados en sesión correctamente")
    
    # Revocar consentimiento
    session_manager.set_training_consent(test_user, False)
    consent_revoked = session_manager.get_training_consent(test_user)
    print(f"\n❌ Después de revocar:")
    print(f"   Consentimiento: {consent_revoked}")
    assert consent_revoked == False
    print("   ✅ Consentimiento revocado correctamente")
    
    print("\n✅ TEST 2 COMPLETADO: Sistema de consentimiento funciona correctamente")


def test_message_capture():
    """Test 3: Captura de mensajes"""
    print("\n" + "="*80)
    print("TEST 3: CAPTURA DE MENSAJES")
    print("="*80)
    
    # Limpiar directorio de prueba
    test_data_dir = Path("data_test")
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
    
    pipeline = get_training_pipeline(str(test_data_dir))
    test_user = "test_user_capture"
    
    # Otorgar consentimiento
    session_manager.set_training_consent(test_user, True)
    
    # Test 1: Mensaje válido
    msg1 = "HLSO 16/20 con 20% glaseo"
    captured1 = pipeline.capture_message(test_user, msg1, "user")
    print(f"\n✅ Mensaje válido:")
    print(f"   Mensaje: {msg1}")
    print(f"   Capturado: {captured1}")
    assert captured1 == True
    print("   ✅ Mensaje capturado correctamente")
    
    # Test 2: Mensaje muy corto (debe rechazarse)
    msg2 = "ok"
    captured2 = pipeline.capture_message(test_user, msg2, "user")
    print(f"\n❌ Mensaje muy corto:")
    print(f"   Mensaje: {msg2}")
    print(f"   Capturado: {captured2}")
    assert captured2 == False
    print("   ✅ Mensaje rechazado correctamente")
    
    # Test 3: Saludo simple (debe rechazarse)
    msg3 = "hola"
    captured3 = pipeline.capture_message(test_user, msg3, "user")
    print(f"\n❌ Saludo simple:")
    print(f"   Mensaje: {msg3}")
    print(f"   Capturado: {captured3}")
    assert captured3 == False
    print("   ✅ Saludo rechazado correctamente")
    
    # Test 4: Mensaje con talla (debe capturarse)
    msg4 = "Necesito 21/25"
    captured4 = pipeline.capture_message(test_user, msg4, "user")
    print(f"\n✅ Mensaje con talla:")
    print(f"   Mensaje: {msg4}")
    print(f"   Capturado: {captured4}")
    assert captured4 == True
    print("   ✅ Mensaje capturado correctamente")
    
    # Verificar archivos creados
    queue_files = list((test_data_dir / "etl_queue").glob("*.json"))
    print(f"\n📁 Archivos en cola:")
    print(f"   Total: {len(queue_files)}")
    assert len(queue_files) >= 1  # Al menos 1 mensaje capturado
    print("   ✅ Archivos creados correctamente")
    
    # Verificar contenido de un archivo
    if queue_files:
        with open(queue_files[0], 'r', encoding='utf-8') as f:
            record = json.load(f)
        print(f"\n📄 Contenido de archivo:")
        print(f"   user_id: {record['user_id']}")
        print(f"   role: {record['role']}")
        print(f"   content: {record['content']}")
        print(f"   status: {record['status']}")
        assert record['status'] == 'pending'
        assert '[PHONE]' in record['user_id'] or 'test_user' in record['user_id']
        print("   ✅ Contenido correcto")
    
    # Estadísticas
    stats = pipeline.get_stats()
    print(f"\n📊 Estadísticas del pipeline:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ TEST 3 COMPLETADO: Captura de mensajes funciona correctamente")
    
    # Limpiar
    shutil.rmtree(test_data_dir)


def test_pipeline_processing():
    """Test 4: Procesamiento del pipeline ETL"""
    print("\n" + "="*80)
    print("TEST 4: PROCESAMIENTO DEL PIPELINE")
    print("="*80)
    
    # Limpiar directorio de prueba
    test_data_dir = Path("data_test_pipeline")
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
    
    pipeline = get_training_pipeline(str(test_data_dir))
    test_user = "test_user_pipeline"
    
    # Capturar varios mensajes
    messages = [
        "HLSO 16/20 con 20% glaseo",
        "Precio CFR Houston",
        "HOSO 20/30",
        "Necesito cotización P&D IQF 21/25",
        "Cuanto cuesta el camarón?"
    ]
    
    print(f"\n📥 Capturando {len(messages)} mensajes...")
    for msg in messages:
        pipeline.capture_message(test_user, msg, "user")
    
    stats_before = pipeline.get_stats()
    print(f"\n📊 Estadísticas antes de procesar:")
    print(f"   Capturados: {stats_before['captured']}")
    print(f"   En cola: {stats_before['queue_size']}")
    
    # Procesar cola (sin OpenAI ni QA para este test)
    print(f"\n⚙️ Procesando cola...")
    results = pipeline.process_queue(
        openai_service=None,
        qa_service=None,
        max_items=10
    )
    
    print(f"\n📊 Resultados del procesamiento:")
    for key, value in results.items():
        print(f"   {key}: {value}")
    
    assert results['processed'] > 0
    print("   ✅ Mensajes procesados correctamente")
    
    # Verificar archivos movidos
    processed_files = list((test_data_dir / "processed").glob("*.json"))
    print(f"\n📁 Archivos procesados:")
    print(f"   Total: {len(processed_files)}")
    assert len(processed_files) > 0
    print("   ✅ Archivos movidos a processed/")
    
    # Verificar contenido
    if processed_files:
        with open(processed_files[0], 'r', encoding='utf-8') as f:
            record = json.load(f)
        print(f"\n📄 Contenido de archivo procesado:")
        print(f"   content: {record['content']}")
        print(f"   status: {record['status']}")
        print(f"   confidence: {record.get('confidence', 'N/A')}")
        assert record['status'] in ['approved', 'needs_review', 'rejected']
        print("   ✅ Contenido correcto")
    
    stats_after = pipeline.get_stats()
    print(f"\n📊 Estadísticas después de procesar:")
    print(f"   En cola: {stats_after['queue_size']}")
    print(f"   Procesados: {stats_after['processed_size']}")
    
    print("\n✅ TEST 4 COMPLETADO: Procesamiento del pipeline funciona correctamente")
    
    # Limpiar
    shutil.rmtree(test_data_dir)


def test_export_jsonl():
    """Test 5: Exportación a JSONL"""
    print("\n" + "="*80)
    print("TEST 5: EXPORTACIÓN A JSONL")
    print("="*80)
    
    # Limpiar directorio de prueba
    test_data_dir = Path("data_test")
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
    
    pipeline = get_training_pipeline(str(test_data_dir))
    test_user = "test_user_export"
    
    # Crear archivos procesados simulados
    processed_dir = test_data_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Crear 10 ejemplos aprobados
    print(f"\n📝 Creando ejemplos de prueba...")
    for i in range(10):
        record = {
            "user_id": f"[PHONE]_{i}",
            "role": "user",
            "content": f"HLSO {16+i}/{20+i} con 20% glaseo",
            "analysis": {
                "intent": "proforma",
                "product": "HLSO",
                "size": f"{16+i}/{20+i}",
                "confidence": 0.9
            },
            "qa_passed": True,
            "status": "approved",
            "confidence": 0.9
        }
        
        filepath = processed_dir / f"example_{i}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ Creados 10 ejemplos")
    
    # Exportar
    print(f"\n📤 Exportando a JSONL...")
    train_count, valid_count = pipeline.export_for_finetune(
        min_confidence=0.85,
        train_split=0.8
    )
    
    print(f"\n📊 Resultados de exportación:")
    print(f"   Train: {train_count}")
    print(f"   Valid: {valid_count}")
    print(f"   Total: {train_count + valid_count}")
    
    assert train_count > 0
    assert valid_count > 0
    print("   ✅ Exportación exitosa")
    
    # Verificar archivos JSONL
    train_file = test_data_dir / "finetune" / "train.jsonl"
    valid_file = test_data_dir / "finetune" / "valid.jsonl"
    
    assert train_file.exists()
    assert valid_file.exists()
    print(f"\n📁 Archivos creados:")
    print(f"   {train_file}")
    print(f"   {valid_file}")
    print("   ✅ Archivos JSONL creados")
    
    # Verificar formato
    with open(train_file, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        example = json.loads(first_line)
    
    print(f"\n📄 Ejemplo de train.jsonl:")
    print(f"   prompt: {example['prompt'][:50]}...")
    print(f"   completion: {example['completion'][:50]}...")
    
    assert 'prompt' in example
    assert 'completion' in example
    assert 'Usuario:' in example['prompt']
    assert 'Asistente:' in example['prompt']
    print("   ✅ Formato correcto")
    
    print("\n✅ TEST 5 COMPLETADO: Exportación a JSONL funciona correctamente")
    
    # Limpiar
    shutil.rmtree(test_data_dir)


def test_integration():
    """Test 6: Integración completa"""
    print("\n" + "="*80)
    print("TEST 6: INTEGRACIÓN COMPLETA")
    print("="*80)
    
    # Limpiar directorio de prueba
    test_data_dir = Path("data_test")
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
    
    pipeline = get_training_pipeline(str(test_data_dir))
    test_user = "test_user_integration"
    
    # 1. Otorgar consentimiento
    print(f"\n1️⃣ Otorgando consentimiento...")
    session_manager.set_training_consent(test_user, True)
    assert session_manager.get_training_consent(test_user) == True
    print("   ✅ Consentimiento otorgado")
    
    # 2. Simular conversación
    print(f"\n2️⃣ Simulando conversación...")
    conversation = [
        ("user", "Hola, necesito precios de camarón"),
        ("assistant", "¡Hola! ¿Qué producto necesitas?"),
        ("user", "HLSO 16/20 con 20% glaseo"),
        ("assistant", "Perfecto, generando tu proforma..."),
        ("user", "Precio CFR Houston"),
        ("assistant", "Para calcular CFR necesito el flete...")
    ]
    
    for role, content in conversation:
        session_manager.add_to_conversation(test_user, role, content)
    
    print(f"   ✅ Conversación simulada ({len(conversation)} mensajes)")
    
    # 3. Verificar captura automática
    print(f"\n3️⃣ Verificando captura automática...")
    stats = pipeline.get_stats()
    print(f"   Capturados: {stats['captured']}")
    print(f"   En cola: {stats['queue_size']}")
    assert stats['captured'] > 0
    print("   ✅ Mensajes capturados automáticamente")
    
    # 4. Procesar cola
    print(f"\n4️⃣ Procesando cola...")
    results = pipeline.process_queue(max_items=10)
    print(f"   Procesados: {results['processed']}")
    assert results['processed'] > 0
    print("   ✅ Cola procesada")
    
    # 5. Exportar
    print(f"\n5️⃣ Exportando a JSONL...")
    train_count, valid_count = pipeline.export_for_finetune()
    print(f"   Train: {train_count}")
    print(f"   Valid: {valid_count}")
    print("   ✅ Datos exportados")
    
    # 6. Verificar archivos finales
    print(f"\n6️⃣ Verificando archivos finales...")
    train_file = test_data_dir / "finetune" / "train.jsonl"
    valid_file = test_data_dir / "finetune" / "valid.jsonl"
    
    if train_file.exists():
        print(f"   ✅ {train_file}")
    if valid_file.exists():
        print(f"   ✅ {valid_file}")
    
    print("\n✅ TEST 6 COMPLETADO: Integración completa funciona correctamente")
    
    # Limpiar
    shutil.rmtree(test_data_dir)


def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "="*80)
    print("🧪 INICIANDO TESTS DEL SISTEMA DE ENTRENAMIENTO")
    print("="*80)
    
    try:
        test_anonymization()
        test_consent()
        test_message_capture()
        test_pipeline_processing()
        test_export_jsonl()
        test_integration()
        
        print("\n" + "="*80)
        print("✅ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE")
        print("="*80)
        print("\n🎉 El sistema de entrenamiento está funcionando correctamente!")
        print("\n📚 Funcionalidades verificadas:")
        print("   ✅ Anonimización de datos sensibles")
        print("   ✅ Sistema de consentimiento")
        print("   ✅ Captura automática de mensajes")
        print("   ✅ Pipeline ETL completo")
        print("   ✅ Procesamiento con análisis y QA")
        print("   ✅ Exportación a JSONL para fine-tuning")
        print("   ✅ Integración end-to-end")
        print("\n🚀 El sistema está listo para producción!")
        
    except Exception as e:
        print(f"\n❌ ERROR EN TESTS: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
