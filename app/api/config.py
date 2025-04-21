from flask import jsonify, request
from flask_jwt_extended import JWTManager, decode_token
from datetime import timedelta
import os
import logging
import traceback

def configure_api(app):
    
    # Configuration JWT
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", app.config.get("SECRET_KEY"))
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"
    app.config["JWT_ERROR_MESSAGE_KEY"] = "message"
    
    jwt = JWTManager(app)
    
    # Ajouter un logger pour JWT
    logger = logging.getLogger('jwt_debug')
    logger.setLevel(logging.DEBUG)
    
    # Gestionnaire d'erreurs JWT
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        # Log l'erreur de token expiré
        logger.warning(f"Token expiré: Header={jwt_header}, Payload={jwt_payload}")
        
        return jsonify({
            "message": "Le token a expiré",
            "error": "token_expired"
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        # Log l'erreur de token invalide
        auth_header = request.headers.get('Authorization', '')
        logger.warning(f"Token invalide: {error}")
        logger.debug(f"Header Authorization: {auth_header}")
        
        # Essayer de décoder le token pour voir ce qui ne va pas
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            logger.debug(f"Token extrait: {token[:15]}...")
            try:
                # Essayer de décoder sans vérification pour voir le contenu
                import jwt as pyjwt
                decoded = pyjwt.decode(token, options={"verify_signature": False})
                logger.debug(f"Contenu du token (sans vérification): {decoded}")
            except Exception as e:
                logger.error(f"Erreur lors du décodage du token: {str(e)}")
                logger.debug(traceback.format_exc())
        
        return jsonify({
            "message": "Token invalide",
            "error": "invalid_token"
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        # Log l'erreur de token manquant
        logger.warning(f"Token manquant: {error}")
        logger.debug(f"Headers reçus: {dict(request.headers)}")
        
        return jsonify({
            "message": "Token manquant",
            "error": "authorization_required"
        }), 401
    
    # Ajouter un décorateur pour logger les tokens reçus
    @app.before_request
    def log_jwt_token():
        if request.path.startswith('/api/'):
            auth_header = request.headers.get('Authorization', '')
            if auth_header:
                logger.debug(f"API Request: {request.method} {request.path}")
                logger.debug(f"Auth header: {auth_header[:20]}..." if len(auth_header) > 20 else f"Auth header: {auth_header}")
    
    return jwt
