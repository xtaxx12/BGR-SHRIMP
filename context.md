 📄 IMPLEMENTACIÓN DE ENTRENAMIENTO CON MENSAJES DE USUARIOS — GUÍA TÉCNICA COMPLETA

Este documento describe cómo integrar en el sistema actual la capacidad de capturar mensajes de usuarios, anonimizar, filtrar, auto-etiquetar, exportar para fine-tuning o RAG, y hacer QA antes de incluir datos en el modelo.

Está diseñado como briefing completo para que otra IA pueda implementar los cambios en el sistema existente.

📌 1. Objetivo de la Implementación

Incorporar un flujo completo para usar mensajes reales de usuarios en el entrenamiento/mejora de la IA:

Consentimiento del usuario.

Captura automática de los mensajes.

Anonimización obligatoria.

Filtrado + análisis automático (intentos, productos, tallas, glaseo, etc.).

Revisión humana opcional.

Exportación a JSONL para fine-tuning o documentos para RAG.

Validación automática (QA) antes de incluir datos.

Integración con SessionManager, OpenAIService y otros servicios del proyecto.

📌 2. Archivos del Sistema que deben modificarse

El sistema está compuesto, principalmente, por los siguientes módulos relevantes para la integración:

Archivo	Función actual	Usos en la implementación
session.py	Manejo de sesiones, historial, persistencia	Añadir consentimiento + gancho ETL
openai_service.py	Llamadas a OpenAI, análisis de intención, parsing	Auto-etiquetado, análisis previo a QA
quality_assurance.py	Validación de tallas, glaseo, producto, precios	Validación de datos antes de entrenamiento
google_sheets.py	Ingeniero de precios desde sheets	Fuente para documentos RAG
interactive.py	Menús y flujos de conversación	Agregar solicitud de consentimiento
dependencies.py	Inyección de dependencias	Exponer servicios del pipeline de entrenamiento
📌 3. Consentimiento del Usuario (Requerido)

Antes de almacenar mensajes para entrenamiento, el usuario debe aceptar lo siguiente:

“Autorizo que mis mensajes sean utilizados de forma anonimizada para mejorar el sistema.”

Implementación sugerida:

Añadir atributo a las sesiones

    session["consent_for_training"] = True/False
Dónde implementarlo

En interactive.py, en el flujo de bienvenida del usuario.

En SessionManager.add_to_conversation() validar:

    if session.get("consent_for_training"):
        enqueue_for_training(message)

📌 4. Anonimización de Datos

Obligatoria antes de guardar datos para entrenamiento.

Funciones recomendadas

import re

def anonymize(text: str) -> str:
    text = re.sub(r'\+?\d[\d\-\s]{6,}\d', '[PHONE]', text)     # teléfonos
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)  # emails
    text = re.sub(r'\b\d{6,}\b', '[ID]', text)                 # números grandes
    text = re.sub(r'\b(av|avenida|calle|cra|cl|transv)\.? [^\n,]+', '[ADDRESS]', text, flags=re.I)
    return text


📌 5. Pipeline de Captura → Análisis → Etiquetado → Exportación
5.1. Captura

El sistema ya guarda todos los mensajes en:
    SessionManager.conversation_history

Cada entrada contiene:
    {
  "role": "user" | "assistant",
  "content": "texto..."
}

Agregar en SessionManager:

    if session.get("consent_for_training") and role == "user":
    push_to_etl_queue(user_id, content)

5.2. Filtrado inicial

Excluir mensajes que no sirven:

vacíos

saludos (“hola”, “ok”)

mensajes < 5 caracteres sin entidades

mensajes que no contienen producto/talla/solicitud clara

5.3. Análisis automático (auto-etiquetado)

Usar OpenAIService.analyze_user_intent().

Este método ya retorna:

    {
  "intent": "...",
  "product": "...",
  "size": "...",
  "glaseo_percentage": ...,
  "destination": "...",
  "quantity": ...,
  "confidence": 0.0–1.0
}


Se debe:

Guardar el análisis adjunto al ejemplo.

Enviar a revisión humana si confidence < 0.85.

5.4. Validación (QA)

Usar quality_assurance.py para validar:

Tallas permitidas

Productos válidos

Glaseo permitido

Precios dentro de rangos

Formato correcto

Ejemplo:
    qa.validate_product(product)
    qa.validate_size(size)
    qa.validate_glaseo(glaseo)

📌 6. Exportar Dataset para Fine-Tuning (JSONL)

Después de análisis + anonimización + QA, generar un archivo:

    data/finetune/train.jsonl
    data/finetune/valid.jsonl

Cada entrada:

    {
  "prompt": "Usuario: HLSO 16/20 con 20% glaseo\nAsistente:",
  "completion": " ¡Perfecto! Generando tu proforma...\n"
}

Script de exportación (listo para usar en el sistema)
    # export_for_finetune.py
    import json, random, re
    from pathlib import Path
    from services import get_session_manager

    S = get_session_manager()
    OUT = Path("data/finetune")
    OUT.mkdir(exist_ok=True, parents=True)

    def anonymize(text):
        text = re.sub(r'\+?\d[\d\-\s]{6,}\d', '[PHONE]', text)
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)
        text = re.sub(r'\b\d{6,}\b', '[ID]', text)
        return text

    examples = []

    for user_id, sess in S.sessions.items():
        if not sess.get("consent_for_training"): 
            continue

        history = sess.get("conversation_history", [])
        for i in range(len(history)-1):
            if history[i]['role']=="user" and history[i+1]['role']=="assistant":
                user_msg = anonymize(history[i]["content"]).strip()
                ai_msg   = anonymize(history[i+1]["content"]).strip()

                if len(user_msg) < 5: 
                    continue

                examples.append({
                    "prompt": f"Usuario: {user_msg}\nAsistente:",
                    "completion": f" {ai_msg}\n"
                })

    random.shuffle(examples)
    cut = int(len(examples) * 0.9)
    train = examples[:cut]
    valid = examples[cut:]

    with open(OUT/"train.jsonl", "w", encoding="utf-8") as f:
        for e in train:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    with open(OUT/"valid.jsonl", "w", encoding="utf-8") as f:
        for e in valid:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print("Export complete.")



📌 7. Alternativa Recomendadísima: RAG (Retrieval-Augmented Generation)

RAG evita tener que re-entrenar el modelo.

Pasos de Implementación

Convertir documentos (precios, FAQs, conversaciones útiles) en fragmentos pequeños.

Generar embeddings con OpenAI (text-embedding-3-small o similar).

Guardarlos en un vector DB:

FAISS (local)

Pinecone

Weaviate

Durante cada pregunta del usuario:

Recuperar top-k documentos.

Incluirlos en el prompt del modelo.

Enviar la respuesta final al usuario.

📌 8. Integración en Tiempo Real (Runtime)

Para cada mensaje:

Guardar en SessionManager.

Si hay consentimiento → colocar en ETL.

Analizar con OpenAIService.analyze_user_intent.

Si intent == “proforma”:

Preguntar por faltantes (talla, glaseo, cantidad).

Validar con QA.

Generar proforma si corresponde.

Guardar la respuesta en el historial.

📌 9. Hooks y Métricas

Agregar registros:

Número de ejemplos capturados

Número aprobados por QA

Ejemplos descartados

Errores de parseo/JSON

Confianza promedio del análisis

📌 10. MVP de Implementación (2 Semanas)
Semana 1

Consentimiento obligatorio

ETL queue

Anonimización

Script de exportación

Semana 2

Auto-etiquetado con OpenAIService

QA antes de exportar

Integración RAG básica (opcional)

Validación y documentación

📌 11. Beneficios

Cumplimiento legal (consent + anonimización)

Entrenamiento con datos reales

Eficiencia: auto-etiquetado con IA + revisión humana

Integración directa con tu código

Mejor rendimiento del bot

Actualización continua vía RAG sin re-entrenar

📌 12. Qué debe implementar la IA que reciba este documento

Crear función para bandera de consentimiento.

Ampliar SessionManager para:

Guardar consentimiento

Encolar mensajes

Implementar anonymize() en un módulo utilitario.

Crear pipeline ETL.

Integrar análisis con OpenAIService.

Validar datos con quality_assurance.py.

Generar export JSONL (fine-tune).

Implementar RAG inicial.

Ajustar flujos en interactive.py para solicitar información faltante.

Documentar métricas y logs.

📢 IMPORTANTE

La IA debe:

Respetar la arquitectura existente

No romper compatibilidad de servicios actuales

Escribir código limpio y modular

Validar que el pipeline no exponga datos sensibles

Incluir ejemplos concretos

Entregar TODO el código funcionando, no solo teoría