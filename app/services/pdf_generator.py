from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF
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
        Genera un PDF profesional con la cotización corporativa
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
            
            # Crear documento PDF con márgenes optimizados
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=80
            )
            
            # Contenido del PDF
            story = []
            styles = getSampleStyleSheet()
            
            # Colores corporativos BGR Export
            azul_marino = colors.HexColor('#1B365D')  # Azul marino corporativo
            naranja = colors.HexColor('#FF6B35')      # Naranja corporativo
            gris_claro = colors.HexColor('#F5F5F5')   # Gris claro para fondos
            gris_medio = colors.HexColor('#E0E0E0')   # Gris medio para bordes
            
            # Estilos corporativos personalizados
            company_title_style = ParagraphStyle(
                'CompanyTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=5,
                alignment=TA_LEFT,
                textColor=azul_marino,
                fontName='Helvetica-Bold'
            )
            
            slogan_style = ParagraphStyle(
                'Slogan',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=15,
                alignment=TA_LEFT,
                textColor=naranja,
                fontName='Helvetica-Oblique'
            )
            
            quote_title_style = ParagraphStyle(
                'QuoteTitle',
                parent=styles['Heading1'],
                fontSize=22,
                spaceAfter=20,
                spaceBefore=10,
                alignment=TA_CENTER,
                textColor=azul_marino,
                fontName='Helvetica-Bold'
            )
            
            section_title_style = ParagraphStyle(
                'SectionTitle',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=12,
                spaceBefore=15,
                textColor=azul_marino,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=6,
                fontName='Helvetica'
            )
            
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.grey,
                fontName='Helvetica'
            )
            
            # ENCABEZADO CORPORATIVO PROFESIONAL
            logo_path = os.path.join("data", "logoBGR.png")
            
            # Crear encabezado con logo y datos de empresa
            if os.path.exists(logo_path):
                try:
                    # Logo optimizado
                    logo_img = Image(logo_path, width=2.5*inch, height=1.5*inch)
                    
                    # Datos de la empresa
                    company_info = [
                        Paragraph("BGR EXPORT SHRIMP S.A.", company_title_style),
                        Paragraph("Camarón Premium del Ecuador para el Mundo", slogan_style),
                        Paragraph("www.bgrexport.com | info@bgrexport.com", normal_style),
                        Paragraph("Tel: +593 98-805-7425", normal_style)
                    ]
                    
                    # Tabla del encabezado con logo a la izquierda y datos a la derecha
                    header_data = [[logo_img, company_info]]
                    header_table = Table(header_data, colWidths=[3*inch, 4*inch])
                    header_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (0, 0), 'LEFT'),    # Logo a la izquierda
                        ('ALIGN', (1, 0), (1, 0), 'LEFT'),    # Datos a la izquierda
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alineación superior
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ]))
                    
                    story.append(header_table)
                    
                except Exception as logo_error:
                    logger.warning(f"⚠️ Error cargando logo: {logo_error}")
                    # Fallback elegante sin logo
                    story.append(Paragraph("BGR EXPORT SHRIMP S.A.", company_title_style))
                    story.append(Paragraph("Camarón Premium del Ecuador para el Mundo", slogan_style))
                    story.append(Paragraph("www.bgrexport.com | info@bgrexport.com", normal_style))
                    story.append(Spacer(1, 15))
            else:
                logger.warning(f"⚠️ Logo no encontrado en: {logo_path}")
                # Fallback elegante sin logo
                story.append(Paragraph("BGR EXPORT SHRIMP S.A.", company_title_style))
                story.append(Paragraph("Camarón Premium del Ecuador para el Mundo", slogan_style))
                story.append(Paragraph("www.bgrexport.com | info@bgrexport.com", normal_style))
                story.append(Spacer(1, 15))
            
            # Línea separadora elegante
            line_data = [["", ""]]
            line_table = Table(line_data, colWidths=[7*inch])
            line_table.setStyle(TableStyle([
                ('LINEBELOW', (0, 0), (-1, -1), 2, azul_marino),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ]))
            story.append(line_table)
            
            # Título principal de cotización
            story.append(Paragraph("COTIZACIÓN DE CAMARÓN", quote_title_style))
            story.append(Spacer(1, 20))
            
            # DATOS DE LA COTIZACIÓN - Bloque elegante con fondo gris y bordes redondeados
            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # Crear datos de información
            info_data = [
                ["📅 Fecha de Cotización:", fecha_actual],
                ["🦐 Producto:", price_info.get('producto', 'Camarón')],
                ["📏 Talla:", price_info.get('talla', 'N/A')]
            ]
            
            # Agregar cliente si está disponible
            if price_info.get('cliente_nombre'):
                info_data.append(["👤 Cliente:", price_info['cliente_nombre'].title()])
            
            if price_info.get('destination'):
                info_data.append(["🌍 Destino:", price_info['destination']])
            
            if price_info.get('quantity'):
                info_data.append(["📦 Cantidad:", f"{price_info['quantity']} {price_info.get('unit', 'lb')}"])
            
            # Agregar glaseo si fue especificado por el usuario
            if price_info.get('calculo_dinamico') and price_info.get('factor_glaseo'):
                glaseo_percent = price_info['factor_glaseo'] * 100
                if glaseo_percent != 70:  # Solo mostrar si es diferente al estándar
                    info_data.append(["❄️ Glaseo solicitado:", f"{glaseo_percent:.0f}%"])
            
            # Tabla de información con diseño elegante
            info_table = Table(info_data, colWidths=[2.8*inch, 3.5*inch])
            info_table.setStyle(TableStyle([
                # Fondo gris claro para toda la tabla
                ('BACKGROUND', (0, 0), (-1, -1), gris_claro),
                # Fondo más oscuro para las etiquetas
                ('BACKGROUND', (0, 0), (0, -1), gris_medio),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),    # Etiquetas alineadas a la izquierda
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),    # Valores alineados a la izquierda
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                # Bordes suaves
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 25))     
       
            # SECCIÓN PRINCIPAL: COTIZACIÓN FOB - Precio destacado
            story.append(Paragraph("💰 COTIZACIÓN FOB", section_title_style))
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
            
            # Tabla principal de precios con diseño corporativo destacado
            if is_houston:
                main_price_data = [
                    ["PRECIO FOB", "POR KILOGRAMO"],
                    [f"${precio_kg:.2f}", "USD/KG"]
                ]
                main_price_table = Table(main_price_data, colWidths=[4*inch, 2.5*inch])
                main_price_table.setStyle(TableStyle([
                    # Encabezado con colores corporativos
                    ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    
                    # Fila de precios destacada
                    ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#FFF8DC')),  # Fondo crema para precio
                    ('BACKGROUND', (1, 1), (1, 1), gris_claro),  # Fondo gris para unidad
                    ('TEXTCOLOR', (0, 1), (-1, 1), azul_marino),
                    ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 1), (1, 1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (0, 1), 28),  # Precio muy grande y destacado
                    ('FONTSIZE', (1, 1), (1, 1), 14),
                    ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                    
                    # Bordes elegantes
                    ('GRID', (0, 0), (-1, -1), 2, azul_marino),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 15),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
            else:
                main_price_data = [
                    ["PRECIO FOB", "POR KILOGRAMO", "POR LIBRA"],
                    [f"${precio_kg:.2f}", f"${precio_lb:.2f}", "USD"]
                ]
                main_price_table = Table(main_price_data, colWidths=[2.5*inch, 2.2*inch, 1.8*inch])
                main_price_table.setStyle(TableStyle([
                    # Encabezado con colores corporativos
                    ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    
                    # Fila de precios destacada
                    ('BACKGROUND', (0, 1), (1, 1), colors.HexColor('#FFF8DC')),  # Fondo crema para precios
                    ('BACKGROUND', (2, 1), (2, 1), gris_claro),  # Fondo gris para moneda
                    ('TEXTCOLOR', (0, 1), (-1, 1), azul_marino),
                    ('FONTNAME', (0, 1), (1, 1), 'Helvetica-Bold'),
                    ('FONTNAME', (2, 1), (2, 1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (1, 1), 22),  # Precios grandes y destacados
                    ('FONTSIZE', (2, 1), (2, 1), 12),
                    ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                    
                    # Bordes elegantes
                    ('GRID', (0, 0), (-1, -1), 2, azul_marino),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 15),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
            
            story.append(main_price_table)
            story.append(Spacer(1, 25))
            
            # ESPECIFICACIONES - Tabla profesional con colores corporativos
            story.append(Paragraph("📋 ESPECIFICACIONES", section_title_style))
            story.append(Spacer(1, 12))
            
            # Preparar datos de especificaciones
            specs_data = [
                ["Concepto", "Detalle"],
                ["❄️ Glaseo aplicado", f"{glaseo_factor:.1%}"],
            ]
            
            # Agregar flete si está incluido
            if price_info.get('calculo_dinamico') and flete > 0:
                specs_data.append(["🚢 Flete incluido", f"${flete:.2f}/kg"])
            
            # Agregar observaciones adicionales si aplica
            if price_info.get('destination'):
                if is_houston:
                    specs_data.append(["📍 Destino especial", "Houston - Precios en kilos"])
                else:
                    specs_data.append(["🌍 Destino", price_info['destination']])
            
            # Agregar tipo de producto
            if price_info.get('producto') and price_info.get('talla'):
                specs_data.append(["🦐 Especificación", f"{price_info['producto']} - Talla {price_info['talla']}"])
            
            # Tabla de especificaciones con estilo corporativo
            specs_table = Table(specs_data, colWidths=[3.5*inch, 3*inch])
            specs_table.setStyle(TableStyle([
                # Encabezado con colores corporativos
                ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),    # Concepto alineado a la izquierda
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Detalle centrado
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                
                # Filas de datos alternadas
                ('BACKGROUND', (0, 1), (-1, 1), colors.white),
                ('BACKGROUND', (0, 2), (-1, 2), gris_claro),
                ('BACKGROUND', (0, 3), (-1, 3), colors.white),
                ('BACKGROUND', (0, 4), (-1, 4), gris_claro),
                ('BACKGROUND', (0, 5), (-1, 5), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Conceptos alineados a la izquierda
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Detalles centrados
                
                # Bordes suaves y espaciado
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            
            story.append(specs_table)
            story.append(Spacer(1, 25))       
     
            # CUADRO CON PRECIO TOTAL CALCULADO (si hay cantidad)
            if price_info.get('quantity'):
                story.append(Paragraph("📊 TOTAL ESTIMADO", section_title_style))
                story.append(Spacer(1, 12))
                
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
                    
                    # Tabla destacada de total con colores corporativos
                    total_data = [
                        ["CANTIDAD", "PRECIO UNITARIO", "TOTAL FOB"],
                        [f"{price_info['quantity']} {unit}", f"${unit_price:.2f}", f"${total:,.2f}"]
                    ]
                    
                    total_table = Table(total_data, colWidths=[2.2*inch, 2.2*inch, 2.2*inch])
                    total_table.setStyle(TableStyle([
                        # Encabezado con colores corporativos
                        ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 11),
                        
                        # Fila de totales destacada con naranja corporativo
                        ('BACKGROUND', (0, 1), (1, 1), colors.HexColor('#FFF8DC')),  # Fondo crema para cantidad y precio
                        ('BACKGROUND', (2, 1), (2, 1), naranja),  # Fondo naranja para total
                        ('TEXTCOLOR', (0, 1), (1, 1), colors.black),
                        ('TEXTCOLOR', (2, 1), (2, 1), colors.white),
                        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 1), (1, 1), 14),
                        ('FONTSIZE', (2, 1), (2, 1), 18),  # Total más grande
                        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                        
                        # Bordes elegantes
                        ('GRID', (0, 0), (-1, -1), 2, azul_marino),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    
                    story.append(total_table)
                    story.append(Spacer(1, 30))
                    
                except:
                    pass
            
            # PIE DE PÁGINA CORPORATIVO
            story.append(Spacer(1, 40))
            
            # Línea separadora antes del pie
            line_data = [["", ""]]
            line_table = Table(line_data, colWidths=[7*inch])
            line_table.setStyle(TableStyle([
                ('LINEABOVE', (0, 0), (-1, -1), 1, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(line_table)
            
            # Disclaimer en letra pequeña
            disclaimer_style = ParagraphStyle(
                'Disclaimer',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.grey,
                fontName='Helvetica-Oblique',
                spaceAfter=8
            )
            
            contact_style = ParagraphStyle(
                'Contact',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER,
                textColor=azul_marino,
                fontName='Helvetica',
                spaceAfter=3
            )
            
            story.append(Paragraph("Precios FOB sujetos a confirmación final. BGR Export Shrimp – Garantía de calidad y frescura.", disclaimer_style))
            story.append(Spacer(1, 8))
            
            # Datos de contacto en el pie
            story.append(Paragraph("📞 Tel: +593 4 123-4567 | 📧 info@bgrexport.com | 🌐 www.bgrexport.com", contact_style))
            story.append(Paragraph("BGR EXPORT SHRIMP S.A. - Camarón Premium del Ecuador", contact_style))
            
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