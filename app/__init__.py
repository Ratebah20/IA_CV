from flask import Flask
import os
import urllib.parse
import pyodbc
from dotenv import load_dotenv
from sqlalchemy import event

from app.models.models import db

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # Chargement des variables d'environnement
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)
    
    # Construction de la chaîne de connexion SQL Server
    db_driver = os.environ.get('DB_DRIVER', 'SQL Server')
    db_server = os.environ.get('DB_SERVER', '10.1.100.44')
    db_name = os.environ.get('DB_NAME', 'ATS_CV')
    db_user = os.environ.get('DB_USER', 'olu_appli-admin')
    db_password = os.environ.get('DB_PASSWORD', '')
    
    # Encoder le mot de passe pour la chaîne de connexion
    encoded_password = urllib.parse.quote_plus(db_password)
    
    # Chaîne de connexion ODBC avec le driver SQL Server natif et désactivation complète des vérifications SSL
    # Utiliser le mot de passe encodé dans la chaîne de connexion
    odbc_connection = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_server};DATABASE={db_name};UID={db_user};PWD={encoded_password};TrustServerCertificate=yes;Encrypt=NO;"
    # Alternative avec paramètres de connexion plus explicites
    connection_string = f"mssql+pyodbc://{db_user}:{encoded_password}@{db_server}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes&Encrypt=NO&trusted_connection=no"
    
    # Configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_change_this'),
        SQLALCHEMY_DATABASE_URI=connection_string,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
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
    
    # Enregistrement des blueprints
    from app.routes import main, candidate, hr
    app.register_blueprint(main.bp)
    app.register_blueprint(candidate.bp)
    app.register_blueprint(hr.bp)
    
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
            dbapi_connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
            dbapi_connection.setencoding(encoding='utf-8')
        
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
