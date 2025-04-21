from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db
from ..models.auth_models import User
from ..models.models import Candidate, Application
from . import api_bp

@api_bp.route('/candidates', methods=['GET'])
@jwt_required()
def get_candidates():
    """Récupérer tous les candidats (réservé aux utilisateurs authentifiés)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    candidates = Candidate.query.all()
    
    result = []
    for candidate in candidates:
        result.append({
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'email': candidate.email,
            'phone': candidate.phone,
            'applications_count': Application.query.filter_by(candidate_id=candidate.id).count()
        })
    
    return jsonify(result), 200

@api_bp.route('/candidates/<int:candidate_id>', methods=['GET'])
@jwt_required()
def get_candidate(candidate_id):
    """Récupérer un candidat spécifique avec ses candidatures"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    candidate = Candidate.query.get_or_404(candidate_id)
    applications = Application.query.filter_by(candidate_id=candidate.id).all()
    
    applications_data = []
    for app in applications:
        applications_data.append({
            'id': app.id,
            'job_id': app.job_id,
            'status': app.status,
            'created_at': app.created_at.strftime('%Y-%m-%d')
        })
    
    return jsonify({
        'id': candidate.id,
        'first_name': candidate.first_name,
        'last_name': candidate.last_name,
        'email': candidate.email,
        'phone': candidate.phone,
        'applications': applications_data
    }), 200
