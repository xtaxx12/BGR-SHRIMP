from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
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
        Genera un PDF profesional con la cotización
        """
        try:
            # Generar nombre único para el archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            phone_suffix = user_phone.replace("+", "").replace(":", "")[-4:] if user_phone else "0000"
            filename = f"cotizacion_BGR_{timestamp}_{phone_suffix}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            logger.info(f"📁 Directorio de salida: {self.output_dir}")
            logger.info(f"📄 Nombre del archivo: {filename}")
            logger.info(f"🗂️ Ruta completa: {filepath}")
            logger.info(f"📍 Directorio actual: {os.getcwd()}")
            
            # Crear documento PDF
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Contenido del PDF
            story = []
            styles = getSampleStyleSheet()
            
            # Estilo personalizado para el título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#1f4e79')
            )
            
            # Estilo para subtítulos
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=12,
                textColor=colors.HexColor('#2f5f8f')
            )
            
            # Estilo para texto normal
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=6
            )
            
            # Encabezado con logo
            logo_path = os.path.join("data", "logoBGR.png")
            
            if os.path.exists(logo_path):
                try:
                    # Crear imagen del logo con tamaño optimizado
                    logo_img = Image(logo_path, width=4*inch, height=2*inch)
                    
                    # Crear tabla para centrar el logo
                    header_data = [[logo_img]]
                    header_table = Table(header_data, colWidths=[6*inch])
                    header_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ]))
                    
                    story.append(header_table)
                    story.append(Spacer(1, 15))
                    
                except Exception as logo_error:
                    logger.warning(f"⚠️ Error cargando logo: {logo_error}")
                    # Fallback al título de texto si no se puede cargar el logo
                    story.append(Paragraph("🦐 BGR EXPORT", title_style))
                    story.append(Spacer(1, 20))
            else:
                logger.warning(f"⚠️ Logo no encontrado en: {logo_path}")
                # Fallback al título de texto
                story.append(Paragraph("🦐 BGR EXPORT", title_style))
                story.append(Spacer(1, 20))
            
            # Subtítulo
            story.append(Paragraph("Cotización de Camarón", subtitle_style))
            story.append(Spacer(1, 20))
            
            # Información de la cotización
            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            info_data = [
                ["Fecha de Cotización:", fecha_actual],
                ["Producto:", price_info.get('producto', 'N/A')],
                ["Talla:", price_info.get('talla', 'N/A')]
            ]
            
            # Agregar cliente si está disponible
            if price_info.get('cliente_nombre'):
                info_data.append(["Cliente:", price_info['cliente_nombre'].title()])
            
            if price_info.get('destination'):
                info_data.append(["Destino:", price_info['destination']])
            
            if price_info.get('quantity'):
                info_data.append(["Cantidad:", f"{price_info['quantity']} {price_info.get('unit', 'lb')}"])
            
            # Agregar glaseo si fue especificado por el usuario
            if price_info.get('calculo_dinamico') and price_info.get('factor_glaseo'):
                glaseo_percent = price_info['factor_glaseo'] * 100
                if glaseo_percent != 70:  # Solo mostrar si es diferente al estándar
                    info_data.append(["Glaseo solicitado:", f"{glaseo_percent:.0f}%"])
            
            info_table = Table(info_data, colWidths=[2*inch, 3*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 30))
            
            # Sección de precios mejorada y más atractiva
            story.append(Paragraph("💰 COTIZACIÓN FOB", subtitle_style))
            story.append(Spacer(1, 15))
            
            # Obtener precio final y datos
            if price_info.get('calculo_dinamico') and 'precio_final_kg' in price_info:
                precio_kg = price_info['precio_final_kg']
                precio_lb = price_info['precio_final_lb']
                glaseo_factor = price_info.get('factor_glaseo', 0)
                flete = price_info.get('flete', 0)
            elif 'precio_flete_kg' in price_info:
                precio_kg = price_info['precio_flete_kg']
                precio_lb = price_info['precio_flete_lb']
                glaseo_factor = 0.7  # Default
                flete = 0.22  # Default
            else:
                precio_kg = price_info.get('precio_kg', 0)
                precio_lb = price_info.get('precio_lb', 0)
                glaseo_factor = 0.7
                flete = 0.22
            
            # Verificar si es Houston (solo kilos)
            destination = price_info.get('destination', '')
            is_houston = destination.lower() == 'houston'
            
            # Tabla principal de precios - adaptada según destino
            if is_houston:
                main_price_data = [
                    ["PRECIO FOB", "POR KILOGRAMO"],
                    ["", f"${precio_kg:.2f}"]
                ]
                main_price_table = Table(main_price_data, colWidths=[3*inch, 3*inch])
            else:
                main_price_data = [
                    ["PRECIO FOB", "POR KILOGRAMO", "POR LIBRA"],
                    ["", f"${precio_kg:.2f}", f"${precio_lb:.2f}"]
                ]
                main_price_table = Table(main_price_data, colWidths=[2*inch, 2*inch, 2*inch])
            main_price_table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                
                # Fila de precios
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f0f8ff')),
                ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
                ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 1), (-1, 1), 18),
                
                # Bordes
                ('GRID', (0, 0), (-1, -1), 1.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(main_price_table)
            story.append(Spacer(1, 20))
            
            # Información adicional elegante
            story.append(Paragraph("📋 ESPECIFICACIONES", subtitle_style))
            story.append(Spacer(1, 10))
            
            # Tabla de especificaciones
            specs_data = [
                ["Concepto", "Valor"],
                ["Glaseo aplicado", f"{glaseo_factor:.1%}"],
                ["Flete incluido", f"${flete:.2f}"],
               
            ]
            
            specs_table = Table(specs_data, colWidths=[3*inch, 3*inch])
            specs_table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f5f8f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                
                # Datos
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f8f8')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                
                # Bordes
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            
            story.append(specs_table)
            story.append(Spacer(1, 30))
            
            # Agregar espacio después de la tabla de precios
            story.append(Spacer(1, 30))
            
            # Cálculo de total si hay cantidad - simplificado
            if price_info.get('quantity'):
                story.append(Paragraph("📊 TOTAL ESTIMADO", subtitle_style))
                story.append(Spacer(1, 10))
                
                try:
                    qty = float(price_info['quantity'].replace(',', ''))
                    unit = price_info.get('unit', 'lb')
                    
                    # Usar precio final
                    if price_info.get('calculo_dinamico') and 'precio_final_kg' in price_info:
                        if unit == 'kg':
                            unit_price = price_info['precio_final_kg']
                        else:
                            unit_price = price_info['precio_final_lb']
                    elif 'precio_flete_kg' in price_info:
                        if unit == 'kg':
                            unit_price = price_info['precio_flete_kg']
                        else:
                            unit_price = price_info['precio_flete_lb']
                    else:
                        if unit == 'kg':
                            unit_price = price_info.get('precio_kg', 0)
                        else:
                            unit_price = price_info.get('precio_lb', 0)
                    
                    total = qty * unit_price
                    
                    # Tabla simple de total
                    total_data = [
                        ["Cantidad", "Total FOB"],
                        [f"{price_info['quantity']} {unit}", f"${total:,.2f}"]
                    ]
                    
                    total_table = Table(total_data, colWidths=[3*inch, 3*inch])
                    total_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fff2cc')),
                        ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
                        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 1), (-1, 1), 16),
                        ('GRID', (0, 0), (-1, -1), 2, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    
                    story.append(total_table)
                    story.append(Spacer(1, 30))
                    
                except:
                    pass
            
            # Pie de página
            story.append(Spacer(1, 50))
            
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
            
            story.append(Paragraph("Precios FOB sujetos a confirmación final", footer_style))
            story.append(Paragraph("BGR Export - Camarón Premium", footer_style))
            
            # Generar PDF
            doc.build(story)
            
            # Verificar que el archivo se creó correctamente
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                logger.info(f"✅ PDF generado exitosamente: {filepath}")
                logger.info(f"📊 Tamaño del archivo: {file_size} bytes")
                return filepath
            else:
                logger.error(f"❌ PDF no se creó en la ruta esperada: {filepath}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error generando PDF: {str(e)}")
            return None
    
    def _get_flete_description(self, price_info: Dict) -> str:
        """
        Obtiene la descripción correcta del flete según el destino
        """
        usar_libras = price_info.get('usar_libras', False)
        
        if usar_libras:
            return 'USA - libras'
        else:
            return 'Internacional - kilos'
    
    def cleanup_old_pdfs(self, days_old: int = 7):
        """
        Limpia PDFs antiguos para ahorrar espacio
        """
        try:
            import time
            current_time = time.time()
            
            for filename in os.listdir(self.output_dir):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(self.output_dir, filename)
                    file_time = os.path.getctime(filepath)
                    
                    # Si el archivo tiene más de X días, eliminarlo
                    if (current_time - file_time) > (days_old * 24 * 3600):
                        os.remove(filepath)
                        logger.info(f"🗑️ PDF antiguo eliminado: {filename}")
                        
        except Exception as e:
            logger.error(f"Error limpiando PDFs antiguos: {str(e)}")