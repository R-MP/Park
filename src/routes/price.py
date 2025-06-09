from flask import Blueprint, request, redirect, url_for, render_template, flash, session
from src.models.price import PriceConfiguration
from src.models.user import User, db
from src.routes.auth import login_required, admin_required
from src.utils.vehicle_data import VehicleDataManager

price_bp = Blueprint('price', __name__)
vehicle_data = VehicleDataManager()

@price_bp.route('/configuracao', methods=['GET', 'POST'])
@login_required
@admin_required
def price_config():
    # Buscar configuração atual
    current_config = PriceConfiguration.query.order_by(PriceConfiguration.id.desc()).first()
    
    # Se não existir, criar configuração padrão
    if not current_config:
        current_config = PriceConfiguration(
            # Preços para carros
            first_hour_car_price=10.0,
            additional_hour_car_price=5.0,
            daily_car_price=50.0,
            
            # Preços para motos
            first_hour_motorcycle_price=5.0,
            additional_hour_motorcycle_price=3.0,
            daily_motorcycle_price=25.0,
            
            # Tolerancia
            time_tolerance=5,
            
            # Mantendo campos originais para compatibilidade
            first_hour_price=10.0,
            additional_hour_price=5.0,
            
            user_id=session['user_id']
        )
        db.session.add(current_config)
        db.session.commit()
    
    if request.method == 'POST':
        # Verificar se o usuário é administrador
        if not session.get('is_admin', False):
            flash('Você não tem permissão para alterar as configurações de preço.', 'danger')
            return redirect(url_for('price.price_config'))
        
        # Obter valores do formulário
        try:
            # Preços para carros
            first_hour_car_price = float(request.form.get('first_hour_car_price', 0))
            additional_hour_car_price = float(request.form.get('additional_hour_car_price', 0))
            daily_car_price = float(request.form.get('daily_car_price', 0))
            
            # Preços para motos
            first_hour_motorcycle_price = float(request.form.get('first_hour_motorcycle_price', 0))
            additional_hour_motorcycle_price = float(request.form.get('additional_hour_motorcycle_price', 0))
            daily_motorcycle_price = float(request.form.get('daily_motorcycle_price', 0))
            
            # Tolerancia
            time_tolerance = int(request.form.get('time_tolerance', 5))
            
            # Validação básica
            if (first_hour_car_price <= 0 or additional_hour_car_price <= 0 or daily_car_price <= 0 or
                first_hour_motorcycle_price <= 0 or additional_hour_motorcycle_price <= 0 or daily_motorcycle_price <= 0):
                flash('Todos os valores de preço devem ser maiores que zero.', 'danger')
                return render_template('price/config.html', config=current_config)
            
            if time_tolerance < 0:
                raise ValueError("Tolerância negativa")
                
            # Criar nova configuração
            new_config = PriceConfiguration(
                # Preços para carros
                first_hour_car_price=first_hour_car_price,
                additional_hour_car_price=additional_hour_car_price,
                daily_car_price=daily_car_price,
                
                # Preços para motos
                first_hour_motorcycle_price=first_hour_motorcycle_price,
                additional_hour_motorcycle_price=additional_hour_motorcycle_price,
                daily_motorcycle_price=daily_motorcycle_price,
                
                # Tolerancia
                time_tolerance=time_tolerance,
                
                # Mantendo campos originais para compatibilidade
                first_hour_price=first_hour_car_price,
                additional_hour_price=additional_hour_car_price,
                
                user_id=session['user_id']
            )
            
            db.session.add(new_config)
            db.session.commit()
            
            flash('Configuração de preços atualizada com sucesso!', 'success')
            return redirect(url_for('price.price_config'))
            
        except ValueError:
            flash('Valores inválidos: preços e tolerância devem ser numéricos e não-negativos.', 'danger')
            return render_template('price/config.html', config=current_config)
    
    # Histórico de configurações (para auditoria)
    config_history = PriceConfiguration.query.order_by(PriceConfiguration.updated_at.desc()).all()
    
    # Carregar marcas para o dropdown
    car_brands = vehicle_data.get_car_brands()
    motorcycle_brands = vehicle_data.get_motorcycle_brands()
    
    return render_template(
        'price/config.html', 
        config=current_config, 
        history=config_history,
        car_brands=car_brands,
        motorcycle_brands=motorcycle_brands
    )
    
@price_bp.route('/refresh-autocomplete')
def refresh_autocomplete():
    try:
        data = vehicle_data.refresh_data()
        return render_template('/config.html', data=data)
    except Exception as e:
        return f"Erro ao atualizar autocomplete: {str(e)}", 500

@price_bp.route('/download-models', methods=['POST'])
@login_required
@admin_required
def download_models():
    """Rota para baixar modelos de veículos da API Invertexto"""
    try:
        # Obter parâmetros do formulário
        brand_id = int(request.form.get('brand_id', 0))
        brand_name = request.form.get('brand_name', '')
        vehicle_type = request.form.get('vehicle_type', '')
        
        # Validação básica
        if not brand_id or not brand_name or not vehicle_type:
            flash('Parâmetros inválidos. Selecione uma marca e tipo de veículo.', 'danger')
            return redirect(url_for('price.price_config'))
        
        # Verificar se o tipo de veículo é válido
        if vehicle_type not in ['carro', 'moto']:
            flash('Tipo de veículo inválido.', 'danger')
            return redirect(url_for('price.price_config'))
        
        # Baixar modelos da API
        success, message, count = vehicle_data.download_models_from_api(brand_id, brand_name, vehicle_type)
        
        # vehicle_data.refresh_data()
        
        if success:
            flash(f'Modelos de {brand_name} baixados com sucesso! Total: {count} modelos.', 'success')
        else:
            flash(f'Erro ao baixar modelos: {message}', 'danger')
        
        return redirect(url_for('price.price_config'))
        
    except Exception as e:
        flash(f'Erro ao processar solicitação: {str(e)}', 'danger')
        return redirect(url_for('price.price_config'))
    
@price_bp.route('/download-brands', methods=['POST'])
@login_required
@admin_required
def download_brands():
    """Rota para baixar marcas de veículos da API Invertexto"""
    try:
        # Obter parâmetros do formulário
        vehicle_type = request.form.get('brand_type', '')
        
        # Verificar se o tipo de veículo é válido
        if vehicle_type not in ['1', '2']:
            flash('Tipo de veículo inválido.', 'danger')
            return redirect(url_for('price.price_config'))
        
        # Baixar modelos da API
        success, message, count = vehicle_data.download_brands_from_api(vehicle_type)
        
        # vehicle_data.refresh_data()
        
        if success:
            flash(f'Marcas baixadas com sucesso! Total: {count} marcas.', 'success')
        else:
            flash(f'Erro ao baixar marcas: {message}', 'danger')
        
        return redirect(url_for('price.price_config'))
        
    except Exception as e:
        flash(f'Erro ao processar solicitação: {str(e)}', 'danger')
        return redirect(url_for('price.price_config'))