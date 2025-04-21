"""
Script d'initialisation pour créer les premiers utilisateurs (RH et managers)
Exécuter ce script une seule fois pour initialiser les données
"""
import os
import sys
from dotenv import load_dotenv
from flask import Flask
from app import create_app
from app.models.auth_models import User, Role, db

# Chargement des variables d'environnement
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Création de l'application Flask
app = create_app()

def init_roles():
    """Initialisation des rôles"""
    print("Initialisation des rôles...")
    
    # Vérifier si les rôles existent déjà
    if Role.query.count() > 0:
        print("Les rôles existent déjà.")
        return
    
    # Création des rôles
    roles = [
        Role(id=1, name='RH', description='Personnel RH avec gestion complète des candidatures et aux systèmes'),
        Role(id=2, name='MANAGER', description='Manager avec accès restreint aux candidatures et postes du département concerné')
    ]
    
    db.session.add_all(roles)
    db.session.commit()
    print("Rôles créés avec succès.")

def init_users():
    """Initialisation des utilisateurs"""
    print("Initialisation des utilisateurs...")
    
    # Vérifier si les utilisateurs existent déjà
    if User.query.count() > 0:
        print("Des utilisateurs existent déjà.")
        return
    
    # Création des utilisateurs
    users = [
        # Utilisateur RH
        {
            'username': 'admin_rh',
            'email': 'rh@example.com',
            'password': 'password123',
            'role_id': 1,  # RH
            'department': None
        },
        # Manager Informatique
        {
            'username': 'manager_it',
            'email': 'it@example.com',
            'password': 'password123',
            'role_id': 2,  # MANAGER
            'department': 'Informatique'
        },
        # Manager Marketing
        {
            'username': 'manager_marketing',
            'email': 'marketing@example.com',
            'password': 'password123',
            'role_id': 2,  # MANAGER
            'department': 'Marketing'
        },
        # Manager Ressources Humaines
        {
            'username': 'manager_rh',
            'email': 'manager_rh@example.com',
            'password': 'password123',
            'role_id': 2,  # MANAGER
            'department': 'Ressources Humaines'
        }
    ]
    
    for user_data in users:
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            role_id=user_data['role_id'],
            department=user_data['department']
        )
        user.set_password(user_data['password'])
        db.session.add(user)
    
    db.session.commit()
    print("Utilisateurs créés avec succès.")

def init_departments():
    """Mise à jour des offres d'emploi existantes avec des départements"""
    from app.models.models import JobPosition
    
    print("Mise à jour des départements pour les offres d'emploi existantes...")
    
    # Liste des départements
    departments = ['Informatique', 'Marketing', 'Ressources Humaines', 'Finance', 'Commercial']
    
    # Récupérer toutes les offres d'emploi
    jobs = JobPosition.query.all()
    
    if not jobs:
        print("Aucune offre d'emploi trouvée.")
        return
    
    # Attribuer un département à chaque offre d'emploi
    import random
    for i, job in enumerate(jobs):
        # Attribuer un département de manière cyclique
        job.department = departments[i % len(departments)]
    
    db.session.commit()
    print(f"{len(jobs)} offres d'emploi mises à jour avec des départements.")

def main():
    """Fonction principale"""
    with app.app_context():
        try:
            # Initialisation des rôles
            init_roles()
            
            # Initialisation des utilisateurs
            init_users()
            
            # Mise à jour des départements pour les offres d'emploi existantes
            init_departments()
            
            print("Initialisation terminée avec succès.")
        except Exception as e:
            print(f"Erreur lors de l'initialisation: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    main()
