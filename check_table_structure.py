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
    
    # Vérification de la structure de la table JobPosition
    print("\nStructure de la table JobPosition:")
    cursor.execute("SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'JobPosition' ORDER BY ORDINAL_POSITION")
    columns = cursor.fetchall()
    
    if not columns:
        print("La table JobPosition n'existe pas dans la base de données!")
    else:
        for column in columns:
            print(f" - {column[0]}: {column[1]}", end="")
            if column[1] in ('varchar', 'nvarchar', 'char', 'nchar'):
                print(f"({column[2]})", end="")
            print(f", {'NULL' if column[3] == 'YES' else 'NOT NULL'}")
    
    # Vérification des triggers sur la table JobPosition
    print("\nTriggers sur la table JobPosition:")
    cursor.execute("SELECT name FROM sys.triggers WHERE parent_id = OBJECT_ID('JobPosition')")
    triggers = cursor.fetchall()
    
    if not triggers:
        print("Aucun trigger trouvé sur la table JobPosition")
    else:
        for trigger in triggers:
            print(f" - {trigger[0]}")
    
    # Vérification des données dans la table JobPosition
    print("\nDonnées dans la table JobPosition:")
    cursor.execute("SELECT TOP 5 id, title, is_active FROM JobPosition")
    rows = cursor.fetchall()
    
    if not rows:
        print("Aucune donnée trouvée dans la table JobPosition")
    else:
        for row in rows:
            print(f" - ID: {row[0]}, Titre: {row[1]}, Actif: {row[2]}")
    
    # Fermeture des ressources
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'\nErreur: {str(e)}')
