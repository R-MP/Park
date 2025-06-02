from flask import Flask, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
import os
import sys

# Configuração do caminho para importações
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Inicialização da aplicação Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Configuração do banco de dados SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estacionamento.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização do SQLAlchemy
from src.models.user import db
db.init_app(app)

# Importação e registro dos blueprints
from src.routes.auth import auth_bp
from src.routes.parking import parking_bp
from src.routes.price import price_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(parking_bp, url_prefix='/parking')
app.register_blueprint(price_bp, url_prefix='/price')

# Config de Tempo
@app.context_processor
def inject_now():
    fuso_brasilia = pytz.timezone('America/Sao_Paulo')
    return {
        'now': datetime.now(fuso_brasilia),
        'pytz': pytz
    }

# Rota principal
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('parking.active_entries'))

# Manipulador de erro 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Criação das tabelas do banco de dados
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
