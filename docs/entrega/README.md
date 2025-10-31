# BGR Shrimp Bot — Documentación de Entrega (v2.0)

[Estado del proyecto] [badge-placeholder] [Última actualización: Enero 2025]

Descripción breve
-----------------
BGR Shrimp Bot es una solución orientada a automatizar consultas y ventas (proformas, precios, tallas) para BGR Export, integrando canales como WhatsApp (Twilio), Google Sheets y servicios de IA. Esta carpeta contiene la documentación de entrega organizada por rol y propósito.

Tabla de contenido
------------------
- Quick Start
- Documentos principales
  - Resumen Ejecutivo
  - Manual de Usuario
  - Manual Técnico
  - Guía de Troubleshooting
  - Documentación de API
  - Guía de Mantenimiento
- Deployment y Mantenimiento
- Troubleshooting rápido
- Contribuir / Cambios
- Contacto y Soporte
- Licencia y Confidencialidad
- Historial y Metadatos

Quick Start
-----------
Prerrequisitos:
- Python 3.10+ (o la versión indicada en el MANUAL_TECNICO)
- Acceso a la cuenta Twilio (SID, Auth Token) para integración WhatsApp
- Credenciales de Google (API/Service Account) para Google Sheets
- Clave de OpenAI (si se utiliza)
- Acceso a la base de datos / credenciales de almacenamiento

Pasos básicos:
1. Clonar el repositorio.
2. Crear y activar un entorno virtual: python -m venv .venv && source .venv/bin/activate
3. Instalar dependencias: pip install -r requirements.txt
4. Crear un archivo .env con las variables necesarias (ver abajo).
5. Ejecutar las validaciones: scripts/pre_deploy_checklist.py
6. Iniciar la aplicación (ver README raíz / MANUAL_TECNICO para comandos específicos).

Variables de entorno recomendadas (ejemplos)
- TWILIO_ACCOUNT_SID=
- TWILIO_AUTH_TOKEN=
- TWILIO_WHATSAPP_FROM=
- GOOGLE_SERVICE_ACCOUNT_JSON_PATH=
- OPENAI_API_KEY=
- DATABASE_URL=
- LOG_LEVEL=INFO

Documentos principales (resumen y enlaces)
-----------------------------------------
- 01-RESUMEN_EJECUTIVO.md — Overview para gerencia: objetivos, ROI, métricas clave.
- 02-MANUAL_USUARIO.md — Guía para usuarios finales: comandos, FAQs, casos de uso.
- 03-MANUAL_TECNICO.md — Documentación técnica: arquitectura, variables de entorno, despliegue.
- 04-GUIA_TROUBLESHOOTING.md — Diagnóstico y soluciones rápidas para soporte.
- 05-API_DOCUMENTATION.md — Endpoints, autenticación y ejemplos (incluye webhooks de Twilio).
- 06-GUIA_MANTENIMIENTO.md — Procedimientos de mantenimiento, backups y calendario.

(Archivos ubicados en la carpeta docs/entrega; ver cada archivo para detalles completos)

Deployment y mantenimiento
--------------------------
- Revisa 03-MANUAL_TECNICO.md para el proceso de despliegue y ramas recomendadas.
- Antes de cada release ejecutar: scripts/master_validation.py y scripts/pre_deploy_checklist.py
- Backups: seguir la sección "Backup y restauración" en 06-GUIA_MANTENIMIENTO.md
- Monitoreo y alertas: configurar logging (LOG_LEVEL) y un sistema de alertas para errores críticos.

Troubleshooting rápido
----------------------
- Problema de integración Twilio: validar variables TWILIO_* y revisar logs de Twilio.
- Problemas con Google Sheets: verificar el path de GOOGLE_SERVICE_ACCOUNT_JSON y permisos.
- Fallos de IA / OpenAI: revisar cuota y clave OPENAI_API_KEY, manejar errores por rate limit.
- Para pasos detallados seguir 04-GUIA_TROUBLESHOOTING.md.

Scripts de validación incluidos
-------------------------------
- scripts/master_validation.py
- scripts/pre_deploy_checklist.py
- scripts/validate_critical_points.py
- scripts/generate_quality_certificate.py

Contribuir y control de cambios
-------------------------------
- CAMBIOS_DDP.md contiene el historial detallado de cambios.
- Para propuestas de cambio: crear un branch con nombre tipo feature/xxx o fix/xxx y abrir PR describiendo el objetivo y pruebas realizadas.
- Tests y QA: seguir QUALITY_ASSURANCE.md antes de mergear.

Contacto y soporte
------------------
- Documentación y consultas: rojassebas765@gmail.com
- Soporte técnico (incidentes críticos): rojassebas765@gmail.com / +593 968058769 — Disponibilidad: 24/7 para incidentes críticos
- Mantenido por: Sebastián Rojas

Licencia y confidencialidad
---------------------------
- Confidencialidad: Uso interno de BGR Export
- Distribución: Prohibida sin autorización
- Copyright © 2025 BGR Export — Todos los derechos reservados

Historial y metadatos
---------------------
- Versión actual: 1.0
- Fecha: Enero 2025
- Próxima revisión: Febrero 2025
- Última actualización: Enero 2025

Notas finales y recomendaciones
-------------------------------
- Reemplaza los badges/placeholder por enlaces reales (status CI, cobertura, security scan).
- Mueve instrucciones de Quick Start al README raíz si deseas que nuevos contribuyentes las vean primero.
- Añade ejemplos de comandos concretos de inicio y ejemplos de conversación (si aplica) en 02-MANUAL_USUARIO.md para acelerar onboarding.
- Considera añadir una sección "Rollback" en 06-GUIA_MANTENIMIENTO.md con pasos de reversión seguros.
