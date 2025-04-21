from flask import request, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt, decode_token
from datetime import datetime, timezone, timedelta
import logging
import json
import traceback
from .. import db
from ..models.auth_models import User
from . import api_bp

# Configurer le logger pour l'authentification
auth_logger = logging.getLogger('auth')
auth_logger.setLevel(logging.DEBUG)

@api_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Identifiants manquants'}), 400
    
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user or not user.check_password(data.get('password')):
        return jsonify({'message': 'Identifiants incorrects'}), 401
    
    # Créer les tokens avec des informations supplémentaires
    additional_claims = {
        'username': user.username,
        'email': user.email,
        'role_id': user.role_id,
        'is_hr': user.is_hr(),
        'sub': str(user.id)  # Ajouter explicitement le sujet comme chaîne
    }
    
    auth_logger.debug(f"Claims supplémentaires pour le token: {additional_claims}")
    
    # Définir les délais d'expiration
    access_expires = timedelta(hours=1)
    refresh_expires = timedelta(days=30)
    
    # Créer les tokens avec les claims supplémentaires
    access_token = create_access_token(
        identity=user.id,
        additional_claims=additional_claims,
        expires_delta=access_expires
    )
    refresh_token = create_refresh_token(
        identity=user.id,
        additional_claims=additional_claims,
        expires_delta=refresh_expires
    )
    
    # Log pour le débogage
    current_app.logger.info(f"Utilisateur {user.username} connecté avec succès")
    auth_logger.debug(f"Access token généré: {access_token[:20]}...")
    
    # Essayer de décoder le token pour vérifier son contenu
    try:
        decoded_token = decode_token(access_token)
        auth_logger.debug(f"Token décodé: {json.dumps(decoded_token, default=str)}")
        auth_logger.debug(f"Type de l'identité dans le token: {type(decoded_token.get('sub')).__name__}")
    except Exception as e:
        auth_logger.error(f"Erreur lors du décodage du token: {str(e)}")
        auth_logger.debug(traceback.format_exc())
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role_id': user.role_id,
            'department': user.department,
            'is_hr': user.is_hr()
        }
    }), 200

@api_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    # Récupérer l'identité et les claims du token de rafraîchissement
    identity = get_jwt_identity()
    jwt_claims = get_jwt()
    
    # Récupérer les informations utilisateur pour les claims supplémentaires
    user = User.query.get(identity)
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    # Créer un nouveau token d'accès avec les mêmes claims supplémentaires
    additional_claims = {
        'username': user.username,
        'email': user.email,
        'role_id': user.role_id,
        'is_hr': user.is_hr(),
        'sub': str(identity)  # Ajouter explicitement le sujet comme chaîne
    }
    
    auth_logger.debug(f"Claims pour le refresh token: {additional_claims}")
    auth_logger.debug(f"Type de l'identité: {type(identity).__name__}, Valeur: {identity}")
    
    access_token = create_access_token(
        identity=identity,
        additional_claims=additional_claims,
        expires_delta=timedelta(hours=1)
    )
    
    # Log pour le débogage
    current_app.logger.info(f"Token rafraîchi pour l'utilisateur {user.username}")
    auth_logger.debug(f"Nouveau access token généré: {access_token[:20]}...")
    
    # Essayer de décoder le token pour vérifier son contenu
    try:
        decoded_token = decode_token(access_token)
        auth_logger.debug(f"Token rafraîchi décodé: {json.dumps(decoded_token, default=str)}")
        auth_logger.debug(f"Type de l'identité dans le token rafraîchi: {type(decoded_token.get('sub')).__name__}")
    except Exception as e:
        auth_logger.error(f"Erreur lors du décodage du token rafraîchi: {str(e)}")
        auth_logger.debug(traceback.format_exc())
    
    return jsonify({'access_token': access_token}), 200

@api_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def me():
    # Récupérer l'identité et les claims du token
    user_id = get_jwt_identity()
    jwt_claims = get_jwt()
    
    # Log pour le débogage
    current_app.logger.info(f"Requête /me pour l'utilisateur ID {user_id}")
    current_app.logger.debug(f"Claims JWT: {jwt_claims}")
    
    # Logs détaillés pour le débogage
    auth_logger.debug(f"Type de l'identité dans /me: {type(user_id).__name__}, Valeur: {user_id}")
    auth_logger.debug(f"Headers reçus: {dict(request.headers)}")
    
    auth_header = request.headers.get('Authorization', '')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        auth_logger.debug(f"Token extrait: {token[:20]}...")
        
        # Essayer de décoder le token sans vérification
        try:
            import jwt as pyjwt
            decoded = pyjwt.decode(token, options={"verify_signature": False})
            auth_logger.debug(f"Contenu du token (sans vérification): {decoded}")
        except Exception as e:
            auth_logger.error(f"Erreur lors du décodage manuel du token: {str(e)}")
            auth_logger.debug(traceback.format_exc())
    
    user = User.query.get(user_id)
    
    if not user:
        current_app.logger.warning(f"Utilisateur ID {user_id} non trouvé dans la base de données")
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    # Log pour le débogage
    current_app.logger.info(f"Utilisateur {user.username} récupéré avec succès")
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role_id': user.role_id,
        'department': user.department,
        'is_hr': user.is_hr()
    }), 200
