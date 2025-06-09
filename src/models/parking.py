from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from pytz import utc
from .user import db
import pytz
import math

fuso_brasilia = pytz.timezone('America/Sao_Paulo')

def to_utc_aware(dt):
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return utc.localize(dt)
    return dt

class ParkingRecord(db.Model):
    """Modelo para registros de estacionamento"""
    __tablename__ = 'parking_records'
    
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(10), nullable=False, index=True)
    entry_time = db.Column(db.DateTime, default=lambda: datetime.now(fuso_brasilia), nullable=False)
    exit_time = db.Column(db.DateTime, nullable=True)
    total_value = db.Column(db.Float, nullable=True)
    
    # Novo campo para tipo de veículo (carro/moto)
    vehicle_type = db.Column(db.String(10), nullable=False, default='carro')
    
    # Novo campo para indicar se é diária
    is_daily = db.Column(db.Boolean, default=False)
    
    # Campos opcionais (comentados conforme solicitado)
    # car_model = db.Column(db.String(50), nullable=True)
    # car_color = db.Column(db.String(30), nullable=True)
    
    # Relacionamento com o usuário que registrou a entrada/saída
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('parking_records', lazy=True))
    
    def calculate_total(self, price_config):
        """Calcula o valor total com base no tempo de permanência e configuração de preços"""
        if not self.exit_time:
            return None
        
        # Converter para o mesmo fuso (São Paulo)
        entry_time = self.entry_time.astimezone(fuso_brasilia)
        exit_time = self.exit_time.astimezone(fuso_brasilia)

        duration = (exit_time - entry_time).total_seconds() / 3600
        
        # Tolerancia
        tol = getattr(price_config, 'time_tolerance', None)
        tolerance = tol if (isinstance(tol, (int, float)) and tol >= 0) else 5
        
        # Cálculo de diária
        if self.is_daily:
            # dias iniciados (por exemplo, 1,1d → 2 dias)
            days = math.ceil(duration / 24)
            if self.vehicle_type == 'moto':
                price = price_config.daily_motorcycle_price
            else:
                price = price_config.daily_car_price
            self.total_value = round(days * price, 2)
            return self.total_value

        # Cálculo por hora
        hours_to_charge = max(1, math.ceil((duration - tolerance) / 60))
        
        if self.vehicle_type == 'moto':
            first = price_config.first_hour_motorcycle_price
            extra = price_config.additional_hour_motorcycle_price
        else:
            first = price_config.first_hour_car_price
            extra = price_config.additional_hour_car_price
            
        # Dentro da tolerancia inicial
        if duration <= tolerance:
            self.total_value = 0.0
            return self.total_value

        self.total_value = round(first + (hours_to_charge - 1) * extra, 2)
        return self.total_value
    
    def __repr__(self):
        return f'<ParkingRecord {self.plate} - {self.vehicle_type} - {self.entry_time}>'
