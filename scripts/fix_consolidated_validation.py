"""
Script para agregar validación de productos no disponibles en cotizaciones consolidadas.
"""
import re

# Leer el archivo
with open('app/routes/whatsapp_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Patrón a buscar: después de failed_products.append y antes de if products_info:
# Solo si no hay ya una validación
pattern = r'(failed_products\.append\(f"\{product_data\[\'product\'\]\} \{product_data\[\'size\'\]\}"\)\n\n)(                    if products_info:)'

replacement = r'\1                    # 🆕 VALIDACIÓN: Si hay productos que fallaron, rechazar la cotización\n                    if validate_products_availability(failed_products, response, user_id):\n                        return PlainTextResponse(str(response), media_type="application/xml")\n                    \n\2'

# Aplicar el reemplazo solo donde no existe ya la validación
lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    new_lines.append(lines[i])
    
    # Si encontramos failed_products.append seguido de línea vacía y luego if products_info:
    if i < len(lines) - 2:
        if 'failed_products.append' in lines[i] and lines[i+1].strip() == '' and 'if products_info:' in lines[i+2]:
            # Verificar que no haya ya una validación
            if i < len(lines) - 3 and 'validate_products_availability' not in lines[i+3]:
                # Agregar la validación
                new_lines.append('')  # Línea vacía
                new_lines.append('                    # 🆕 VALIDACIÓN: Si hay productos que fallaron, rechazar la cotización')
                new_lines.append('                    if validate_products_availability(failed_products, response, user_id):')
                new_lines.append('                        return PlainTextResponse(str(response), media_type="application/xml")')
                i += 1  # Saltar la línea vacía que ya agregamos
    
    i += 1

# Escribir el archivo
with open('app/routes/whatsapp_routes.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("✅ Validación agregada en todos los lugares necesarios")
