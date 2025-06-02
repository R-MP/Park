from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, flash
from datetime import datetime
import requests
import pytz
from src.models.parking import ParkingRecord
from src.models.price import PriceConfiguration
from src.models.user import User, db
from src.routes.auth import login_required, admin_required

parking_bp = Blueprint('parking', __name__)

fuso_brasilia = pytz.timezone('America/Sao_Paulo')

@parking_bp.route('/entrada', methods=['GET', 'POST'])
@login_required
def register_entry():
    if request.method == 'POST':
        plate = request.form.get('plate')
        vehicle_type = request.form.get('vehicle_type', 'carro')
        is_daily = request.form.get('is_daily') == 'on'
        
        if not plate:
            flash('A placa do veículo é obrigatória.', 'danger')
            return render_template('parking/entry.html')
        
        existing_entry = ParkingRecord.query.filter_by(
            plate=plate, 
            exit_time=None
        ).first()
        
        if existing_entry:
            flash('Este veículo já está registrado no estacionamento.', 'warning')
            return render_template('parking/entry.html')
        
        car_model = request.form.get('car_model', '')
        car_color = request.form.get('car_color', '')
        
        new_entry = ParkingRecord(
            plate=plate.upper(),
            user_id=session['user_id'],
            vehicle_type=vehicle_type,
            is_daily=is_daily
            # car_model=car_model,
            # car_color=car_color
        )
        
        db.session.add(new_entry)
        db.session.commit()
        
        flash(f'Veículo com placa {plate.upper()} registrado com sucesso!', 'success')
        return redirect(url_for('parking.active_entries'))
    
    return render_template('parking/entry.html')

@parking_bp.route('/saida/<int:record_id>', methods=['GET', 'POST'])
@login_required
def register_exit(record_id):
    record = ParkingRecord.query.get_or_404(record_id)
    fuso_brasilia = pytz.timezone('America/Sao_Paulo')
    
    if record.exit_time:
        flash('Este veículo já foi registrado como saída.', 'warning')
        return redirect(url_for('parking.active_entries'))
    
    if request.method == 'POST':
        record.exit_time = datetime.now(fuso_brasilia)
        price_config = PriceConfiguration.query.order_by(PriceConfiguration.id.desc()).first()
        
        if not price_config:
            price_config = PriceConfiguration(
                first_hour_car_price=10.0,
                additional_hour_car_price=5.0,
                first_hour_motorcycle_price=5.0,
                additional_hour_motorcycle_price=3.0,
                daily_car_price=50.0,
                daily_motorcycle_price=25.0,
                # Mantendo campos originais para compatibilidade
                first_hour_price=10.0,
                additional_hour_price=5.0,
                user_id=session['user_id']
            )
            db.session.add(price_config)
        
        record.calculate_total(price_config)
        db.session.commit()
        
        flash(f'Saída registrada com sucesso! Valor a cobrar: R$ {record.total_value:.2f}', 'success')
        return redirect(url_for('parking.receipt', record_id=record.id))
    
    current_time = datetime.now(fuso_brasilia)
    entry_time = record.entry_time.astimezone(fuso_brasilia)
    
    duration = (current_time - entry_time).total_seconds() / 3600
    
    price_config = PriceConfiguration.query.order_by(PriceConfiguration.id.desc()).first()
    
    if not price_config:
        if record.is_daily:
            estimated_price = 50.0 if record.vehicle_type == 'carro' else 25.0
        else:
            if record.vehicle_type == 'carro':
                estimated_price = 10.0 if duration <= 1 else 10.0 + ((duration - 1) * 5.0)
            else:  # moto
                estimated_price = 5.0 if duration <= 1 else 5.0 + ((duration - 1) * 3.0)
    else:
        if record.is_daily:
            estimated_price = price_config.daily_car_price if record.vehicle_type == 'carro' else price_config.daily_motorcycle_price
        else:
            if record.vehicle_type == 'carro':
                estimated_price = price_config.first_hour_car_price if duration <= 1 else \
                    price_config.first_hour_car_price + ((duration - 1) * price_config.additional_hour_car_price)
            else:  # moto
                estimated_price = price_config.first_hour_motorcycle_price if duration <= 1 else \
                    price_config.first_hour_motorcycle_price + ((duration - 1) * price_config.additional_hour_motorcycle_price)
    
    return render_template(
        'parking/exit.html', 
        record=record, 
        duration=duration,
        estimated_price=estimated_price
    )

@parking_bp.route('/recibo/<int:record_id>')
@login_required
def receipt(record_id):
    record = ParkingRecord.query.get_or_404(record_id)
    
    if not record.exit_time:
        flash('Este veículo ainda não saiu do estacionamento.', 'warning')
        return redirect(url_for('parking.active_entries'))
    
    duration_seconds = (record.exit_time - record.entry_time).total_seconds()
    hours = int(duration_seconds // 3600)
    minutes = int((duration_seconds % 3600) // 60)
    
    return render_template(
        'parking/receipt.html', 
        record=record,
        hours=hours,
        minutes=minutes
    )

@parking_bp.route('/ativos')
@login_required
def active_entries():
    active_records = ParkingRecord.query.filter_by(exit_time=None).order_by(ParkingRecord.entry_time.desc()).all()
    return render_template('parking/active.html', records=active_records)

@parking_bp.route('/historico')
@login_required
def history():
    plate = request.args.get('plate', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = ParkingRecord.query
    
    if plate:
        query = query.filter(ParkingRecord.plate.like(f'%{plate}%'))
    
    if date_from:
        try:
            date_from = fuso_brasilia.localize(datetime.strptime(date_from, '%Y-%m-%d'))
            query = query.filter(ParkingRecord.entry_time >= date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = fuso_brasilia.localize(datetime.strptime(date_to, '%Y-%m-%d'))
            query = query.filter(ParkingRecord.entry_time <= date_to)
        except ValueError:
            pass
    
    records = query.order_by(ParkingRecord.entry_time.desc()).all()
    
    return render_template('parking/history.html', records=records, plate=plate, date_from=date_from, date_to=date_to)

# 🚘 ROTA DE CONSULTA DE PLACA
@parking_bp.route('/consulta_placa', methods=['POST'])
@login_required
def consulta_placa():
    data = request.get_json()
    placa = data.get('plate', '').upper().strip()

    if not placa:
        return jsonify({'error': 'Placa não enviada'}), 400

    try:
        response = requests.post(
            'https://placa-fipe.apibrasil.com.br/placa/consulta',
            json={'placa': placa},
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code != 200:
            return jsonify({'error': 'Erro na consulta'}), 500

        resultado = response.json()
        return jsonify({
            'modelo': resultado.get('modelo', ''),
            'cor': resultado.get('cor', '')
        })
    except Exception as e:
        return jsonify({'error': 'Erro ao consultar placa', 'detalhe': str(e)}), 500
