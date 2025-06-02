from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.user import User, db
import functools

auth_bp = Blueprint('auth', __name__)

# Decorator para verificar se o usuário está logado
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

# Decorator para verificar se o usuário é administrador
def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validação básica
        if not username or not email or not password:
            flash('Todos os campos são obrigatórios.', 'danger')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('As senhas não coincidem.', 'danger')
            return render_template('auth/register.html')
            
        # Verificar se o usuário ou email já existem
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Nome de usuário já está em uso.', 'danger')
            return render_template('auth/register.html')
            
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email já está em uso.', 'danger')
            return render_template('auth/register.html')
            
        # Criar novo usuário
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        # O primeiro usuário registrado será administrador
        if User.query.count() == 0:
            new_user.is_admin = True
            
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registro realizado com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validação básica
        if not username or not password:
            flash('Nome de usuário e senha são obrigatórios.', 'danger')
            return render_template('auth/login.html')
            
        # Verificar usuário e senha
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Nome de usuário ou senha incorretos.', 'danger')
            return render_template('auth/login.html')
            
        # Atualizar último login
        from datetime import datetime
        import pytz
        fuso_brasilia = pytz.timezone('America/Sao_Paulo')
        user.last_login = datetime.now(fuso_brasilia)
        db.session.commit()
        
        # Criar sessão
        session.clear()
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        session['dark_mode'] = user.dark_mode  # Adicionar preferência de modo escuro à sessão
        
        flash(f'Bem-vindo, {user.username}!', 'success')
        return redirect(url_for('index'))
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('auth/profile.html', user=user)

@auth_bp.route('/toggle_dark_mode')
@login_required
def toggle_dark_mode():
    user = User.query.get(session['user_id'])
    user.dark_mode = not user.dark_mode
    db.session.commit()
    
    # Atualizar a sessão
    session['dark_mode'] = user.dark_mode
    
    return redirect(request.referrer or url_for('index'))
