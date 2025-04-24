from flask import Flask
import os
import urllib.parse
import pyodbc
from dotenv import load_dotenv
from sqlalchemy import event
from flask_login import LoginManager
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from app.models.models import db
from app.api.config import configure_api

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # Chargement des variables d'environnement
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)
    
    # Construction de la chaîne de connexion SQL Server
    db_driver = os.environ.get('DB_DRIVER', 'SQL Server')
    db_server = os.environ.get('DB_SERVER', 'localhost')
    db_name = os.environ.get('DB_NAME', 'ATS_CV')
    db_windows_auth = os.environ.get('DB_WINDOWS_AUTH', 'yes')
    
    # Chaîne de connexion ODBC avec le driver SQL Server natif et authentification Windows
    if db_windows_auth.lower() == 'yes':
        # Utiliser l'authentification Windows (trusted_connection=yes)
        odbc_connection = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_server};DATABASE={db_name};Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=NO;"
        connection_string = f"mssql+pyodbc://{db_server}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes&Encrypt=NO&trusted_connection=yes&charset=latin1"
    else:
        # Utiliser l'authentification SQL Server si nécessaire
        db_user = os.environ.get('DB_USER', 'sa')
        db_password = os.environ.get('DB_PASSWORD', '')
        encoded_password = urllib.parse.quote_plus(db_password)
        odbc_connection = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_server};DATABASE={db_name};UID={db_user};PWD={encoded_password};TrustServerCertificate=yes;Encrypt=NO;"
        connection_string = f"mssql+pyodbc://{db_user}:{encoded_password}@{db_server}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes&Encrypt=NO&trusted_connection=no&charset=latin1"
    
    # Configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_change_this'),
        SQLALCHEMY_DATABASE_URI=connection_string,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Activer le mode debug pour voir les requêtes SQL générées
        #SQLALCHEMY_ECHO=True,
        SQLALCHEMY_ENGINE_OPTIONS={
            'fast_executemany': True,  # Amélioration des performances
            'connect_args': {
                'TrustServerCertificate': 'yes',
                'Encrypt': 'NO'
            }
        },
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
    
    # Initialisation de l'extension SQLAlchemy
    db.init_app(app)
    
    # Initialisation de Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Initialisation des filtres personnalisés pour les templates
    from app.utils import template_filters
    template_filters.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.auth_models import User
        return User.query.get(int(user_id))
    
    # Configuration de l'API REST - Doit être avant l'enregistrement des blueprints
    CORS(app, 
         resources={r"/api/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}},
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         expose_headers=["Content-Type", "Authorization"],
         origins=["http://localhost:3000", "http://127.0.0.1:3000"],
         send_wildcard=False,
         always_send=True)
    jwt = configure_api(app)
    
    # Enregistrement des blueprints
    from app.routes import main, candidate, hr, hr_interview
    from app.auth import bp as auth_bp
    from app.manager import bp as manager_bp
    from app.api import api_bp
    
    app.register_blueprint(main.bp)
    app.register_blueprint(candidate.bp)
    app.register_blueprint(hr.bp)
    app.register_blueprint(hr_interview.bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(manager_bp, url_prefix='/manager')
    app.register_blueprint(api_bp)
    
    # Ne pas recréer les tables car elles existent déjà dans SQL Server
    # Les tables ont été créées avec le script SQL
    # 
    # Configurer SQLAlchemy pour utiliser le schéma de base de données correct
    with app.app_context():
        # Définir le gestionnaire d'événements pour la connexion
        @event.listens_for(db.engine, 'connect')
        def on_connect(dbapi_connection, connection_record):
            # Configurer la connexion pour éviter les problèmes de précision avec SQL Server
            cursor = dbapi_connection.cursor()
            cursor.execute("SET ANSI_NULLS ON")
            cursor.execute("SET ANSI_PADDING ON")
            cursor.execute("SET ANSI_WARNINGS ON")
            cursor.execute("SET ARITHABORT ON")
            cursor.execute("SET CONCAT_NULL_YIELDS_NULL ON")
            cursor.execute("SET QUOTED_IDENTIFIER ON")
            cursor.commit()
            
            # Désactiver la mise en cache des requêtes qui peut causer des problèmes
            cursor.execute("SET NOCOUNT ON")
            cursor.commit()
            
            # Indiquer au driver pyodbc de ne pas tenter de convertir les types de données automatiquement
            dbapi_connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
            dbapi_connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16le')
            dbapi_connection.setencoding(encoding='utf-8', ctype=pyodbc.SQL_CHAR)
            dbapi_connection.setencoding(encoding='utf-16le', ctype=pyodbc.SQL_WCHAR)
        
        # Au lieu de créer les tables, vérifier la connexion
        try:
            # Exécuter une requête simple pour vérifier que la connexion fonctionne
            from sqlalchemy import text
            db.session.execute(text('SELECT 1')).fetchall()
            print("Connexion à la base de données réussie!")
        except Exception as e:
            print(f"Erreur de connexion à la base de données: {str(e)}")
            # Afficher plus de détails sur l'erreur pour faciliter le débogage
            import traceback
            traceback.print_exc()
            # Log l'erreur mais ne pas arrêter l'application
            pass
    
    from markupsafe import Markup, escape
    def nl2br(value):
        return Markup('<br>'.join(escape(value).split('\n')))
    app.jinja_env.filters['nl2br'] = nl2br

    return app
