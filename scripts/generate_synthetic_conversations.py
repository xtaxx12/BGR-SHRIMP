"""
Script para generar conversaciones sintéticas basadas en mensajes reales.

Esto simula el flujo completo del bot para crear datos de entrenamiento.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.session import session_manager
from app.services.training_pipeline import get_training_pipeline

# Mensajes reales de usuarios
REAL_USER_MESSAGES = [
    """Buenas Tardes
Necesito precios para Contenedor Lagostino Vannamei Color A3 calidad Cocedero CFR Lisboa para lo siguiente talles:
Inteiro 0%
20/30
30/40
40/50

Colas Talle Real 1.7 kg.
21/25
31/35
36/40
41/50""",
    
    """Precios para esto por favor ..
HOSO 50-60 block 10x4
HLSO 16-20 block 10x4
HLSO 26-30 block 10x4
HLSO 36-40 block 10x4
HLSO 51-60 block 10x4
PYD TAIL OFF 61-70 IQF 5X2
16-20 EZPEEL IQF 10X2
26-30 EZPEEL IQF 10X2
DDP LA or Houston al 15% con 0.20 de flete""",
    
    "hazme una proforma para el cliente jose andres con el producto 16/20 sin cabeza con 20 de glaseo con flete a houston",
    
    "Cotizar un Contenedor de 30/40 con 0.15 de flete",
    
    """Precios para esto por favor ..
HOSO 50-60 block 10x4
HLSO 16-20 block 10x4
HLSO 26-30 block 10x4
HLSO 36-40 block 10x4
HLSO 51-60 block 10x4
PYD TAIL OFF 61-70 IQF 5X2
16-20 EZPEEL IQF 10X2
26-30 EZPEEL IQF 10X2
DDP LA or Houston al 15%""",
    
    """Hola Erick, como estas? podras ofertar otros tamaños de camaron? 
HLSO 16-20/ 21-25/26-30/31-35/36-40/41-50/51-60 
HOSO 20-30/30-40/40-50
BRINE
100% NET
20k/caja""",
]

# Respuestas típicas del asistente para cada tipo de mensaje
ASSISTANT_RESPONSES = {
    "cotizacion_consolidada": """✅ **Cotización consolidada detectada:**

🦐 **Inteiro (Entero):** {inteiro_sizes}
🦐 **Colas:** {colas_sizes}
🌍 **Destino:** {destination}
❄️ **Glaseo:** {glaseo}%

🚢 **Para calcular el precio CFR necesito el valor del flete a {destination}:**

💡 **Ejemplos:**
• "flete 0.20"
• "0.25 de flete"
• "con flete de 0.22"

¿Cuál es el valor del flete por kilo? 💰""",
    
    "cotizacion_simple": """✅ **Productos confirmados: {num_products} tallas**

{products_list}

🌍 **Destino:** {destination}
❄️ **Glaseo:** {glaseo}%

🚢 **Para calcular el precio CFR necesito el valor del flete a {destination}:**

💡 **Ejemplos:**
• "flete 0.20"
• "0.25 de flete"

¿Cuál es el valor del flete por kilo? 💰""",
    
    "cotizacion_generada": "✅ Cotización consolidada generada con flete ${flete} - {num_products} productos 🚢",
    
    "saludo": """👋 ¡Hola! Claro que sí, puedo cotizar esos tamaños.

Para generar la cotización necesito:
• Destino (CFR/CIF)
• Porcentaje de glaseo
• Valor del flete

¿Me confirmas estos datos? 🦐""",
}


def generate_conversation_1():
    """Conversación: Cotización consolidada Inteiro + Colas"""
    user_id = "synthetic_user_001"
    
    # Usuario solicita cotización
    user_msg = REAL_USER_MESSAGES[0]
    session_manager.add_to_conversation(user_id, 'user', user_msg)
    
    # Asistente solicita flete
    assistant_msg = ASSISTANT_RESPONSES["cotizacion_consolidada"].format(
        inteiro_sizes="20/30, 30/40, 40/50",
        colas_sizes="21/25, 31/35, 36/40, 41/50",
        destination="Lisboa",
        glaseo="0"
    )
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg)
    
    # Usuario proporciona flete
    user_msg_2 = "0.2"
    session_manager.add_to_conversation(user_id, 'user', user_msg_2)
    
    # Asistente genera cotización
    assistant_msg_2 = ASSISTANT_RESPONSES["cotizacion_generada"].format(
        flete="0.20",
        num_products="7"
    )
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg_2)
    
    print(f"✅ Conversación 1 generada: {user_id}")


def generate_conversation_2():
    """Conversación: Múltiples productos con flete especificado"""
    user_id = "synthetic_user_002"
    
    # Usuario solicita cotización con flete
    user_msg = REAL_USER_MESSAGES[1]
    session_manager.add_to_conversation(user_id, 'user', user_msg)
    
    # Asistente confirma y genera
    assistant_msg = """✅ **Productos confirmados: 8 tallas**

   1. HOSO 50/60
   2. HLSO 16/20
   3. HLSO 26/30
   4. HLSO 36/40
   5. HLSO 51/60
   6. PYD TAIL OFF 61/70
   7. EZPEEL 16/20
   8. EZPEEL 26/30

🌍 **Destino:** Houston
❄️ **Glaseo:** 15%
🚢 **Flete:** $0.20/kg

Generando cotización consolidada..."""
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg)
    
    # Asistente genera cotización
    assistant_msg_2 = ASSISTANT_RESPONSES["cotizacion_generada"].format(
        flete="0.20",
        num_products="8"
    )
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg_2)
    
    print(f"✅ Conversación 2 generada: {user_id}")


def generate_conversation_3():
    """Conversación: Proforma para cliente específico"""
    user_id = "synthetic_user_003"
    
    # Usuario solicita proforma
    user_msg = REAL_USER_MESSAGES[2]
    session_manager.add_to_conversation(user_id, 'user', user_msg)
    
    # Asistente confirma datos
    assistant_msg = """✅ **Datos confirmados:**

👤 **Cliente:** Jose Andres
🦐 **Producto:** HLSO 16/20
❄️ **Glaseo:** 20%
🌍 **Destino:** Houston

🚢 **Para calcular el precio CFR necesito el valor del flete a Houston:**

💡 **Ejemplos:**
• "flete 0.20"
• "0.25 de flete"

¿Cuál es el valor del flete por kilo? 💰"""
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg)
    
    # Usuario proporciona flete
    user_msg_2 = "flete 0.25"
    session_manager.add_to_conversation(user_id, 'user', user_msg_2)
    
    # Asistente genera proforma
    assistant_msg_2 = "✅ Proforma generada para Jose Andres - HLSO 16/20 con 20% glaseo y flete $0.25 a Houston 🚢"
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg_2)
    
    print(f"✅ Conversación 3 generada: {user_id}")


def generate_conversation_4():
    """Conversación: Cotización simple con flete"""
    user_id = "synthetic_user_004"
    
    # Usuario solicita cotización
    user_msg = REAL_USER_MESSAGES[3]
    session_manager.add_to_conversation(user_id, 'user', user_msg)
    
    # Asistente confirma y solicita más info
    assistant_msg = """✅ **Producto confirmado:**

🦐 **Talla:** 30/40
🚢 **Flete:** $0.15/kg

Para generar la cotización necesito:
• ¿Qué producto? (HLSO, HOSO, COOKED, etc.)
• ¿Destino? (CFR a qué puerto?)
• ¿Porcentaje de glaseo?

Por favor especifica estos datos 🦐"""
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg)
    
    # Usuario proporciona más info
    user_msg_2 = "HLSO CFR Lisboa con 20% glaseo"
    session_manager.add_to_conversation(user_id, 'user', user_msg_2)
    
    # Asistente genera cotización
    assistant_msg_2 = "✅ Cotización generada - HLSO 30/40 con 20% glaseo y flete $0.15 a Lisboa 🚢"
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg_2)
    
    print(f"✅ Conversación 4 generada: {user_id}")


def generate_conversation_5():
    """Conversación: Múltiples productos sin flete"""
    user_id = "synthetic_user_005"
    
    # Usuario solicita cotización
    user_msg = REAL_USER_MESSAGES[4]
    session_manager.add_to_conversation(user_id, 'user', user_msg)
    
    # Asistente solicita flete
    assistant_msg = ASSISTANT_RESPONSES["cotizacion_simple"].format(
        num_products="8",
        products_list="""   1. HOSO 50/60
   2. HLSO 16/20
   3. HLSO 26/30
   4. HLSO 36/40
   5. HLSO 51/60
   6. PYD TAIL OFF 61/70
   7. EZPEEL 16/20
   8. EZPEEL 26/30""",
        destination="Houston",
        glaseo="15"
    )
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg)
    
    # Usuario proporciona flete
    user_msg_2 = "0.22 de flete"
    session_manager.add_to_conversation(user_id, 'user', user_msg_2)
    
    # Asistente genera cotización
    assistant_msg_2 = ASSISTANT_RESPONSES["cotizacion_generada"].format(
        flete="0.22",
        num_products="8"
    )
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg_2)
    
    print(f"✅ Conversación 5 generada: {user_id}")


def generate_conversation_6():
    """Conversación: Saludo y consulta general"""
    user_id = "synthetic_user_006"
    
    # Usuario saluda y consulta
    user_msg = REAL_USER_MESSAGES[5]
    session_manager.add_to_conversation(user_id, 'user', user_msg)
    
    # Asistente responde amablemente
    assistant_msg = ASSISTANT_RESPONSES["saludo"]
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg)
    
    # Usuario proporciona datos
    user_msg_2 = "CFR Lisboa, 100% NET (sin glaseo), flete 0.20"
    session_manager.add_to_conversation(user_id, 'user', user_msg_2)
    
    # Asistente confirma y genera
    assistant_msg_2 = """✅ **Datos confirmados:**

🦐 **HLSO:** 16/20, 21/25, 26/30, 31/35, 36/40, 41/50, 51/60
🦐 **HOSO:** 20/30, 30/40, 40/50
🌍 **Destino:** Lisboa
❄️ **Glaseo:** 0% (100% NET)
🚢 **Flete:** $0.20/kg

Generando cotización consolidada para 10 tallas..."""
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg_2)
    
    # Asistente genera cotización
    assistant_msg_3 = ASSISTANT_RESPONSES["cotizacion_generada"].format(
        flete="0.20",
        num_products="10"
    )
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg_3)
    
    print(f"✅ Conversación 6 generada: {user_id}")


def generate_conversation_7():
    """Conversación: Variación de cotización simple"""
    user_id = "synthetic_user_007"
    
    # Usuario solicita cotización
    user_msg = "Necesito precio para HLSO 21/25 CFR Houston con 15% glaseo"
    session_manager.add_to_conversation(user_id, 'user', user_msg)
    
    # Asistente solicita flete
    assistant_msg = """✅ **Datos confirmados:**

🦐 **Producto:** HLSO 21/25
🌍 **Destino:** Houston
❄️ **Glaseo:** 15%

🚢 **Para calcular el precio CFR necesito el valor del flete a Houston:**

💡 **Ejemplos:**
• "flete 0.20"
• "0.25 de flete"

¿Cuál es el valor del flete por kilo? 💰"""
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg)
    
    # Usuario proporciona flete
    user_msg_2 = "con flete de 0.18"
    session_manager.add_to_conversation(user_id, 'user', user_msg_2)
    
    # Asistente genera cotización
    assistant_msg_2 = "✅ Proforma generada - HLSO 21/25 con 15% glaseo y flete $0.18 a Houston 🚢"
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg_2)
    
    print(f"✅ Conversación 7 generada: {user_id}")


def generate_conversation_8():
    """Conversación: Pregunta sobre disponibilidad"""
    user_id = "synthetic_user_008"
    
    # Usuario pregunta
    user_msg = "Tienes disponible HOSO 40/50 para CFR Lisboa?"
    session_manager.add_to_conversation(user_id, 'user', user_msg)
    
    # Asistente responde
    assistant_msg = """✅ Sí, tenemos disponible HOSO 40/50 para CFR Lisboa.

Para generar la cotización necesito:
• Porcentaje de glaseo
• Valor del flete a Lisboa

¿Me confirmas estos datos? 🦐"""
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg)
    
    # Usuario proporciona datos
    user_msg_2 = "20% glaseo, flete 0.22"
    session_manager.add_to_conversation(user_id, 'user', user_msg_2)
    
    # Asistente genera cotización
    assistant_msg_2 = "✅ Proforma generada - HOSO 40/50 con 20% glaseo y flete $0.22 a Lisboa 🚢"
    session_manager.add_to_conversation(user_id, 'assistant', assistant_msg_2)
    
    print(f"✅ Conversación 8 generada: {user_id}")


def main():
    """Función principal."""
    print("=" * 80)
    print("🤖 GENERADOR DE CONVERSACIONES SINTÉTICAS")
    print("=" * 80)
    
    # Dar consentimiento a todos los usuarios sintéticos
    print("\n1️⃣ Configurando usuarios sintéticos...")
    for i in range(1, 9):
        user_id = f"synthetic_user_{i:03d}"
        session_manager.set_training_consent(user_id, True)
    print("   ✅ 8 usuarios configurados con consentimiento")
    
    # Generar conversaciones
    print("\n2️⃣ Generando conversaciones...")
    generate_conversation_1()
    generate_conversation_2()
    generate_conversation_3()
    generate_conversation_4()
    generate_conversation_5()
    generate_conversation_6()
    generate_conversation_7()
    generate_conversation_8()
    
    # Verificar archivos capturados
    print("\n3️⃣ Verificando captura...")
    pipeline = get_training_pipeline()
    stats = pipeline.get_stats()
    
    print(f"   📥 Archivos en cola: {stats['queue_size']}")
    print(f"   📝 Mensajes capturados: {stats['captured']}")
    
    # Exportar
    print("\n4️⃣ Exportando datos...")
    import subprocess
    result = subprocess.run(
        ["python", "scripts/export_for_finetune.py", "--min-confidence", "0.5", "--source", "both"],
        capture_output=True,
        text=True
    )
    
    # Mostrar resultados
    for line in result.stdout.split('\n'):
        if 'Train:' in line or 'Valid:' in line or 'Total:' in line:
            print(f"   {line.strip()}")
    
    print("\n" + "=" * 80)
    print("✅ CONVERSACIONES GENERADAS EXITOSAMENTE")
    print("=" * 80)
    print("\n💡 Ahora puedes:")
    print("   1. Validar: python scripts/upload_to_openai.py --validate-only")
    print("   2. Subir: python scripts/upload_to_openai.py")


if __name__ == "__main__":
    main()
