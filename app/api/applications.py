from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from .. import db
from ..models.auth_models import User
from ..models.models import JobPosition, Application, Candidate, ApplicationStatus, Department
from ..utils.ai_analysis import analyze_cv
from . import api_bp

@api_bp.route('/applications', methods=['GET'])
@jwt_required()
def get_applications():
    """Récupérer les candidatures (filtré selon le rôle de l'utilisateur)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    # Si l'utilisateur est RH, il peut voir toutes les candidatures
    if user.is_hr():
        applications = Application.query.all()
    # Sinon, il ne voit que les candidatures pour son département
    elif user.department_id:  # Vérifier que l'utilisateur a un département attribué
        job_positions = JobPosition.query.filter_by(department_id=user.department_id).all()
        job_ids = [job.id for job in job_positions]
        applications = Application.query.filter(Application.job_position_id.in_(job_ids)).all()
    else:
        # Si l'utilisateur n'a pas de département, renvoyer une liste vide
        applications = []
    
    result = []
    for app in applications:
        candidate = Candidate.query.get(app.candidate_id)
        job = JobPosition.query.get(app.job_position_id)
        
        # Récupérer le nom du département
        department_name = "Non spécifié"
        if job.department_id:
            department = Department.query.get(job.department_id)
            if department:
                department_name = department.name
        
        result.append({
            'id': app.id,
            'candidate': {
                'id': candidate.id,
                'first_name': candidate.first_name,
                'last_name': candidate.last_name,
                'email': candidate.email,
                'phone': candidate.phone
            },
            'job': {
                'id': job.id,
                'title': job.title,
                'department_id': job.department_id,
                'department_name': department_name
            },
            'status': app.status,
            'status_text': ApplicationStatus.get_name(app.status),
            'cover_letter': app.cover_letter,
            'cv_filename': app.cv_filename,
            'ai_analysis': app.ai_analysis,
            'ai_score': app.ai_score,
            'created_at': app.created_at.strftime('%Y-%m-%d')
        })
    
    return jsonify(result), 200

@api_bp.route('/applications/<int:application_id>', methods=['GET'])
@jwt_required()
def get_application(application_id):
    """Récupérer une candidature spécifique"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    application = Application.query.get_or_404(application_id)
    job = JobPosition.query.get(application.job_position_id)
    
    # Vérifier les autorisations
    if not user.is_hr() and job.department_id != user.department_id:
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    candidate = Candidate.query.get(application.candidate_id)
    
    # Récupérer le nom du département
    department_name = "Non spécifié"
    if job.department_id:
        department = Department.query.get(job.department_id)
        if department:
            department_name = department.name
    
    return jsonify({
        'id': application.id,
        'candidate': {
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'email': candidate.email,
            'phone': candidate.phone
        },
        'job': {
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'requirements': job.requirements,
            'department_id': job.department_id,
            'department_name': department_name
        },
        'status': application.status,
        'status_text': ApplicationStatus.get_name(application.status),
        'cover_letter': application.cover_letter,
        'cv_filename': application.cv_filename,
        'ai_analysis': application.ai_analysis,
        'ai_score': application.ai_score,
        'created_at': application.created_at.strftime('%Y-%m-%d')
    }), 200

@api_bp.route('/applications/<int:application_id>/status', methods=['PUT'])
@jwt_required()
def update_application_status(application_id):
    """Mettre à jour le statut d'une candidature"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    application = Application.query.get_or_404(application_id)
    job = JobPosition.query.get(application.job_position_id)
    
    # Vérifier les autorisations
    if not user.is_hr() and job.department_id != user.department_id:
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'message': 'Statut manquant'}), 400
    
    new_status = data.get('status')
    
    # Vérifier que le statut est valide
    valid_statuses = [
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.REJECTED,
        ApplicationStatus.ACCEPTED
    ]
    
    if new_status not in valid_statuses:
        return jsonify({'message': 'Statut invalide'}), 400
    
    try:
        # Utiliser une requête de mise à jour directe plutôt que de modifier l'objet
        # Cela évite les problèmes de concurrence et de StaleDataError
        db.session.execute(
            db.update(Application)
            .where(Application.id == application_id)
            .values(status_id=new_status)
        )
        db.session.commit()
        
        # Rafraîchir l'objet pour obtenir les dernières valeurs
        db.session.refresh(application)
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Erreur lors de la mise à jour du statut: {str(e)}'}), 500
    
    return jsonify({
        'message': 'Statut mis à jour avec succès',
        'status': application.status,
        'status_text': ApplicationStatus.get_name(application.status)
    }), 200

@api_bp.route('/applications', methods=['POST'])
def create_application():
    """Créer une nouvelle candidature (accessible sans authentification)"""
    # Les données du formulaire peuvent être envoyées en multipart/form-data
    # pour gérer le téléchargement du CV
    job_id = request.form.get('job_id')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    cover_letter = request.form.get('cover_letter')
    
    if not job_id or not first_name or not last_name or not email:
        return jsonify({'message': 'Données manquantes'}), 400
    
    # Vérifier que l'offre d'emploi existe
    job = JobPosition.query.get(job_id)
    if not job:
        return jsonify({'message': 'Offre d\'emploi non trouvée'}), 404
    
    # Créer ou récupérer le candidat
    candidate = Candidate.query.filter_by(email=email).first()
    if not candidate:
        candidate = Candidate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone or ''
        )
        db.session.add(candidate)
        db.session.flush()  # Pour obtenir l'ID du candidat
    
    # Gérer le téléchargement du CV
    cv_filename = None
    if 'cv' in request.files:
        cv_file = request.files['cv']
        if cv_file and cv_file.filename:
            # Sécuriser le nom du fichier
            filename = secure_filename(cv_file.filename)
            # Ajouter un timestamp pour éviter les doublons
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            cv_filename = f"{timestamp}_{filename}"
            
            # Créer le dossier uploads s'il n'existe pas
            uploads_dir = os.path.join('app', 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Sauvegarder le fichier
            cv_file.save(os.path.join(uploads_dir, cv_filename))
    
    # Créer la candidature
    application = Application(
        job_position_id=job_id,
        candidate_id=candidate.id,
        status_id=ApplicationStatus.SUBMITTED,
        cover_letter=cover_letter or '',
        cv_filename=cv_filename
    )
    
    db.session.add(application)
    db.session.commit()
    
    return jsonify({
        'message': 'Candidature soumise avec succès',
        'application_id': application.id
    }), 201

@api_bp.route('/applications/department/<int:department_id>', methods=['GET'])
@jwt_required()
def get_applications_by_department(department_id):
    """Récupérer les candidatures pour un département spécifique"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    # Vérifier les autorisations : soit l'utilisateur est RH, soit il appartient au département demandé
    if not user.is_hr() and user.department_id != department_id:
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    # Vérifier que le département existe
    department = Department.query.get_or_404(department_id)
    
    # Récupérer toutes les offres d'emploi pour ce département
    job_positions = JobPosition.query.filter_by(department_id=department_id).all()
    job_ids = [job.id for job in job_positions]
    
    # Récupérer les candidatures pour ces offres
    applications = Application.query.filter(Application.job_position_id.in_(job_ids)).all() if job_ids else []
    
    result = []
    for app in applications:
        candidate = Candidate.query.get(app.candidate_id)
        job = JobPosition.query.get(app.job_position_id)
        
        result.append({
            'id': app.id,
            'candidate': {
                'id': candidate.id,
                'first_name': candidate.first_name,
                'last_name': candidate.last_name,
                'email': candidate.email,
                'phone': candidate.phone
            },
            'job': {
                'id': job.id,
                'title': job.title,
                'department_id': job.department_id,
                'department_name': department.name
            },
            'status': app.status,
            'status_text': ApplicationStatus.get_name(app.status),
            'cover_letter': app.cover_letter,
            'cv_filename': app.cv_filename,
            'ai_analysis': app.ai_analysis,
            'ai_score': app.ai_score,
            'created_at': app.created_at.strftime('%Y-%m-%d')
        })
    
    return jsonify(result), 200

@api_bp.route('/applications/<int:application_id>/analyze', methods=['POST'])
@jwt_required()
def analyze_application_cv(application_id):
    """Analyser le CV d'une candidature avec l'IA"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilisateur non trouvé'}), 404
    
    application = Application.query.get_or_404(application_id)
    job = JobPosition.query.get(application.job_position_id)
    
    # Vérifier les autorisations
    if not user.is_hr() and job.department_id != user.department_id:
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    # Vérifier que le CV existe
    if not application.cv_filename:
        return jsonify({'message': 'Aucun CV trouvé pour cette candidature'}), 400
    
    # Chemin du CV
    cv_path = os.path.join('app', 'static', 'uploads', application.cv_filename)
    
    # Vérifier que le fichier CV existe
    if not os.path.exists(cv_path):
        return jsonify({'message': 'Le fichier CV n\'a pas été trouvé'}), 404
    
    try:
        # Appel à la fonction d'analyse IA
        analysis_result, score = analyze_cv(cv_path, job.description, job.requirements)
        
        # S'assurer que l'analyse est en UTF-8 pour éviter les problèmes d'encodage
        if isinstance(analysis_result, str):
            # Remplacer les apostrophes typographiques par des apostrophes simples
            analysis_result = analysis_result.replace('\u2019', "'")
            # Autres remplacements possibles si nécessaire
            analysis_result = analysis_result.replace('\u2018', "'")
            analysis_result = analysis_result.replace('\u201c', '"')
            analysis_result = analysis_result.replace('\u201d', '"')
        
        # Mise à jour des résultats de l'analyse
        db.session.query(Application).filter_by(id=application_id).update(
            {
                'ai_analysis': analysis_result,
                'ai_score': score
            },
            synchronize_session='evaluate'
        )
        
        # Commit des changements
        db.session.commit()
        
        # Rafraîchir l'objet pour obtenir les dernières valeurs
        application = Application.query.get(application_id)
        
        return jsonify({
            'message': 'Analyse du CV effectuée avec succès',
            'ai_analysis': application.ai_analysis,
            'ai_score': application.ai_score
        }), 200
    except Exception as e:
        return jsonify({'message': f'Erreur lors de l\'analyse du CV: {str(e)}'}), 500
