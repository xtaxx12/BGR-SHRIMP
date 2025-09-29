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
            if user_phone:
                cleaned_phone = user_phone.replace("+", "").replace(":", "")
                phone_suffix = cleaned_phone[-4:] if len(cleaned_phone) >= 4 else cleaned_phone.zfill(4)
            else:
                phone_suffix = "0000"
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
            
            # Colores corporativos BGR Export - Actualizados según especificaciones
            azul_marino = colors.HexColor('#0a2e5d')  # Azul marino corporativo
            naranja = colors.HexColor('#f36f21')      # Naranja corporativo
            gris_claro = colors.HexColor('#F8F9FA')   # Gris claro para fondos
            gris_medio = colors.HexColor('#DEE2E6')   # Gris medio para bordes
            blanco = colors.white                     # Blanco
            
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
            
            # ENCABEZADO CORPORATIVO CON FONDO AZUL MARINO
            logo_path = os.path.join("data", "logoBGR.png")
            
            # Crear encabezado con fondo azul marino
            if os.path.exists(logo_path):
                try:
                    # Logo optimizado
                    logo_img = Image(logo_path, width=2.2*inch, height=1.3*inch)
                    
                    # Estilos para texto blanco en fondo azul
                    header_company_style = ParagraphStyle(
                        'HeaderCompany',
                        parent=styles['Heading1'],
                        fontSize=20,
                        spaceAfter=3,
                        alignment=TA_RIGHT,
                        textColor=blanco,
                        fontName='Helvetica-Bold'
                    )
                    
                    header_slogan_style = ParagraphStyle(
                        'HeaderSlogan',
                        parent=styles['Normal'],
                        fontSize=11,
                        spaceAfter=8,
                        alignment=TA_RIGHT,
                        textColor=blanco,
                        fontName='Helvetica-Oblique'
                    )
                    
                    header_contact_style = ParagraphStyle(
                        'HeaderContact',
                        parent=styles['Normal'],
                        fontSize=10,
                        spaceAfter=2,
                        alignment=TA_RIGHT,
                        textColor=blanco,
                        fontName='Helvetica'
                    )
                    
                    # Datos de la empresa con texto blanco (sin emojis)
                    company_info_text = """BGR EXPORT SHRIMP S.A.<br/>
                    Camarón Premium del Ecuador para el Mundo<br/>
                    Web: www.bgrexport.com<br/>
                    Email: amerino@bgrexport.com<br/>
                    Tel: +593 4 123-4567"""
                    
                    company_info = Paragraph(company_info_text, header_contact_style)
                    
                    # Crear fondo blanco para el logo para que resalte
                    logo_with_bg = Table([[logo_img]], colWidths=[2.5*inch])
                    logo_with_bg.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), blanco),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                        ('LEFTPADDING', (0, 0), (-1, -1), 10),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ]))
                    
                    # Tabla del encabezado con fondo azul marino
                    header_data = [[logo_with_bg, company_info]]
                    header_table = Table(header_data, colWidths=[3*inch, 4.5*inch])
                    header_table.setStyle(TableStyle([
                        # Fondo azul marino para toda la tabla
                        ('BACKGROUND', (0, 0), (-1, -1), azul_marino),
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),    # Logo centrado
                        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),     # Datos a la derecha
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), # Centrado vertical
                        ('TOPPADDING', (0, 0), (-1, -1), 15),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                        ('LEFTPADDING', (0, 0), (-1, -1), 20),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                        # Sin bordes para un look más limpio
                        ('GRID', (0, 0), (-1, -1), 0, azul_marino),
                    ]))
                    
                    story.append(header_table)
                    
                except Exception as logo_error:
                    logger.warning(f"⚠️ Error cargando logo: {logo_error}")
                    # Fallback con fondo azul marino sin logo
                    fallback_data = [["BGR EXPORT SHRIMP S.A.\nCamarón Premium del Ecuador para el Mundo\nWeb: www.bgrexport.com | Email: amerino@bgrexport.com | Tel: +593 98-805-7425"]]
                    fallback_table = Table(fallback_data, colWidths=[7.5*inch])
                    fallback_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), azul_marino),
                        ('TEXTCOLOR', (0, 0), (-1, -1), blanco),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 14),
                        ('TOPPADDING', (0, 0), (-1, -1), 20),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                    ]))
                    story.append(fallback_table)
            else:
                logger.warning(f"⚠️ Logo no encontrado en: {logo_path}")
                # Fallback con fondo azul marino sin logo
                fallback_data = [["BGR EXPORT SHRIMP S.A.\nCamarón Premium del Ecuador para el Mundo\nWeb: www.bgrexport.com | Email: amerino@bgrexport.com | Tel: +593 98-805-7425"]]
                fallback_table = Table(fallback_data, colWidths=[7.5*inch])
                fallback_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), azul_marino),
                    ('TEXTCOLOR', (0, 0), (-1, -1), blanco),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 14),
                    ('TOPPADDING', (0, 0), (-1, -1), 20),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                ]))
                story.append(fallback_table)
            
            # Espaciado después del encabezado
            story.append(Spacer(1, 25))
            
            # Título principal de cotización
            story.append(Paragraph("COTIZACIÓN DE CAMARÓN", quote_title_style))
            story.append(Spacer(1, 20))
            
            # BLOQUE DE DATOS DE LA COTIZACIÓN - Tabla con fondo gris claro y bordes suaves
            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # Crear datos de información con íconos visuales
            info_data = [
                ["Fecha de Cotización", fecha_actual],
                ["Producto", price_info.get('producto', 'Camarón')],
                ["Talla", price_info.get('talla', 'N/A')]
            ]
            
            # Agregar cliente si está disponible
            if price_info.get('cliente_nombre'):
                info_data.append(["Cliente", price_info['cliente_nombre'].title()])
            
            if price_info.get('destination'):
                info_data.append(["Destino", price_info['destination']])
            
            if price_info.get('quantity'):
                info_data.append(["Cantidad", f"{price_info['quantity']} {price_info.get('unit', 'lb')}"])
            
            # Agregar glaseo si fue especificado por el usuario
            if price_info.get('calculo_dinamico') and price_info.get('factor_glaseo'):
                glaseo_percent = price_info['factor_glaseo'] * 100
                if glaseo_percent != 70:  # Solo mostrar si es diferente al estándar
                    info_data.append(["Glaseo Solicitado", f"{glaseo_percent:.0f}%"])
            
            # Tabla de información con diseño corporativo minimalista
            info_table = Table(info_data, colWidths=[3.2*inch, 3.8*inch])
            info_table.setStyle(TableStyle([
                # Fondo gris claro para toda la tabla
                ('BACKGROUND', (0, 0), (-1, -1), gris_claro),
                # Fondo azul marino para las etiquetas
                ('BACKGROUND', (0, 0), (0, -1), azul_marino),
                ('TEXTCOLOR', (0, 0), (0, -1), blanco),  # Texto blanco en etiquetas
                ('TEXTCOLOR', (1, 0), (1, -1), colors.black),  # Texto negro en valores
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),    # Etiquetas alineadas a la izquierda
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),    # Valores alineados a la izquierda
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                # Bordes suaves y elegantes
                ('GRID', (0, 0), (-1, -1), 0.5, gris_medio),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ]))
            
            info_table.hAlign = 'CENTER'
            story.append(info_table)
            story.append(Spacer(1, 30))     
       
            # SECCIÓN DE COTIZACIÓN FOB - Precio destacado, grande, negrita y centrada
            fob_title_style = ParagraphStyle(
                'FOBTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=15,
                spaceBefore=5,
                alignment=TA_CENTER,
                textColor=azul_marino,
                fontName='Helvetica-Bold'
            )
            
            story.append(Paragraph("COTIZACIÓN FOB", fob_title_style))
            
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
            
            # TABLA PRINCIPAL DE PRECIOS - Diseño minimalista y elegante
            if is_houston:
                # Para Houston: Solo kilogramos
                main_price_data = [
                    ["PRECIO FOB USD/KG"],
                    [f"${precio_kg:.2f}"]
                ]
                main_price_table = Table(main_price_data, colWidths=[5*inch])
                main_price_table.setStyle(TableStyle([
                    # Encabezado elegante
                    ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                    ('TEXTCOLOR', (0, 0), (-1, 0), blanco),
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),  # Encabezado centrado
                    ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (0, 0), 14),
                    
                    # Precio destacado - PERFECTAMENTE CENTRADO
                    ('BACKGROUND', (0, 1), (0, 1), blanco),
                    ('TEXTCOLOR', (0, 1), (0, 1), azul_marino),
                    ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 1), (0, 1), 36),  # Precio MUY GRANDE
                    ('ALIGN', (0, 1), (0, 1), 'CENTER'),  # PRECIO CENTRADO
                    
                    # Bordes minimalistas
                    ('GRID', (0, 0), (-1, -1), 1.5, azul_marino),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    # Padding del encabezado
                    ('TOPPADDING', (0, 0), (0, 0), 20),
                    ('BOTTOMPADDING', (0, 0), (0, 0), 20),
                    # Padding del precio - menos padding arriba para que suba
                    ('TOPPADDING', (0, 1), (0, 1), 10),  # Reducido para subir el precio
                    ('BOTTOMPADDING', (0, 1), (0, 1), 30), # Aumentado para compensar
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
            else:
                # Para otros destinos: Kilogramos y libras
                main_price_data = [
                    ["PRECIO FOB", "USD/KG", "USD/LB"],
                    ["", f"${precio_kg:.2f}", f"${precio_lb:.2f}"]
                ]
                main_price_table = Table(main_price_data, colWidths=[2*inch, 2.5*inch, 2.5*inch])
                main_price_table.setStyle(TableStyle([
                    # Encabezado elegante
                    ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                    ('TEXTCOLOR', (0, 0), (-1, 0), blanco),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    
                    # Precios destacados - GRANDES, NEGRITAS Y CENTRADOS
                    ('BACKGROUND', (0, 1), (-1, 1), blanco),
                    ('TEXTCOLOR', (0, 1), (-1, 1), azul_marino),
                    ('FONTNAME', (1, 1), (2, 1), 'Helvetica-Bold'),
                    ('FONTSIZE', (1, 1), (2, 1), 28),  # Precios GRANDES
                    ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                    
                    # Bordes minimalistas
                    ('GRID', (0, 0), (-1, -1), 1.5, azul_marino),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 18),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
            
            # Centrar la tabla en la página
            main_price_table.hAlign = 'CENTER'
            story.append(main_price_table)
            story.append(Spacer(1, 25))
            
            # ESPECIFICACIONES - Tabla estilizada con colores corporativos e íconos
            specs_title_style = ParagraphStyle(
                'SpecsTitle',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=15,
                spaceBefore=10,
                alignment=TA_CENTER,
                textColor=azul_marino,
                fontName='Helvetica-Bold'
            )
            
            story.append(Paragraph("ESPECIFICACIONES", specs_title_style))
            
            # Preparar datos de especificaciones con íconos visuales
            specs_data = [
                ["Concepto", "Detalle"],
                ["Glaseo Aplicado", f"{glaseo_factor:.1%}"],
            ]
            
            # Agregar flete si está incluido
            if price_info.get('calculo_dinamico') and flete > 0:
                specs_data.append(["Flete Incluido", f"${flete:.2f}/kg"])
            
            # Agregar observaciones adicionales si aplica
            if price_info.get('destination') and not is_houston:
                specs_data.append(["Destino", price_info['destination']])
            
            # Agregar tipo de producto
            if price_info.get('producto') and price_info.get('talla'):
                specs_data.append(["Especificación", f"{price_info['producto']} - Talla {price_info['talla']}"])
            
            # Tabla de especificaciones con diseño corporativo elegante
            specs_table = Table(specs_data, colWidths=[3.5*inch, 3.5*inch])
            specs_table.setStyle(TableStyle([
                # Encabezado con azul marino
                ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                ('TEXTCOLOR', (0, 0), (-1, 0), blanco),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                
                # Filas alternadas elegantes
                ('BACKGROUND', (0, 1), (-1, 1), blanco),
                ('BACKGROUND', (0, 2), (-1, 2), gris_claro),
                ('BACKGROUND', (0, 3), (-1, 3), blanco),
                ('BACKGROUND', (0, 4), (-1, 4), gris_claro),
                ('BACKGROUND', (0, 5), (-1, 5), blanco),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Conceptos alineados a la izquierda
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Detalles centrados
                
                # Bordes minimalistas
                ('GRID', (0, 0), (-1, -1), 0.5, gris_medio),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ]))
            
            specs_table.hAlign = 'CENTER'
            story.append(specs_table)
            story.append(Spacer(1, 30))       
     
            # CUADRO DE PRECIO TOTAL - Cantidad × Precio Unitario
            if price_info.get('quantity') and price_info['quantity'] is not None:
                total_title_style = ParagraphStyle(
                    'TotalTitle',
                    parent=styles['Heading2'],
                    fontSize=16,
                    spaceAfter=15,
                    spaceBefore=10,
                    alignment=TA_CENTER,
                    textColor=azul_marino,
                    fontName='Helvetica-Bold'
                )
                
                story.append(Paragraph("TOTAL ESTIMADO", total_title_style))
                
                try:
                    # Verificar que quantity no sea None y sea convertible a string
                    quantity_str = str(price_info['quantity']) if price_info['quantity'] is not None else "0"
                    qty = float(quantity_str.replace(',', ''))
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
                    
                    # Tabla elegante de total con diseño minimalista
                    total_data = [
                        ["CANTIDAD", "PRECIO UNITARIO", "TOTAL FOB USD"],
                        [f"{quantity_str} {unit.upper()}", f"${unit_price:.2f}", f"${total:,.2f}"]
                    ]
                    
                    total_table = Table(total_data, colWidths=[2.3*inch, 2.3*inch, 2.4*inch])
                    total_table.setStyle(TableStyle([
                        # Encabezado elegante
                        ('BACKGROUND', (0, 0), (-1, 0), azul_marino),
                        ('TEXTCOLOR', (0, 0), (-1, 0), blanco),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 11),
                        
                        # Fila de totales con naranja corporativo destacado
                        ('BACKGROUND', (0, 1), (1, 1), blanco),  # Fondo blanco para cantidad y precio
                        ('BACKGROUND', (2, 1), (2, 1), naranja),  # Fondo naranja para total
                        ('TEXTCOLOR', (0, 1), (1, 1), colors.black),
                        ('TEXTCOLOR', (2, 1), (2, 1), blanco),
                        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 1), (1, 1), 14),
                        ('FONTSIZE', (2, 1), (2, 1), 20),  # Total destacado
                        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                        
                        # Bordes minimalistas
                        ('GRID', (0, 0), (-1, -1), 1.5, azul_marino),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 15),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                        ('LEFTPADDING', (0, 0), (-1, -1), 10),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ]))
                    
                    total_table.hAlign = 'CENTER'
                    story.append(total_table)
                    story.append(Spacer(1, 35))
                    
                except:
                    pass
            
            # PIE DE PÁGINA CORPORATIVO ELEGANTE
            story.append(Spacer(1, 45))
            
            # Línea divisoria elegante
            divider_data = [["", ""]]
            divider_table = Table(divider_data, colWidths=[7*inch])
            divider_table.setStyle(TableStyle([
                ('LINEABOVE', (0, 0), (-1, -1), 2, azul_marino),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(divider_table)
            
            # Disclaimer profesional
            disclaimer_style = ParagraphStyle(
                'Disclaimer',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.grey,
                fontName='Helvetica-Oblique',
                spaceAfter=10
            )
            
            # Contacto corporativo
            contact_style = ParagraphStyle(
                'Contact',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER,
                textColor=azul_marino,
                fontName='Helvetica-Bold',
                spaceAfter=3
            )
            
            company_footer_style = ParagraphStyle(
                'CompanyFooter',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.grey,
                fontName='Helvetica',
                spaceAfter=0
            )
            
            # Disclaimer exacto como solicitaste
            story.append(Paragraph("Precios FOB sujetos a confirmación final. BGR Export Shrimp – Garantía de calidad y frescura.", disclaimer_style))
            
            # Contacto de la empresa alineado al centro
            story.append(Paragraph("Tel: +593 98-805-7425 | Email: amerino@bgrexport.com | Web: www.bgrexport.com", contact_style))
            story.append(Paragraph("BGR EXPORT SHRIMP S.A. - Camarón Premium del Ecuador", company_footer_style))
            
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
