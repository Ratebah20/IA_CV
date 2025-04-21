from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from .. import db
from ..models.auth_models import User, InterviewRequest
from ..models.models import Application, Candidate, JobPosition
from . import api_bp

@api_bp.route('/interview-requests', methods=['GET'])
@jwt_required()
def get_interview_requests():
    """Récupérer les demandes d'entretien (filtré selon le rôle de l'utilisateur)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    # Si l'utilisateur est RH, il peut voir toutes les demandes
    if user.is_hr():
        requests = InterviewRequest.query.all()
    # Sinon, il ne voit que ses propres demandes
    else:
        requests = InterviewRequest.query.filter_by(manager_id=user.id).all()
    
    result = []
    for req in requests:
        application = Application.query.get(req.application_id)
        candidate = Candidate.query.get(application.candidate_id)
        job = JobPosition.query.get(application.job_position_id)
        
        result.append({
            'id': req.id,
            'application_id': req.application_id,
            'manager_id': req.manager_id,
            'manager_name': f"{User.query.get(req.manager_id).username}",
            'candidate': {
                'id': candidate.id,
                'name': f"{candidate.first_name} {candidate.last_name}",
                'email': candidate.email
            },
            'job': {
                'id': job.id,
                'title': job.title
            },
            'requested_date': req.requested_date.strftime('%Y-%m-%dT%H:%M'),
            'status': req.status,
            'comments': req.comments,
            'created_at': req.created_at.strftime('%Y-%m-%d')
        })
    
    return jsonify(result), 200

@api_bp.route('/interview-requests/<int:request_id>', methods=['GET'])
@jwt_required()
def get_interview_request(request_id):
    """Récupérer une demande d'entretien spécifique"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    req = InterviewRequest.query.get_or_404(request_id)
    
    # Vérifier les autorisations
    if not user.is_hr() and req.manager_id != user.id:
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    application = Application.query.get(req.application_id)
    candidate = Candidate.query.get(application.candidate_id)
    job = JobPosition.query.get(application.job_position_id)
    
    return jsonify({
        'id': req.id,
        'application_id': req.application_id,
        'manager_id': req.manager_id,
        'manager_name': f"{User.query.get(req.manager_id).username}",
        'candidate': {
            'id': candidate.id,
            'name': f"{candidate.first_name} {candidate.last_name}",
            'email': candidate.email
        },
        'job': {
            'id': job.id,
            'title': job.title
        },
        'requested_date': req.requested_date.strftime('%Y-%m-%dT%H:%M'),
        'status': req.status,
        'comments': req.comments,
        'created_at': req.created_at.strftime('%Y-%m-%d')
    }), 200

@api_bp.route('/interview-requests', methods=['POST'])
@jwt_required()
def create_interview_request():
    """Créer une nouvelle demande d'entretien"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    data = request.get_json()
    
    if not data or not data.get('application_id') or not data.get('requested_date'):
        return jsonify({'message': 'Données manquantes'}), 400
    
    application_id = data.get('application_id')
    requested_date = data.get('requested_date')
    comments = data.get('comments', '')
    
    # Vérifier que la candidature existe
    application = Application.query.get(application_id)
    if not application:
        return jsonify({'message': 'Candidature non trouvée'}), 404
    
    # Vérifier les autorisations (si l'utilisateur est manager, il doit être du même département que l'offre d'emploi)
    job = JobPosition.query.get(application.job_position_id)
    if not user.is_hr() and job.department != user.department:
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    # Vérifier si une demande existe déjà pour cette candidature
    existing_request = InterviewRequest.query.filter_by(application_id=application_id).first()
    if existing_request:
        return jsonify({'message': 'Une demande d\'entretien existe déjà pour cette candidature'}), 400
    
    # Convertir la date de string à datetime
    try:
        requested_date_obj = datetime.strptime(requested_date, '%Y-%m-%dT%H:%M')
    except ValueError:
        return jsonify({'message': 'Format de date invalide. Utilisez YYYY-MM-DDTHH:MM'}), 400
    
    # Créer la demande d'entretien
    interview_request = InterviewRequest(
        application_id=application_id,
        manager_id=user.id,
        requested_date=requested_date_obj,
        status='PENDING',
        comments=comments
    )
    
    db.session.add(interview_request)
    db.session.commit()
    
    return jsonify({
        'message': 'Demande d\'entretien créée avec succès',
        'id': interview_request.id
    }), 201

@api_bp.route('/interview-requests/<int:request_id>/status', methods=['PUT'])
@jwt_required()
def update_interview_request_status(request_id):
    """Mettre à jour le statut d'une demande d'entretien (réservé aux RH)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_hr():
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    req = InterviewRequest.query.get_or_404(request_id)
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'message': 'Statut manquant'}), 400
    
    new_status = data.get('status')
    
    # Vérifier que le statut est valide
    valid_statuses = ['PENDING', 'APPROVED', 'REFUSED', 'COMPLETED']
    if new_status not in valid_statuses:
        return jsonify({'message': 'Statut invalide'}), 400
    
    req.status = new_status
    
    # Si la demande est approuvée, mettre à jour le statut de la candidature
    if new_status == 'APPROVED':
        application = Application.query.get(req.application_id)
        application.status = 3  # INTERVIEW
        
    db.session.commit()
    
    return jsonify({
        'message': 'Statut mis à jour avec succès',
        'status': req.status
    }), 200
