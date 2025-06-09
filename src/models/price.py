from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from .user import db
import pytz

fuso_brasilia = pytz.timezone('America/Sao_Paulo')

def hora_brasilia():
    return datetime.now(fuso_brasilia)

class PriceConfiguration(db.Model):
    """Modelo para configuração de preços do estacionamento"""
    __tablename__ = 'price_configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Preços para carros
    first_hour_car_price = db.Column(db.Float, nullable=False, default=10.0)
    additional_hour_car_price = db.Column(db.Float, nullable=False, default=5.0)
    daily_car_price = db.Column(db.Float, nullable=False, default=50.0)
    
    # Preços para motos
    first_hour_motorcycle_price = db.Column(db.Float, nullable=False, default=5.0)
    additional_hour_motorcycle_price = db.Column(db.Float, nullable=False, default=3.0)
    daily_motorcycle_price = db.Column(db.Float, nullable=False, default=25.0)
    
    # Tolerancia
    time_tolerance = db.Column(db.Integer, default=5, nullable=False)
    
    # Mantendo os campos originais para compatibilidade com código existente
    first_hour_price = db.Column(db.Float, nullable=False, default=10.0)
    additional_hour_price = db.Column(db.Float, nullable=False, default=5.0)
    
    updated_at = db.Column(db.DateTime, default=hora_brasilia, onupdate=hora_brasilia)
    
    # Relacionamento com o usuário que atualizou a configuração
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('price_updates', lazy=True))
    
    def __repr__(self):
        return f'<PriceConfiguration {self.id} - Carro: R${self.first_hour_car_price}/{self.additional_hour_car_price} - Moto: R${self.first_hour_motorcycle_price}/{self.additional_hour_motorcycle_price}>'
