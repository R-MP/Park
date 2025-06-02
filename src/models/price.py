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
    first_hour_price = db.Column(db.Float, nullable=False, default=10.0)
    additional_hour_price = db.Column(db.Float, nullable=False, default=5.0)
    updated_at = db.Column(db.DateTime, default=hora_brasilia, onupdate=hora_brasilia)
    
    # Relacionamento com o usuário que atualizou a configuração
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('price_updates', lazy=True))
    
    def __repr__(self):
        return f'<PriceConfiguration {self.id} - R${self.first_hour_price}/{self.additional_hour_price}>'
