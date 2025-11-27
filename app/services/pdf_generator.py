import logging
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self):
        self.output_dir = "generated_pdfs"
        self.ensure_output_dir()

    def ensure_output_dir(self):
        """
        Asegura que el directorio de salida existe
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_quote_pdf(self, price_info: dict, user_phone: str = None, language: str = "es") -> str:
        """
        Genera un PDF dinámico (FOB/CFR) y multiidioma según las reglas de negocio
        
        Args:
            price_info: Datos de la cotización
            user_phone: Teléfono del usuario
            language: Idioma del PDF ("es" para español, "en" para inglés)
        """
        try:
            logger.debug(f"🔍 Iniciando generación PDF con datos: {price_info}")

            # Generar nombre único para el archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if user_phone:
                cleaned_phone = user_phone.replace("+", "").replace(":", "")
                phone_suffix = cleaned_phone[-4:] if len(cleaned_phone) >= 4 else cleaned_phone.zfill(4)
            else:
                phone_suffix = "0000"
            filename = f"cotizacion_BGR_{timestamp}_{phone_suffix}.pdf"
            filepath = os.path.join(self.output_dir, filename)

            # Crear documento PDF
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )

            story = []
            styles = getSampleStyleSheet()

            # Colores corporativos BGR Export
            azul_marino = colors.HexColor('#1e3a8a')  # Azul marino
            naranja = colors.HexColor('#ea580c')      # Naranja
            gris_claro = colors.HexColor('#f8fafc')   # Gris muy claro

            # === REGLAS DE NEGOCIO ===
            # Determinar si es FOB o CFR basado en si se solicitó flete
            flete_incluido = price_info.get('incluye_flete', False)
            destino_completo = price_info.get('destination', '')

            # Extraer solo el país del destino (antes de "Para")
            if destino_completo and " para " in destino_completo.lower():
                destino_pais = destino_completo.split(" para ")[0].strip()
            elif destino_completo and " Para " in destino_completo:
                destino_pais = destino_completo.split(" Para ")[0].strip()
            else:
                destino_pais = destino_completo

            # Crear título dinámico con destino para CFR
            if flete_incluido and destino_pais:
                tipo_cotizacion = f"CFR A {destino_pais.upper()}"
            elif flete_incluido:
                tipo_cotizacion = "CFR"
            else:
                tipo_cotizacion = "FOB"

            # === TRADUCCIONES ===
            translations = {
                "es": {
                    "cotizacion": f"COTIZACIÓN {tipo_cotizacion}",
                    "fecha_cotizacion": "Fecha de Cotización",
                    "producto": "Producto",
                    "talla": "Talla",
                    "cliente": "Cliente",
                    "destino": "Destino",
                    "glaseo_solicitado": "Glaseo Solicitado",
                    "precio_header": f"PRECIO {'CFR' if flete_incluido else 'FOB'} USD/KG",
                    "concepto": "Concepto",
                    "detalle": "Detalle",
                    "glaseo_aplicado": "Glaseo Aplicado",
                    "especificacion": "Especificación"
                },
                "en": {
                    "cotizacion": f"{tipo_cotizacion} QUOTATION",
                    "fecha_cotizacion": "Quotation Date",
                    "producto": "Product",
                    "talla": "Size",
                    "cliente": "Client",
                    "destino": "Destination",
                    "glaseo_solicitado": "Requested Glazing",
                    "precio_header": f"{'CFR' if flete_incluido else 'FOB'} PRICE USD/KG",
                    "concepto": "Concept",
                    "detalle": "Detail",
                    "glaseo_aplicado": "Applied Glazing",
                    "especificacion": "Specification"
                }
            }

            # Seleccionar idioma
            t = translations.get(language, translations["es"])

            # === LOGO Y ENCABEZADO ===
            logo_path = os.path.join("data", "logoBGR.png")
            if os.path.exists(logo_path):
                try:
                    # Dimensiones basadas en 714x146 pixels (proporción ~4.9:1)
                    # Convertir a pulgadas manteniendo la proporción
                    logo_width = 4.9*inch  # Más ancho
                    logo_height = 1*inch   # Más bajo
                    logo_img = Image(logo_path, width=logo_width, height=logo_height)
                    story.append(logo_img)
                except Exception as e:
                    logger.warning(f"No se pudo cargar el logo: {e}")

            story.append(Spacer(1, 15))  # Reducir espacio después del logo

            # === SIN TÍTULO PRINCIPAL (eliminado según solicitud) ===

            # === INFORMACIÓN GENERAL ===
            # Extraer datos del price_info
            producto = price_info.get('producto', 'N/A')
            talla = price_info.get('talla', 'N/A')
            cliente = price_info.get('cliente_nombre', 'Cliente')
            # Usar solo el país para el destino en el PDF (ya calculado arriba)
            destino = destino_pais if destino_pais else 'N/A'
            glaseo_factor = price_info.get('factor_glaseo') if price_info.get('factor_glaseo') is not None else price_info.get('glaseo_factor')
            glaseo_percentage = price_info.get('glaseo_percentage')  # Porcentaje original
            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")

            # Calcular porcentaje de glaseo para mostrar en el PDF
            # IMPORTANTE: glaseo_percentage puede ser 0 (sin glaseo) o None (no especificado)
            if glaseo_percentage is not None:
                glaseo_display = f"{glaseo_percentage}%"
            elif glaseo_factor is not None:
                # Calcular porcentaje desde el factor: factor 0.80 = 20% glaseo
                glaseo_percent_calc = int((1 - glaseo_factor) * 100)
                glaseo_display = f"{glaseo_percent_calc}%"
            else:
                glaseo_display = "N/A"

            # Tabla de información general (multiidioma)
            info_data = [
                [t["fecha_cotizacion"], fecha_actual],
                [t["producto"], producto],
                [t["talla"], talla],
                [t["cliente"], cliente],
                [t["destino"], destino],
                [t["glaseo_solicitado"], glaseo_display]
            ]

            # Nota: Información de flete eliminada por solicitud del usuario

            info_table = Table(info_data, colWidths=[2.5*inch, 3*inch])
            info_table.setStyle(TableStyle([
                # Encabezados con fondo azul marino
                ('BACKGROUND', (0, 0), (0, -1), azul_marino),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white]),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))

            story.append(info_table)
            story.append(Spacer(1, 20))  # Reducir espacio antes del título FOB

            # === TÍTULO COTIZACIÓN (FOB/CFR dinámico) ===
            cotizacion_title_style = ParagraphStyle(
                'CotizacionTitle',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=15,
                alignment=TA_CENTER,
                textColor=azul_marino,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(t["cotizacion"], cotizacion_title_style))

            # === PRECIO PRINCIPAL (FOB/CFR dinámico) ===
            precio_final = price_info.get('precio_final_kg', 0)

            # Debug: Verificar qué precio se está usando
            logger.info(f"🔍 PDF Generator - Precio CFR: ${precio_final:.2f}")
            logger.info(f"🔍 PDF Generator - price_info keys: {list(price_info.keys())}")
            logger.info("🔍 PDF Generator - Todos los precios:")
            logger.info(f"   - precio_kg: ${price_info.get('precio_kg', 0):.2f}")
            logger.info(f"   - precio_fob_kg: ${price_info.get('precio_fob_kg', 0):.2f}")
            logger.info(f"   - precio_glaseo_kg: ${price_info.get('precio_glaseo_kg', 0):.2f}")
            logger.info(f"   - precio_fob_con_glaseo_kg: ${price_info.get('precio_fob_con_glaseo_kg', 0):.2f}")
            logger.info(f"   - precio_final_kg: ${price_info.get('precio_final_kg', 0):.2f}")
            logger.info(f"   - flete: ${price_info.get('flete', 0):.2f}")
            logger.info(f"   - factor_glaseo: {price_info.get('factor_glaseo', 0)}")

            # Tabla del precio con diseño destacado
            precio_data = [[t["precio_header"]], [f'${precio_final:.2f}']]
            precio_table = Table(precio_data, colWidths=[3*inch])
            precio_table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (0, 0), azul_marino),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (0, 0), 14),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                # Precio
                ('BACKGROUND', (0, 1), (0, 1), colors.white),
                ('TEXTCOLOR', (0, 1), (0, 1), azul_marino),
                ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (0, 1), 24),
                ('ALIGN', (0, 1), (0, 1), 'CENTER'),
                ('VALIGN', (0, 1), (0, 1), 'MIDDLE'),  # Centrado vertical
                # Bordes y padding
                ('GRID', (0, 0), (-1, -1), 2, colors.black),
                ('TOPPADDING', (0, 0), (0, 0), 12),      # Encabezado
                ('BOTTOMPADDING', (0, 0), (0, 0), 12),   # Encabezado
                ('TOPPADDING', (0, 1), (0, 1), 15),      # Precio - más padding arriba
                ('BOTTOMPADDING', (0, 1), (0, 1), 15),   # Precio - más padding abajo
            ]))

            # Centrar la tabla del precio
            precio_centered = Table([[precio_table]], colWidths=[doc.width])
            precio_centered.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ]))

            story.append(precio_centered)
            # === TABLA DE DETALLES ELIMINADA (según solicitud) ===

            # Generar PDF
            doc.build(story)

            # Verificar que el archivo se creó correctamente
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                logger.debug(f"✅ PDF generado exitosamente: {filepath}")
                logger.debug(f"📊 Tamaño del archivo: {file_size} bytes")
                return filepath
            else:
                logger.error(f"❌ PDF no se creó en la ruta esperada: {filepath}")
                return None

        except Exception as e:
            logger.error(f"❌ Error generando PDF: {str(e)}")
            return None

    def generate_consolidated_quote_pdf(self, products_info: list, user_phone: str = None, language: str = "es", glaseo_percentage: int = 20, destination: str = None) -> str:
        """
        Genera un PDF consolidado con múltiples productos
        
        Args:
            products_info: Lista de diccionarios con información de precios de cada producto
            user_phone: Teléfono del usuario
            language: Idioma del PDF
            glaseo_percentage: Porcentaje de glaseo aplicado
            destination: Destino de envío
        """
        try:
            logger.info(f"📄 Generando PDF consolidado con {len(products_info)} productos")

            # Generar nombre único para el archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if user_phone:
                cleaned_phone = user_phone.replace("+", "").replace(":", "")
                phone_suffix = cleaned_phone[-4:] if len(cleaned_phone) >= 4 else cleaned_phone.zfill(4)
            else:
                phone_suffix = "0000"
            filename = f"cotizacion_BGR_consolidada_{timestamp}_{phone_suffix}.pdf"
            filepath = os.path.join(self.output_dir, filename)

            # Crear documento PDF
            doc = SimpleDocTemplate(
                filepath,
                pagesize=letter,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )

            # Contenedor para elementos del PDF
            story = []

            # Colores corporativos
            azul_marino = colors.HexColor('#1e3a8a')
            naranja = colors.HexColor('#f97316')

            # === LOGO ===
            logo_path = "app/static/logo_bgr.png"
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=3*inch, height=0.8*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.3*inch))

            # === INFORMACIÓN GENERAL ===
            styles = getSampleStyleSheet()

            # Traducciones
            translations = {
                "es": {
                    "titulo": "COTIZACIÓN CONSOLIDADA",
                    "fecha": "Fecha de Cotización",
                    "destino": "Destino",
                    "glaseo": "Glaseo Aplicado",
                    "producto": "PRODUCTO",
                    "talla": "TALLA",
                    "precio_fob": "PRECIO FOB USD/KG",
                    "precio_cfr": "PRECIO CFR USD/KG",
                    "contacto": "Contacto: BGR Export | amerino@bgrexport.com | +593 98-805-7425",
                    "notas": "NOTAS IMPORTANTES:",
                    "nota1": "• Precios sujetos a disponibilidad y confirmación.",
                    "nota2": "• Validez de la cotización: 7 días.",
                    "nota3": "• Condiciones de pago: Según acuerdo comercial."
                },
                "en": {
                    "titulo": "CONSOLIDATED QUOTATION",
                    "fecha": "Quotation Date",
                    "destino": "Destination",
                    "glaseo": "Glaze Applied",
                    "producto": "PRODUCT",
                    "talla": "SIZE",
                    "precio_fob": "FOB PRICE USD/KG",
                    "precio_cfr": "CFR PRICE USD/KG",
                    "contacto": "Contact: BGR Export | amerino@bgrexport.com | +593 98-805-7425",
                    "notas": "IMPORTANT NOTES:",
                    "nota1": "• Prices subject to availability and confirmation.",
                    "nota2": "• Quote validity: 7 days.",
                    "nota3": "• Payment terms: According to commercial agreement."
                }
            }

            t = translations.get(language, translations["es"])

            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=azul_marino,
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(t["titulo"], title_style))

            # Información general
            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
            info_data = [
                [t["fecha"], fecha_actual],
            ]

            if destination:
                info_data.append([t["destino"], destination])

            info_data.append([t["glaseo"], f"{glaseo_percentage}%"])

            info_table = Table(info_data, colWidths=[2.5*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e5e7eb')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.3*inch))

            # === TABLA DE PRODUCTOS ===
            # Encabezados
            table_data = [[
                t["producto"],
                t["talla"],
                t["precio_fob"],
                t["precio_cfr"]
            ]]

            # Agregar cada producto
            for product_info in products_info:
                producto = product_info.get('producto', 'N/A')
                talla = product_info.get('talla', 'N/A')
                precio_fob = product_info.get('precio_fob_kg', 0)
                precio_cfr = product_info.get('precio_final_kg', 0)

                table_data.append([
                    producto,
                    talla,
                    f"${precio_fob:.2f}",
                    f"${precio_cfr:.2f}"
                ])

            # Crear tabla
            products_table = Table(table_data, colWidths=[2*inch, 1.2*inch, 1.7*inch, 1.7*inch])
            products_table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                # Datos
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Producto
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Talla
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Precios
                # Bordes y padding
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                # Alternar colores de filas
                *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f3f4f6'))
                  for i in range(2, len(table_data), 2)]
            ]))

            story.append(products_table)
            story.append(Spacer(1, 0.3*inch))

            # === NOTAS ===
            notes_style = ParagraphStyle(
                'Notes',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.black,
                spaceAfter=5
            )

            story.append(Paragraph(f"<b>{t['notas']}</b>", notes_style))
            story.append(Paragraph(t['nota1'], notes_style))
            story.append(Paragraph(t['nota2'], notes_style))
            story.append(Paragraph(t['nota3'], notes_style))
            story.append(Spacer(1, 0.2*inch))

            # === CONTACTO ===
            contact_style = ParagraphStyle(
                'Contact',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER
            )
            story.append(Paragraph(t['contacto'], contact_style))

            # Generar PDF
            doc.build(story)

            if os.path.exists(filepath):
                logger.info(f"✅ PDF consolidado generado: {filepath}")
                return filepath
            else:
                logger.error(f"❌ Error: PDF no se creó en {filepath}")
                return None

        except Exception as e:
            logger.error(f"❌ Error generando PDF consolidado: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def get_language_options(self) -> str:
        """
        Retorna las opciones de idioma para el PDF
        """
        return "🌐 **Seleccione idioma del PDF:**\n\n1️⃣ 🇪🇸 Español\n2️⃣ 🇺🇸 English\n\n💡 Responda con el número de su opción"

    def parse_language_selection(self, user_input: str) -> str:
        """
        Parsea la selección de idioma del usuario
        
        Returns:
            "es" para español, "en" para inglés, None si no es válido
        """
        user_input = user_input.lower().strip()

        # Opciones numéricas
        if user_input in ['1', '1️⃣']:
            return "es"
        elif user_input in ['2', '2️⃣']:
            return "en"

        # Opciones por nombre
        if any(word in user_input for word in ['español', 'spanish', 'es', 'esp']):
            return "es"
        elif any(word in user_input for word in ['english', 'inglés', 'ingles', 'en', 'eng']):
            return "en"

        return None

    def cleanup_old_pdfs(self, days_old: int = 7):
        """
        Limpia PDFs antiguos para ahorrar espacio
        """
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days_old * 24 * 60 * 60)

            for filename in os.listdir(self.output_dir):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(self.output_dir, filename)
                    file_time = os.path.getmtime(filepath)

                    if file_time < cutoff_time:
                        os.remove(filepath)
                        logger.info(f"🗑️ PDF antiguo eliminado: {filename}")

        except Exception as e:
            logger.error(f"❌ Error limpiando PDFs antiguos: {str(e)}")
