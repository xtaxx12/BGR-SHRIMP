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
    
    def generate_quote_pdf(self, price_info: Dict, user_phone: str = None) -> str:
        """
        Genera un PDF limpio y profesional según el diseño especificado
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
            
            # === TÍTULO PRINCIPAL ===
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=azul_marino,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph("COTIZACIÓN DE CAMARÓN", title_style))
            
            # === INFORMACIÓN GENERAL ===
            # Extraer datos del price_info
            producto = price_info.get('producto', 'N/A')
            talla = price_info.get('talla', 'N/A')
            cliente = price_info.get('cliente_nombre', 'Cliente')
            destino = price_info.get('destino', 'N/A')
            glaseo = price_info.get('glaseo_factor', 0.7)
            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # Tabla de información general
            info_data = [
                ['Fecha de Cotización', fecha_actual],
                ['Producto', producto],
                ['Talla', talla],
                ['Cliente', cliente],
                ['Destino', destino],
                ['Glaseo Solicitado', f"{int(glaseo * 100)}%"]
            ]
            
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
            
            # === TÍTULO COTIZACIÓN FOB ===
            fob_title_style = ParagraphStyle(
                'FOBTitle',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=15,  # Reducir espacio después del título
                alignment=TA_CENTER,
                textColor=azul_marino,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph("COTIZACIÓN FOB", fob_title_style))
            
            # === PRECIO FOB PRINCIPAL ===
            precio_final = price_info.get('precio_final_kg', 0)
            
            # Tabla del precio FOB con diseño destacado
            precio_data = [['PRECIO FOB USD/KG'], [f'${precio_final:.2f}']]
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
            story.append(Spacer(1, 25))  # Reducir espacio después del precio FOB
            
            # === TABLA DE DETALLES ===
            # Extraer valores para la tabla de detalles
            glaseo_pct = f"{int(glaseo * 100)}.0%"
            flete_kg = price_info.get('flete', 0)
            especificacion = f"{producto} - Talla {talla}"
            
            detalles_data = [
                ['Concepto', 'Detalle'],
                ['Glaseo Aplicado', glaseo_pct],
                ['Flete Incluido', f'${flete_kg:.2f}/kg'],
                ['Especificación', especificacion]
            ]
            
            detalles_table = Table(detalles_data, colWidths=[3*inch, 3*inch])
            detalles_table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                # Filas de datos
                ('BACKGROUND', (0, 1), (-1, -1), gris_claro),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),   # Concepto alineado a la izquierda
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),  # Detalle alineado a la derecha
                # Bordes y padding
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            
            story.append(detalles_table)
            
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