from flask import Flask
import os
from dotenv import load_dotenv
from app.models.models import db

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # Chargement des variables d'environnement
    load_dotenv()
    
    # Configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_change_this'),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'cv_app.sqlite')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # Limite de taille des fichiers à 16 MB
        HR_PASSWORD=os.environ.get('HR_PASSWORD', 'hr_password_change_this')  # Mot de passe simple pour l'accès RH
    )
    
    # Assurez-vous que le dossier instance existe
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Assurez-vous que le dossier uploads existe
    try:
        os.makedirs(os.path.join(app.root_path, 'static', 'uploads'))
    except OSError:
        pass
    
    # Initialisation de la base de données
    db.init_app(app)
    
    # Enregistrement des blueprints
    from app.routes import main, candidate, hr
    app.register_blueprint(main.bp)
    app.register_blueprint(candidate.bp)
    app.register_blueprint(hr.bp)
    
    # Création des tables de la base de données
    with app.app_context():
        db.create_all()
    
    return app
