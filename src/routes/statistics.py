from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func, extract, and_
import pytz
import calendar
import io

from ..models.parking import ParkingRecord
from ..models.expense import Expense
from ..models.user import db
from ..utils.pdf_generator import generate_report

# Configuração do fuso horário
fuso_brasilia = pytz.timezone('America/Sao_Paulo')

# Criação do blueprint
statistics_bp = Blueprint('statistics', __name__)

def require_login():
    """Decorator para verificar se o usuário está logado"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return None

@statistics_bp.route('/')
def dashboard():
    """Página principal de estatísticas"""
    login_check = require_login()
    if login_check:
        return login_check
    
    # Dados básicos para o dashboard
    current_date = datetime.now(fuso_brasilia)
    
    # Estatísticas do mês atual
    monthly_stats = get_monthly_statistics(current_date.year, current_date.month)
    
    # Estatísticas do ano atual
    yearly_stats = get_yearly_statistics(current_date.year)
    
    # Estatísticas desde o início
    total_stats = get_total_statistics()
    
    return render_template('statistics/dashboard.html', 
                         monthly_stats=monthly_stats,
                         yearly_stats=yearly_stats,
                         total_stats=total_stats,
                         current_date=current_date)

@statistics_bp.route('/charts')
def charts():
    """Página de gráficos avançados"""
    login_check = require_login()
    if login_check:
        return login_check
    
    return render_template('statistics/charts.html')

@statistics_bp.route('/extract/<period>')
def extract(period):
    """Gera extrato para período específico (monthly, yearly, total)"""
    login_check = require_login()
    if login_check:
        return login_check
    
    current_date = datetime.now(fuso_brasilia)
    year = request.args.get('year', current_date.year, type=int)
    month = request.args.get('month', current_date.month, type=int)
    
    if period == 'monthly':
        data = get_monthly_extract(year, month)
        title = f"Extrato Mensal - {calendar.month_name[month]} {year}"
    elif period == 'yearly':
        data = get_yearly_extract(year)
        title = f"Extrato Anual - {year}"
    elif period == 'total':
        data = get_total_extract()
        title = "Extrato Total - Desde o Início"
    else:
        return "Período inválido", 400
    
    return render_template('statistics/extract.html', 
                         data=data, 
                         title=title, 
                         period=period,
                         year=year,
                         month=month,
                         calendar=calendar)

@statistics_bp.route('/pdf/<period>')
def generate_pdf_report(period):
    """Gera relatório em PDF"""
    login_check = require_login()
    if login_check:
        return login_check
    
    return generate_report(period)

@statistics_bp.route('/api/monthly-comparison')
def monthly_comparison_api():
    """API para dados de comparação mensal"""
    login_check = require_login()
    if login_check:
        return jsonify({'error': 'Não autorizado'}), 401
    
    current_date = datetime.now(fuso_brasilia)
    year = request.args.get('year', current_date.year, type=int)
    months_back = request.args.get('months', 12, type=int)
    
    data = get_monthly_comparison_data(year, months_back)
    return jsonify(data)

@statistics_bp.route('/api/yearly-comparison')
def yearly_comparison_api():
    """API para dados de comparação anual"""
    login_check = require_login()
    if login_check:
        return jsonify({'error': 'Não autorizado'}), 401
    
    current_year = datetime.now(fuso_brasilia).year
    years_back = request.args.get('years', 5, type=int)
    
    data = get_yearly_comparison_data(current_year, years_back)
    return jsonify(data)

# Funções auxiliares para cálculos de estatísticas

def get_monthly_statistics(year, month):
    """Calcula estatísticas para um mês específico"""
    start_date = datetime(year, month, 1, tzinfo=fuso_brasilia)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=fuso_brasilia)
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=fuso_brasilia)
    
    # Consulta registros do mês
    records = ParkingRecord.query.filter(
        and_(
            ParkingRecord.exit_time.isnot(None),
            ParkingRecord.exit_time >= start_date,
            ParkingRecord.exit_time < end_date
        )
    ).all()
    
    # Cálculos
    total_revenue = sum(record.total_value or 0 for record in records)
    total_vehicles = len(records)
    cars_count = len([r for r in records if r.vehicle_type == 'carro'])
    motorcycles_count = len([r for r in records if r.vehicle_type == 'moto'])
    daily_count = len([r for r in records if r.is_daily])
    hourly_count = total_vehicles - daily_count
    
    # Gastos (se implementados no futuro)
    expenses = Expense.query.filter(
        and_(
            Expense.expense_date >= start_date,
            Expense.expense_date < end_date
        )
    ).all()
    
    total_expenses = sum(expense.amount for expense in expenses)
    net_profit = total_revenue - total_expenses
    
    return {
        'period': f"{calendar.month_name[month]} {year}",
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'total_vehicles': total_vehicles,
        'cars_count': cars_count,
        'motorcycles_count': motorcycles_count,
        'daily_count': daily_count,
        'hourly_count': hourly_count,
        'records': records,
        'expenses': expenses
    }

def get_yearly_statistics(year):
    """Calcula estatísticas para um ano específico"""
    start_date = datetime(year, 1, 1, tzinfo=fuso_brasilia)
    end_date = datetime(year + 1, 1, 1, tzinfo=fuso_brasilia)
    
    # Consulta registros do ano
    records = ParkingRecord.query.filter(
        and_(
            ParkingRecord.exit_time.isnot(None),
            ParkingRecord.exit_time >= start_date,
            ParkingRecord.exit_time < end_date
        )
    ).all()
    
    # Cálculos
    total_revenue = sum(record.total_value or 0 for record in records)
    total_vehicles = len(records)
    cars_count = len([r for r in records if r.vehicle_type == 'carro'])
    motorcycles_count = len([r for r in records if r.vehicle_type == 'moto'])
    daily_count = len([r for r in records if r.is_daily])
    hourly_count = total_vehicles - daily_count
    
    # Gastos (se implementados no futuro)
    expenses = Expense.query.filter(
        and_(
            Expense.expense_date >= start_date,
            Expense.expense_date < end_date
        )
    ).all()
    
    total_expenses = sum(expense.amount for expense in expenses)
    net_profit = total_revenue - total_expenses
    
    # Estatísticas mensais do ano
    monthly_data = []
    for month in range(1, 13):
        month_stats = get_monthly_statistics(year, month)
        monthly_data.append({
            'month': month,
            'month_name': calendar.month_name[month],
            'revenue': month_stats['total_revenue'],
            'expenses': month_stats['total_expenses'],
            'profit': month_stats['net_profit'],
            'vehicles': month_stats['total_vehicles']
        })
    
    return {
        'period': str(year),
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'total_vehicles': total_vehicles,
        'cars_count': cars_count,
        'motorcycles_count': motorcycles_count,
        'daily_count': daily_count,
        'hourly_count': hourly_count,
        'monthly_data': monthly_data,
        'records': records,
        'expenses': expenses
    }

def get_total_statistics():
    """Calcula estatísticas desde o início"""
    # Consulta todos os registros finalizados
    records = ParkingRecord.query.filter(
        ParkingRecord.exit_time.isnot(None)
    ).all()
    
    # Cálculos
    total_revenue = sum(record.total_value or 0 for record in records)
    total_vehicles = len(records)
    cars_count = len([r for r in records if r.vehicle_type == 'carro'])
    motorcycles_count = len([r for r in records if r.vehicle_type == 'moto'])
    daily_count = len([r for r in records if r.is_daily])
    hourly_count = total_vehicles - daily_count
    
    # Gastos totais (se implementados no futuro)
    expenses = Expense.query.all()
    total_expenses = sum(expense.amount for expense in expenses)
    net_profit = total_revenue - total_expenses
    
    # Primeiro e último registro
    first_record = None
    last_record = None
    if records:
        first_record = min(records, key=lambda r: r.entry_time)
        last_record = max(records, key=lambda r: r.exit_time)
    
    return {
        'period': 'Desde o Início',
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'total_vehicles': total_vehicles,
        'cars_count': cars_count,
        'motorcycles_count': motorcycles_count,
        'daily_count': daily_count,
        'hourly_count': hourly_count,
        'first_record': first_record,
        'last_record': last_record,
        'records': records,
        'expenses': expenses
    }

def get_monthly_extract(year, month):
    """Gera dados detalhados para extrato mensal"""
    stats = get_monthly_statistics(year, month)
    
    # Agrupa registros por dia
    daily_data = {}
    for record in stats['records']:
        day = record.exit_time.day
        if day not in daily_data:
            daily_data[day] = {
                'date': record.exit_time.date(),
                'records': [],
                'total_revenue': 0,
                'vehicles_count': 0
            }
        daily_data[day]['records'].append(record)
        daily_data[day]['total_revenue'] += record.total_value or 0
        daily_data[day]['vehicles_count'] += 1
    
    # Ordena por dia
    daily_data = dict(sorted(daily_data.items()))
    
    return {
        'summary': stats,
        'daily_data': daily_data
    }

def get_yearly_extract(year):
    """Gera dados detalhados para extrato anual"""
    stats = get_yearly_statistics(year)
    return {
        'summary': stats,
        'monthly_data': stats['monthly_data']
    }

def get_total_extract():
    """Gera dados detalhados para extrato total"""
    stats = get_total_statistics()
    
    # Agrupa registros por ano
    yearly_data = {}
    for record in stats['records']:
        year = record.exit_time.year
        if year not in yearly_data:
            yearly_data[year] = {
                'year': year,
                'records': [],
                'total_revenue': 0,
                'vehicles_count': 0
            }
        yearly_data[year]['records'].append(record)
        yearly_data[year]['total_revenue'] += record.total_value or 0
        yearly_data[year]['vehicles_count'] += 1
    
    # Ordena por ano
    yearly_data = dict(sorted(yearly_data.items()))
    
    return {
        'summary': stats,
        'yearly_data': yearly_data
    }

def get_monthly_comparison_data(year, months_back):
    """Gera dados para comparação mensal"""
    current_date = datetime(year, 12, 1, tzinfo=fuso_brasilia)
    data = []
    
    for i in range(months_back):
        # Calcula o mês
        month_date = current_date - timedelta(days=30 * i)
        month_stats = get_monthly_statistics(month_date.year, month_date.month)
        
        data.append({
            'year': month_date.year,
            'month': month_date.month,
            'month_name': calendar.month_name[month_date.month],
            'label': f"{calendar.month_name[month_date.month][:3]} {month_date.year}",
            'revenue': month_stats['total_revenue'],
            'expenses': month_stats['total_expenses'],
            'profit': month_stats['net_profit'],
            'vehicles': month_stats['total_vehicles']
        })
    
    return list(reversed(data))

def get_yearly_comparison_data(current_year, years_back):
    """Gera dados para comparação anual"""
    data = []
    
    for i in range(years_back):
        year = current_year - i
        year_stats = get_yearly_statistics(year)
        
        data.append({
            'year': year,
            'label': str(year),
            'revenue': year_stats['total_revenue'],
            'expenses': year_stats['total_expenses'],
            'profit': year_stats['net_profit'],
            'vehicles': year_stats['total_vehicles']
        })
    
    return list(reversed(data))

