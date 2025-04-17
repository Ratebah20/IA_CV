from flask import Blueprint, render_template, redirect, url_for
from app.models.models import JobPosition

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Page d'accueil du site avec la liste des postes disponibles"""
    # Récupérer les postes actifs pour les afficher sur la page d'accueil
    active_jobs = JobPosition.query.filter_by(is_active=True).all()
    from datetime import datetime
    return render_template('index.html', jobs=active_jobs, year=datetime.now().year)
