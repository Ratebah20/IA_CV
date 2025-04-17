# Application de Gestion des Candidatures avec Analyse IA

Cette application web permet de gérer les candidatures pour différentes offres d'emploi. Les candidats peuvent postuler directement en ligne et les recruteurs peuvent analyser les CV à l'aide de l'IA d'OpenAI.

## Fonctionnalités

### Pour les candidats
- Consulter les offres d'emploi disponibles
- Postuler directement en ligne en joignant un CV au format PDF
- Ajouter une lettre de motivation (optionnel)

### Pour les recruteurs (RH)
- Créer et gérer des offres d'emploi
- Consulter et filtrer les candidatures reçues
- Analyser les CV par rapport à la description du poste grâce à l'IA d'OpenAI
- Suivre le statut des candidatures

## Installation

1. Cloner le dépôt :
```
git clone <URL_du_repo>
cd IA_CV
```

2. Créer un environnement virtuel Python et l'activer :
```
python -m venv venv
venv\Scripts\activate  # Sur Windows
```

3. Installer les dépendances :
```
pip install -r requirements.txt
```

4. Créer un fichier `.env` à la racine du projet et y ajouter les variables d'environnement suivantes :
```
SECRET_KEY=votre_cle_secrete_ici
OPENAI_API_KEY=votre_cle_api_openai_ici
HR_PASSWORD=mot_de_passe_rh_ici
```

## Utilisation

1. Lancer l'application :
```
python run.py
```

2. Accéder à l'application dans votre navigateur :
```
http://127.0.0.1:5000
```

3. Pour accéder à l'espace RH, cliquez sur "Espace RH" dans la barre de navigation et utilisez le mot de passe défini dans le fichier `.env`.

## Structure du projet

```
IA_CV/
├── app/                       # Répertoire principal de l'application
│   ├── models/                # Modèles de données
│   ├── routes/                # Routes et contrôleurs
│   ├── static/                # Fichiers statiques (CSS, JS, uploads)
│   │   └── uploads/           # Répertoire où sont stockés les CV téléchargés
│   ├── templates/             # Templates HTML
│   ├── utils/                 # Utilitaires
│   └── __init__.py            # Initialisation de l'application Flask
├── instance/                  # Données d'instance (base de données SQLite)
├── requirements.txt           # Dépendances Python
├── .env                       # Variables d'environnement (à créer)
└── run.py                     # Point d'entrée de l'application
```

## Technologies utilisées

- Flask : Framework web léger pour Python
- SQLAlchemy : ORM pour la gestion de la base de données
- OpenAI API : Pour l'analyse des CV
- Bootstrap : Pour l'interface utilisateur
- PyPDF2 : Pour l'extraction du texte des CV PDF

## Sécurité

- Ne pas partager votre clé API OpenAI
- Changer le mot de passe RH par défaut
- Utiliser une clé secrète forte pour l'application
