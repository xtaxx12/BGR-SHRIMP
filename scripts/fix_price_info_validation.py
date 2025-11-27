"""
Script para agregar validación de error en price_info.
"""
import re

# Leer el archivo
with open('app/routes/whatsapp_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar todas las ocurrencias de "if price_info:" con "if price_info and not price_info.get('error'):"
# Pero solo en el contexto de pricing_service.get_shrimp_price

content = content.replace(
    "if price_info:",
    "if price_info and not price_info.get('error'):"
)

# Escribir el archivo
with open('app/routes/whatsapp_routes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Validación de error agregada en todas las verificaciones de price_info")
