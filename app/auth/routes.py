from flask import render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.auth import bp
from app.models.auth_models import User, Role
from app.auth.forms import LoginForm, RegisterForm
from functools import wraps

def hr_required(f):
    """Décorateur pour restreindre l'accès aux utilisateurs RH uniquement"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_hr():
            flash('Accès restreint. Vous devez être un membre RH pour accéder à cette page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    """Décorateur pour restreindre l'accès aux managers uniquement"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_manager():
            flash('Accès restreint. Vous devez être un manager pour accéder à cette page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Route de connexion"""
    if current_user.is_authenticated:
        if current_user.is_hr():
            return redirect(url_for('hr.dashboard'))
        elif current_user.is_manager():
            return redirect(url_for('manager.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Log pour débogage
        print(f"Tentative de connexion avec username: {form.username.data}")
        
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None:
            print(f"Utilisateur {form.username.data} non trouvé dans la base de données")
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'danger')
            return redirect(url_for('auth.login'))
        
        # Log pour débogage
        print(f"Utilisateur trouvé: {user.username}, role_id: {user.role_id}, hash: {user.password_hash[:20]}...")
        
        password_check = user.check_password(form.password.data)
        print(f"Résultat de la vérification du mot de passe: {password_check}")
        
        if not password_check:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            if user.is_hr():
                next_page = url_for('hr.dashboard')
            elif user.is_manager():
                next_page = url_for('manager.dashboard')
        
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Connexion', form=form)

@bp.route('/logout')
@login_required
def logout():
    """Route de déconnexion"""
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
@hr_required  # Seuls les RH peuvent créer de nouveaux utilisateurs
def register():
    """Route d'enregistrement d'un nouvel utilisateur (réservée aux RH)"""
    form = RegisterForm()
    
    # Récupération des rôles pour le formulaire
    form.role.choices = [(r.id, r.name) for r in Role.query.all()]
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role_id=form.role.data,
            department=form.department.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Utilisateur {form.username.data} créé avec succès!', 'success')
        return redirect(url_for('hr.dashboard'))
    
    return render_template('auth/register.html', title='Nouvel utilisateur', form=form)
