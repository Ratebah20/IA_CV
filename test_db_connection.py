import os
import pyodbc
from dotenv import load_dotenv

# Chargement des variables d'environnement
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Récupération des informations de connexion
db_server = os.environ.get('DB_SERVER', 'localhost')
db_name = os.environ.get('DB_NAME', 'ATS_CV')

# Construction de la chaîne de connexion avec authentification Windows
conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_server};DATABASE={db_name};Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=NO;"

try:
    # Tentative de connexion
    print(f"Tentative de connexion à {db_server}, base de données {db_name}...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Vérification de la version du serveur
    cursor.execute('SELECT @@VERSION')
    row = cursor.fetchone()
    print('\nConnexion réussie à la base de données!')
    print(f'Version du serveur: {row[0]}')
    
    # Liste des bases de données
    cursor.execute('SELECT name FROM sys.databases')
    print('\nBases de données disponibles:')
    for db in cursor.fetchall():
        print(f' - {db[0]}')
    
    # Liste des tables dans la base de données ATS_CV
    cursor.execute("USE ATS_CV; SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME")
    print('\nTables dans la base de données ATS_CV:')
    for table in cursor.fetchall():
        print(f' - {table[0]}')
    
    # Fermeture des ressources
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'\nErreur de connexion: {str(e)}')
