from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db
from ..models.auth_models import User
from ..models.models import Department
from . import api_bp

@api_bp.route('/departments', methods=['GET'])
def get_departments():
    """Récupérer tous les départements"""
    departments = Department.query.all()
    
    result = []
    for dept in departments:
        result.append({
            'id': dept.id,
            'name': dept.name,
            'description': dept.description
        })
    
    return jsonify(result), 200

@api_bp.route('/departments/<int:department_id>', methods=['GET'])
def get_department(department_id):
    """Récupérer un département spécifique"""
    dept = Department.query.get_or_404(department_id)
    
    return jsonify({
        'id': dept.id,
        'name': dept.name,
        'description': dept.description
    }), 200

@api_bp.route('/departments', methods=['POST'])
@jwt_required()
def create_department():
    """Créer un nouveau département (réservé aux RH)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_hr():
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'message': 'Nom du département requis'}), 400
    
    # Vérifier si un département avec ce nom existe déjà
    existing_dept = Department.query.filter_by(name=data.get('name')).first()
    if existing_dept:
        return jsonify({'message': 'Un département avec ce nom existe déjà'}), 409
    
    new_dept = Department(
        name=data.get('name'),
        description=data.get('description', '')
    )
    
    db.session.add(new_dept)
    db.session.commit()
    
    return jsonify({
        'message': 'Département créé avec succès',
        'id': new_dept.id
    }), 201

@api_bp.route('/departments/<int:department_id>', methods=['PUT'])
@jwt_required()
def update_department(department_id):
    """Mettre à jour un département (réservé aux RH)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_hr():
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    dept = Department.query.get_or_404(department_id)
    data = request.get_json()
    
    try:
        # Préparer les données à mettre à jour
        update_data = {}
        if data.get('name'):
            # Vérifier si un autre département utilise déjà ce nom
            existing = Department.query.filter(Department.name == data.get('name'), Department.id != department_id).first()
            if existing:
                return jsonify({'message': 'Un département avec ce nom existe déjà'}), 409
            update_data['name'] = data.get('name')
        if data.get('description') is not None:
            update_data['description'] = data.get('description')
        
        # Utiliser une requête de mise à jour directe
        if update_data:
            db.session.execute(
                db.update(Department)
                .where(Department.id == department_id)
                .values(**update_data)
            )
            db.session.commit()
            
            # Rafraîchir l'objet pour obtenir les dernières valeurs
            db.session.refresh(dept)
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Erreur lors de la mise à jour du département: {str(e)}'}), 500
    
    return jsonify({'message': 'Département mis à jour avec succès'}), 200

@api_bp.route('/departments/seed', methods=['POST'])
@jwt_required()
def seed_departments():
    """Initialiser les départements standards (réservé aux RH)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_hr():
        return jsonify({'message': 'Accès non autorisé'}), 403
    
    # Liste des départements standards
    standard_departments = [
        {'name': 'Direction Générale', 'description': 'Direction et stratégie de l\'entreprise'},
        {'name': 'Ressources Humaines', 'description': 'Gestion du personnel et recrutement'},
        {'name': 'Finance et Comptabilité', 'description': 'Gestion financière et comptable'},
        {'name': 'Marketing', 'description': 'Stratégie marketing et communication'},
        {'name': 'Ventes', 'description': 'Équipe commerciale et relation client'},
        {'name': 'Informatique', 'description': 'Développement et maintenance des systèmes d\'information'},
        {'name': 'Recherche et Développement', 'description': 'Innovation et développement produit'},
        {'name': 'Production', 'description': 'Fabrication et assemblage'},
        {'name': 'Logistique', 'description': 'Gestion des stocks et distribution'},
        {'name': 'Service Client', 'description': 'Support et assistance client'},
        {'name': 'Juridique', 'description': 'Conseil juridique et conformité'},
        {'name': 'Qualité', 'description': 'Contrôle qualité et amélioration continue'}
    ]
    
    created_count = 0
    for dept_data in standard_departments:
        # Vérifier si le département existe déjà
        existing = Department.query.filter_by(name=dept_data['name']).first()
        if not existing:
            # Créer le département s'il n'existe pas
            new_dept = Department(**dept_data)
            db.session.add(new_dept)
            created_count += 1
    
    db.session.commit()
    
    return jsonify({
        'message': f'{created_count} départements ont été créés',
        'total_departments': Department.query.count()
    }), 200
