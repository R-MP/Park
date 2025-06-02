from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pytz

db = SQLAlchemy()

fuso_brasilia = pytz.timezone('America/Sao_Paulo')
def hora_brasilia():
    return datetime.now(fuso_brasilia)

class User(db.Model):
    """Modelo para usuários do sistema"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=hora_brasilia)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Define a senha criptografada para o usuário"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Verifica se a senha fornecida corresponde à senha armazenada"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
