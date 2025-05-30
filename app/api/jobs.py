from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db
from ..models.auth_models import User
from ..models.models import JobPosition, Department, Application
from . import api_bp

@api_bp.route('/jobs', methods=['GET'])
def get_jobs():
    """Récupérer toutes les offres d'emploi (actives et inactives)"""
    jobs = JobPosition.query.all()
    
    result = []
    for job in jobs:
        # Récupérer le nom du département à partir de l'ID
        department_name = "Non spécifié"
        if job.department_id:
            department = Department.query.get(job.department_id)
            if department:
                department_name = department.name
        
        # Compter le nombre de candidatures pour cette offre
        application_count = Application.query.filter_by(job_position_id=job.id).count()
        
        result.append({
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'requirements': job.requirements,
            'department_id': job.department_id,
            'department_name': department_name,
            'created_at': job.created_at.strftime('%Y-%m-%d'),
            'is_active': job.is_active,
            'application_count': application_count  # Ajouter le nombre de candidatures
        })
    
    return jsonify(result), 200

@api_bp.route('/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Récupérer une offre d'emploi spécifique"""
    job = JobPosition.query.get_or_404(job_id)
    
    # Récupérer le nom du département à partir de l'ID
    department_name = "Non spécifié"
    if job.department_id:
        department = Department.query.get(job.department_id)
        if department:
            department_name = department.name
    
    # Compter le nombre de candidatures pour cette offre
    application_count = Application.query.filter_by(job_position_id=job.id).count()
    
    return jsonify({
        'id': job.id,
        'title': job.title,
        'description': job.description,
        'requirements': job.requirements,
        'department_id': job.department_id, 
        'department_name': department_name,
        'created_at': job.created_at.strftime('%Y-%m-%d'),
        'is_active': job.is_active,
        'application_count': application_count  # Ajouter le nombre de candidatures
    }), 200

@api_bp.route('/jobs', methods=['POST'])
@jwt_required()
def create_job():
    """Créer une nouvelle offre d'emploi (réservé aux RH)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_hr():
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('description') or not data.get('department_id'):
        return jsonify({'message': 'Données manquantes (titre, description, et department_id sont requis)'}), 400
    
    # Vérifier que le département existe
    department = Department.query.get(data.get('department_id'))
    if not department:
        return jsonify({'message': 'Le département spécifié n\'existe pas'}), 404
    
    new_job = JobPosition(
        title=data.get('title'),
        description=data.get('description'),
        requirements=data.get('requirements', ''),
        department_id=data.get('department_id'),
        is_active=data.get('is_active', True)
    )
    
    db.session.add(new_job)
    db.session.commit()
    
    return jsonify({
        'message': 'Offre d\'emploi créée avec succès',
        'id': new_job.id
    }), 201

@api_bp.route('/jobs/<int:job_id>', methods=['PUT'])
@jwt_required()
def update_job(job_id):
    """Mettre à jour une offre d'emploi (réservé aux RH)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_hr():
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    job = JobPosition.query.get_or_404(job_id)
    data = request.get_json()
    
    try:
        # Préparer les données à mettre à jour
        update_data = {}
        if data.get('title'):
            update_data['title'] = data.get('title')
        if data.get('description'):
            update_data['description'] = data.get('description')
        if data.get('requirements') is not None:
            update_data['requirements'] = data.get('requirements')
        if data.get('department_id') is not None:
            # Vérifier que le département existe
            department = Department.query.get(data.get('department_id'))
            if not department:
                return jsonify({'message': 'Le département spécifié n\'existe pas'}), 404
            update_data['department_id'] = data.get('department_id')
        if data.get('is_active') is not None:
            update_data['is_active'] = data.get('is_active')
        
        # Utiliser une requête de mise à jour directe plutôt que de modifier l'objet
        # Cela évite les problèmes de concurrence et de StaleDataError
        if update_data:
            db.session.execute(
                db.update(JobPosition)
                .where(JobPosition.id == job_id)
                .values(**update_data)
            )
            db.session.commit()
            
            # Rafraîchir l'objet pour obtenir les dernières valeurs
            db.session.refresh(job)
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Erreur lors de la mise à jour de l\'offre: {str(e)}'}), 500
    
    return jsonify({'message': 'Offre d\'emploi mise à jour avec succès'}), 200

@api_bp.route('/jobs/<int:job_id>', methods=['DELETE'])
@jwt_required()
def delete_job(job_id):
    """Supprimer une offre d'emploi (réservé aux RH)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_hr():
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    job = JobPosition.query.get_or_404(job_id)
    
    db.session.delete(job)
    db.session.commit()
    
    return jsonify({'message': 'Offre d\'emploi supprimée avec succès'}), 200

@api_bp.route('/jobs/department/<int:department_id>', methods=['GET'])
def get_jobs_by_department(department_id):
    """Récupérer les offres d'emploi par département"""
    # Vérifier que le département existe
    department = Department.query.get_or_404(department_id)
    jobs = JobPosition.query.filter_by(department_id=department_id, is_active=True).all()
    
    result = []
    for job in jobs:
        # Compter le nombre de candidatures pour cette offre
        application_count = Application.query.filter_by(job_position_id=job.id).count()
        
        result.append({
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'requirements': job.requirements,
            'department_id': job.department_id,
            'department_name': department.name,  # Utiliser le nom du département récupéré précédemment
            'created_at': job.created_at.strftime('%Y-%m-%d'),
            'is_active': job.is_active,
            'application_count': application_count  # Ajouter le nombre de candidatures
        })
    
    return jsonify(result), 200
