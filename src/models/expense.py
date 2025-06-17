# Modelo para Gastos (Expenses) - Para implementação futura

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from .user import db
import pytz

fuso_brasilia = pytz.timezone('America/Sao_Paulo')

def hora_brasilia():
    return datetime.now(fuso_brasilia)

class Expense(db.Model):
    """Modelo para registros de gastos do estacionamento"""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Informações básicas do gasto
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.DateTime, default=hora_brasilia, nullable=False)
    
    # Categoria do gasto (manutenção, energia, funcionários, etc.)
    category = db.Column(db.String(50), nullable=False, default='outros')
    
    # Observações adicionais
    notes = db.Column(db.Text, nullable=True)
    
    # Campos de auditoria
    created_at = db.Column(db.DateTime, default=hora_brasilia, nullable=False)
    updated_at = db.Column(db.DateTime, default=hora_brasilia, onupdate=hora_brasilia)
    
    # Relacionamento com o usuário que registrou o gasto
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('expenses', lazy=True))
    
    def __repr__(self):
        return f'<Expense {self.description} - R${self.amount} - {self.expense_date}>'

# Categorias padrão para gastos
EXPENSE_CATEGORIES = [
    'manutencao',
    'energia',
    'funcionarios',
    'equipamentos',
    'limpeza',
    'seguranca',
    'outros'
]

