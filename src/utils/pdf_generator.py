from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func, extract, and_
import pytz
import calendar
import io
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.platypus.flowables import HRFlowable
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.colors import HexColor
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np

from ..models.parking import ParkingRecord
from ..models.expense import Expense
from ..models.user import db

# Configuração do fuso horário
fuso_brasilia = pytz.timezone('America/Sao_Paulo')

# Blueprint para geração de relatórios
reports_bp = Blueprint('reports', __name__)

def require_login():
    """Decorator para verificar se o usuário está logado"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return None

@reports_bp.route('/generate/<period>')
def generate_report(period):
    """Gera relatório em PDF para período específico"""
    login_check = require_login()
    if login_check:
        return login_check
    
    current_date = datetime.now(fuso_brasilia)
    year = request.args.get('year', current_date.year, type=int)
    month = request.args.get('month', current_date.month, type=int)
    
    # Importar funções de estatísticas
    from .statistics import get_monthly_statistics, get_yearly_statistics, get_total_statistics
    
    if period == 'monthly':
        data = get_monthly_statistics(year, month)
        title = f"Relatório Mensal - {calendar.month_name[month]} {year}"
        filename = f"relatorio_mensal_{month:02d}_{year}.pdf"
    elif period == 'yearly':
        data = get_yearly_statistics(year)
        title = f"Relatório Anual - {year}"
        filename = f"relatorio_anual_{year}.pdf"
    elif period == 'total':
        data = get_total_statistics()
        title = "Relatório Total - Desde o Início"
        filename = "relatorio_total.pdf"
    else:
        return "Período inválido", 400
    
    # Gerar PDF
    pdf_buffer = generate_pdf_report(data, title, period, year, month if period == 'monthly' else None)
    
    # Retornar PDF como download
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

def generate_pdf_report(data, title, period, year, month=None):
    """Gera o PDF do relatório"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  # Centralizado
        textColor=colors.HexColor('#2c3e50')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#34495e')
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    
    # Elementos do documento
    elements = []
    
    # Cabeçalho
    elements.append(Paragraph("BARUK ESTACIONAMENTO", title_style))
    elements.append(Paragraph(title, heading_style))
    elements.append(Paragraph(f"Gerado em: {datetime.now(fuso_brasilia).strftime('%d/%m/%Y às %H:%M')}", normal_style))
    elements.append(Spacer(1, 20))
    
    # Linha separadora
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.HexColor('#bdc3c7')))
    elements.append(Spacer(1, 20))
    
    # Resumo Executivo
    elements.append(Paragraph("RESUMO EXECUTIVO", heading_style))
    
    summary_data = [
        ['Métrica', 'Valor'],
        ['Receita Total', f"R$ {data['total_revenue']:.2f}"],
        ['Gastos Totais', f"R$ {data['total_expenses']:.2f}"],
        ['Lucro Líquido', f"R$ {data['net_profit']:.2f}"],
        ['Total de Veículos', str(data['total_vehicles'])],
        ['Carros', str(data['cars_count'])],
        ['Motos', str(data['motorcycles_count'])],
        ['Diárias', str(data['daily_count'])],
        ['Por Hora', str(data['hourly_count'])]
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Gráfico de receita (se for relatório mensal ou anual)
    if period in ['monthly', 'yearly']:
        chart_image = generate_chart_for_pdf(data, period)
        if chart_image:
            elements.append(Paragraph("ANÁLISE GRÁFICA", heading_style))
            elements.append(chart_image)
            elements.append(Spacer(1, 20))
    
    # Detalhamento por período
    if period == 'monthly' and 'monthly_data' in data:
        elements.append(Paragraph("DETALHAMENTO MENSAL", heading_style))
        
        monthly_data = [['Mês', 'Receita', 'Gastos', 'Lucro', 'Veículos']]
        for month_info in data['monthly_data']:
            monthly_data.append([
                month_info['month_name'],
                f"R$ {month_info['revenue']:.2f}",
                f"R$ {month_info['expenses']:.2f}",
                f"R$ {month_info['profit']:.2f}",
                str(month_info['vehicles'])
            ])
        
        monthly_table = Table(monthly_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1*inch])
        monthly_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#d5f4e6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
        ]))
        
        elements.append(monthly_table)
        elements.append(Spacer(1, 20))
    
    # Análise de Performance
    elements.append(Paragraph("ANÁLISE DE PERFORMANCE", heading_style))
    
    # Calcular métricas de performance
    if data['total_vehicles'] > 0:
        avg_ticket = data['total_revenue'] / data['total_vehicles']
        profit_margin = (data['net_profit'] / data['total_revenue'] * 100) if data['total_revenue'] > 0 else 0
    else:
        avg_ticket = 0
        profit_margin = 0
    
    performance_text = f"""
    <b>Ticket Médio:</b> R$ {avg_ticket:.2f}<br/>
    <b>Margem de Lucro:</b> {profit_margin:.1f}%<br/>
    <b>Proporção Carros/Motos:</b> {data['cars_count']}/{data['motorcycles_count']}<br/>
    <b>Proporção Diárias/Horárias:</b> {data['daily_count']}/{data['hourly_count']}
    """
    
    elements.append(Paragraph(performance_text, normal_style))
    elements.append(Spacer(1, 20))
    
    # Observações
    elements.append(Paragraph("OBSERVAÇÕES", heading_style))
    
    observations = []
    
    if data['total_expenses'] == 0:
        observations.append("• Sistema preparado para registrar gastos futuros.")
    
    if profit_margin > 80:
        observations.append("• Excelente margem de lucro.")
    elif profit_margin > 60:
        observations.append("• Boa margem de lucro.")
    elif profit_margin > 40:
        observations.append("• Margem de lucro adequada.")
    else:
        observations.append("• Margem de lucro pode ser melhorada.")
    
    if data['cars_count'] > data['motorcycles_count'] * 2:
        observations.append("• Predominância de carros no estacionamento.")
    elif data['motorcycles_count'] > data['cars_count']:
        observations.append("• Predominância de motos no estacionamento.")
    
    if data['daily_count'] > data['hourly_count']:
        observations.append("• Maior utilização de diárias.")
    else:
        observations.append("• Maior utilização de cobrança por hora.")
    
    for obs in observations:
        elements.append(Paragraph(obs, normal_style))
    
    elements.append(Spacer(1, 30))
    
    # Rodapé
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.HexColor('#bdc3c7')))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Relatório gerado automaticamente pelo Sistema de Estacionamento Baruk", 
                             ParagraphStyle('Footer', parent=normal_style, fontSize=8, alignment=1, textColor=colors.grey)))
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer

def generate_chart_for_pdf(data, period):
    """Gera gráfico para incluir no PDF"""
    try:
        # Configurar matplotlib para não usar GUI
        plt.switch_backend('Agg')
        
        fig, ax = plt.subplots(figsize=(8, 4))
        
        if period == 'yearly' and 'monthly_data' in data:
            # Gráfico mensal para relatório anual
            months = [m['month_name'][:3] for m in data['monthly_data']]
            revenues = [m['revenue'] for m in data['monthly_data']]
            profits = [m['profit'] for m in data['monthly_data']]
            
            x = np.arange(len(months))
            width = 0.35
            
            ax.bar(x - width/2, revenues, width, label='Receita', color='#3498db', alpha=0.8)
            ax.bar(x + width/2, profits, width, label='Lucro', color='#27ae60', alpha=0.8)
            
            ax.set_xlabel('Meses')
            ax.set_ylabel('Valor (R$)')
            ax.set_title(f'Receita e Lucro por Mês - {data["period"]}')
            ax.set_xticks(x)
            ax.set_xticklabels(months)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        elif period == 'monthly':
            # Gráfico simples para relatório mensal
            categories = ['Receita', 'Gastos', 'Lucro']
            values = [data['total_revenue'], data['total_expenses'], data['net_profit']]
            colors_list = ['#3498db', '#e74c3c', '#27ae60']
            
            bars = ax.bar(categories, values, color=colors_list, alpha=0.8)
            ax.set_ylabel('Valor (R$)')
            ax.set_title(f'Resumo Financeiro - {data["period"]}')
            ax.grid(True, alpha=0.3)
            
            # Adicionar valores nas barras
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.01,
                       f'R$ {value:.0f}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Salvar em buffer
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        # Criar objeto Image para ReportLab
        img = Image(img_buffer, width=6*inch, height=3*inch)
        return img
        
    except Exception as e:
        print(f"Erro ao gerar gráfico: {e}")
        return None

# Adicionar rota ao blueprint de estatísticas
def add_pdf_routes(statistics_bp):
    """Adiciona rotas de PDF ao blueprint de estatísticas"""
    
    @statistics_bp.route('/pdf/<period>')
    def generate_pdf(period):
        """Gera PDF do relatório"""
        return generate_report(period)
    
    return statistics_bp

