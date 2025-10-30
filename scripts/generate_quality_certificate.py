"""
Generador de certificado de calidad en formato PDF
Consolida resultados de validación y tests
"""
import sys
import os
import json
from datetime import datetime
from typing import Dict, List

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class QualityCertificateGenerator:
    """Genera certificado de calidad en PDF"""
    
    def __init__(self):
        self.styles = None
        if REPORTLAB_AVAILABLE:
            self.styles = getSampleStyleSheet()
            self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configura estilos personalizados"""
        # Título principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtítulo
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Texto normal
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
    
    def load_validation_report(self, filename: str = 'validation_report.json') -> Dict:
        """Carga el reporte de validación"""
        if not os.path.exists(filename):
            return None
        
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_certificate(self, 
                           validation_report: Dict = None,
                           critical_points: List[Dict] = None,
                           output_filename: str = 'quality_certificate.pdf') -> str:
        """Genera el certificado de calidad en PDF"""
        
        if not REPORTLAB_AVAILABLE:
            print("❌ ReportLab no está instalado. Instalando...")
            print("   Ejecuta: pip install reportlab")
            return None
        
        # Cargar reporte de validación si no se proporciona
        if validation_report is None:
            validation_report = self.load_validation_report()
        
        # Crear documento PDF
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Contenido del documento
        story = []
        
        # Encabezado
        story.append(Paragraph("CERTIFICADO DE CALIDAD", self.styles['CustomTitle']))
        story.append(Paragraph("BGR Shrimp Bot - Sistema de Cotización WhatsApp", 
                              self.styles['CustomSubtitle']))
        story.append(Spacer(1, 0.3*inch))
        
        # Información general
        now = datetime.now()
        story.append(Paragraph(f"<b>Fecha de certificación:</b> {now.strftime('%d/%m/%Y %H:%M:%S')}", 
                              self.styles['CustomBody']))
        story.append(Paragraph(f"<b>Versión del sistema:</b> 1.0.0", 
                              self.styles['CustomBody']))
        story.append(Spacer(1, 0.3*inch))
        
        # Resumen ejecutivo
        story.append(Paragraph("RESUMEN EJECUTIVO", self.styles['CustomSubtitle']))
        
        if validation_report:
            summary = validation_report.get('summary', {})
            
            # Tabla de resumen
            summary_data = [
                ['Métrica', 'Valor'],
                ['Total de tests ejecutados', str(summary.get('total_tests', 0))],
                ['Tests pasados', f"✅ {summary.get('passed', 0)}"],
                ['Tests fallados', f"❌ {summary.get('failed', 0)}"],
                ['Tasa de éxito', f"{summary.get('success_rate', 0):.1f}%"],
                ['Duración total', f"{summary.get('total_duration', 0):.2f}s"]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Puntos críticos
        if critical_points:
            story.append(Paragraph("VALIDACIÓN DE PUNTOS CRÍTICOS", self.styles['CustomSubtitle']))
            
            critical_data = [['Punto Crítico', 'Estado', 'Duración']]
            
            for cp in critical_points:
                status = "✅ PASÓ" if cp['passed'] else "❌ FALLÓ"
                critical_data.append([
                    cp['name'],
                    status,
                    f"{cp['duration']:.3f}s"
                ])
            
            critical_table = Table(critical_data, colWidths=[3.5*inch, 1*inch, 1*inch])
            critical_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(critical_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Detalle de tests
        if validation_report:
            story.append(PageBreak())
            story.append(Paragraph("DETALLE DE TESTS EJECUTADOS", self.styles['CustomSubtitle']))
            
            results = validation_report.get('results', [])
            
            for result in results:
                test_name = result['test_file']
                status = "✅ PASÓ" if result['passed'] else "❌ FALLÓ"
                duration = result['duration']
                
                story.append(Paragraph(f"<b>{test_name}</b> - {status} ({duration:.2f}s)", 
                                      self.styles['CustomBody']))
                
                if not result['passed'] and result.get('stderr'):
                    error_text = result['stderr'][:200]
                    story.append(Paragraph(f"<i>Error: {error_text}</i>", 
                                          self.styles['CustomBody']))
                
                story.append(Spacer(1, 0.1*inch))
        
        # Conclusión
        story.append(PageBreak())
        story.append(Paragraph("CONCLUSIÓN", self.styles['CustomSubtitle']))
        
        if validation_report:
            summary = validation_report.get('summary', {})
            success_rate = summary.get('success_rate', 0)
            
            if success_rate == 100:
                conclusion = """
                El sistema BGR Shrimp Bot ha pasado exitosamente todas las pruebas de validación 
                y cumple con todos los requisitos de calidad establecidos. El sistema está 
                CERTIFICADO para despliegue en producción.
                """
            elif success_rate >= 90:
                conclusion = """
                El sistema BGR Shrimp Bot ha pasado la mayoría de las pruebas de validación. 
                Se recomienda revisar y corregir los tests fallados antes del despliegue en producción.
                """
            else:
                conclusion = """
                El sistema BGR Shrimp Bot requiere correcciones adicionales antes de ser 
                certificado para producción. Se deben resolver los tests fallados.
                """
            
            story.append(Paragraph(conclusion, self.styles['CustomBody']))
        
        # Firma
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("_" * 50, self.styles['CustomBody']))
        story.append(Paragraph("Firma del Responsable de QA", self.styles['CustomBody']))
        story.append(Paragraph(f"Fecha: {now.strftime('%d/%m/%Y')}", self.styles['CustomBody']))
        
        # Generar PDF
        doc.build(story)
        
        return output_filename
    
    def generate_text_certificate(self,
                                 validation_report: Dict = None,
                                 critical_points: List[Dict] = None,
                                 output_filename: str = 'quality_certificate.txt') -> str:
        """Genera certificado en formato texto plano (fallback)"""
        
        # Cargar reporte de validación si no se proporciona
        if validation_report is None:
            validation_report = self.load_validation_report()
        
        now = datetime.now()
        
        lines = []
        lines.append("=" * 80)
        lines.append("CERTIFICADO DE CALIDAD".center(80))
        lines.append("BGR Shrimp Bot - Sistema de Cotización WhatsApp".center(80))
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Fecha de certificación: {now.strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(f"Versión del sistema: 1.0.0")
        lines.append("")
        
        # Resumen ejecutivo
        lines.append("=" * 80)
        lines.append("RESUMEN EJECUTIVO")
        lines.append("=" * 80)
        
        if validation_report:
            summary = validation_report.get('summary', {})
            lines.append(f"Total de tests ejecutados: {summary.get('total_tests', 0)}")
            lines.append(f"Tests pasados: ✅ {summary.get('passed', 0)}")
            lines.append(f"Tests fallados: ❌ {summary.get('failed', 0)}")
            lines.append(f"Tasa de éxito: {summary.get('success_rate', 0):.1f}%")
            lines.append(f"Duración total: {summary.get('total_duration', 0):.2f}s")
        
        lines.append("")
        
        # Puntos críticos
        if critical_points:
            lines.append("=" * 80)
            lines.append("VALIDACIÓN DE PUNTOS CRÍTICOS")
            lines.append("=" * 80)
            
            for cp in critical_points:
                status = "✅ PASÓ" if cp['passed'] else "❌ FALLÓ"
                lines.append(f"{status} - {cp['name']} ({cp['duration']:.3f}s)")
                lines.append(f"   {cp['details']}")
            
            lines.append("")
        
        # Detalle de tests
        if validation_report:
            lines.append("=" * 80)
            lines.append("DETALLE DE TESTS EJECUTADOS")
            lines.append("=" * 80)
            
            results = validation_report.get('results', [])
            
            for result in results:
                status = "✅ PASÓ" if result['passed'] else "❌ FALLÓ"
                lines.append(f"{status} - {result['test_file']} ({result['duration']:.2f}s)")
                
                if not result['passed'] and result.get('stderr'):
                    error_text = result['stderr'][:200]
                    lines.append(f"   Error: {error_text}")
            
            lines.append("")
        
        # Conclusión
        lines.append("=" * 80)
        lines.append("CONCLUSIÓN")
        lines.append("=" * 80)
        
        if validation_report:
            summary = validation_report.get('summary', {})
            success_rate = summary.get('success_rate', 0)
            
            if success_rate == 100:
                lines.append("El sistema BGR Shrimp Bot ha pasado exitosamente todas las pruebas")
                lines.append("de validación y cumple con todos los requisitos de calidad establecidos.")
                lines.append("El sistema está CERTIFICADO para despliegue en producción.")
            elif success_rate >= 90:
                lines.append("El sistema BGR Shrimp Bot ha pasado la mayoría de las pruebas de validación.")
                lines.append("Se recomienda revisar y corregir los tests fallados antes del despliegue.")
            else:
                lines.append("El sistema BGR Shrimp Bot requiere correcciones adicionales antes de ser")
                lines.append("certificado para producción. Se deben resolver los tests fallados.")
        
        lines.append("")
        lines.append("_" * 80)
        lines.append("Firma del Responsable de QA")
        lines.append(f"Fecha: {now.strftime('%d/%m/%Y')}")
        lines.append("")
        
        # Guardar archivo
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_filename


def main():
    """Función principal"""
    print("\n" + "="*80)
    print("📜 GENERADOR DE CERTIFICADO DE CALIDAD")
    print("="*80 + "\n")
    
    generator = QualityCertificateGenerator()
    
    # Cargar reporte de validación
    validation_report = generator.load_validation_report()
    
    if not validation_report:
        print("⚠️  No se encontró validation_report.json")
        print("   Ejecuta primero: python scripts/run_validation.py")
        return 1
    
    # Cargar puntos críticos si existen
    critical_points = None
    if os.path.exists('critical_points_report.json'):
        with open('critical_points_report.json', 'r', encoding='utf-8') as f:
            critical_data = json.load(f)
            critical_points = critical_data.get('results', [])
    
    # Generar certificado en PDF
    if REPORTLAB_AVAILABLE:
        pdf_path = generator.generate_certificate(
            validation_report=validation_report,
            critical_points=critical_points
        )
        
        if pdf_path:
            print(f"✅ Certificado PDF generado: {pdf_path}")
            
            # Verificar tamaño
            if os.path.exists(pdf_path):
                size = os.path.getsize(pdf_path)
                print(f"   📊 Tamaño: {size:,} bytes")
    else:
        print("⚠️  ReportLab no disponible, generando certificado en texto plano...")
    
    # Generar certificado en texto plano (siempre)
    txt_path = generator.generate_text_certificate(
        validation_report=validation_report,
        critical_points=critical_points
    )
    
    print(f"✅ Certificado TXT generado: {txt_path}")
    
    if os.path.exists(txt_path):
        size = os.path.getsize(txt_path)
        print(f"   📊 Tamaño: {size:,} bytes")
    
    print("\n" + "="*80)
    print("✅ Certificados generados exitosamente!")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
