from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, flash
from src.models.price import PriceConfiguration
from src.models.user import User, db
from src.routes.auth import login_required, admin_required

price_bp = Blueprint('price', __name__)

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
            return redirect(url_for('index'))
        
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
            
            # Validação básica
            if (first_hour_car_price <= 0 or additional_hour_car_price <= 0 or daily_car_price <= 0 or
                first_hour_motorcycle_price <= 0 or additional_hour_motorcycle_price <= 0 or daily_motorcycle_price <= 0):
                flash('Todos os valores de preço devem ser maiores que zero.', 'danger')
                return render_template('price/config.html', config=current_config)
                
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
            flash('Os valores de preço devem ser números válidos.', 'danger')
            return render_template('price/config.html', config=current_config)
    
    # Histórico de configurações (para auditoria)
    config_history = PriceConfiguration.query.order_by(PriceConfiguration.updated_at.desc()).all()
    
    return render_template('price/config.html', config=current_config, history=config_history)
