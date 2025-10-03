from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os
from typing import Dict
import logging

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
    
    def generate_quote_pdf(self, price_info: Dict, user_phone: str = None, language: str = "es") -> str:
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
            destino = price_info.get('destination', '')
            
            # Crear título dinámico con destino para CFR
            if flete_incluido and destino:
                tipo_cotizacion = f"CFR A {destino.upper()}"
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
                    "precio_header": f"PRECIO {tipo_cotizacion} USD/KG",
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
                    "precio_header": f"{tipo_cotizacion} PRICE USD/KG",
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
            destino = price_info.get('destination', 'N/A')
            glaseo_factor = price_info.get('glaseo_factor', 0.7)
            glaseo_percentage = price_info.get('glaseo_percentage')  # Porcentaje original
            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # Tabla de información general (multiidioma)
            info_data = [
                [t["fecha_cotizacion"], fecha_actual],
                [t["producto"], producto],
                [t["talla"], talla],
                [t["cliente"], cliente],
                [t["destino"], destino],
                [t["glaseo_solicitado"], f"{glaseo_percentage}%" if glaseo_percentage else f"{int(glaseo_factor * 100)}%"]
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