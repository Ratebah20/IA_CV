from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt
from app import db
from sqlalchemy.sql import func

class Role(db.Model):
    """Modèle pour les rôles utilisateur"""
    __tablename__ = 'Role'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    # Relation avec User
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    """Modèle pour les utilisateurs"""
    __tablename__ = 'User'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('Role.id'), nullable=False)
    department = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, 
                          server_default=func.getdate(),
                          server_onupdate=func.getdate(),
                          nullable=False)
    
    # Relation avec InterviewRequest
    interview_requests = db.relationship('InterviewRequest', backref='requester', lazy='dynamic', overlaps="managed_interview_requests,manager")
    
    def set_password(self, password):
        """Définit le mot de passe hashé de l'utilisateur"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Vérifie si le mot de passe fourni correspond au hash stocké"""
        # Vérifier si c'est un hash bcrypt (commence par $2b$)
        if self.password_hash.startswith('$2b$'):
            # Utiliser bcrypt pour vérifier
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        else:
            # Utiliser la méthode standard de Werkzeug
            return check_password_hash(self.password_hash, password)
    
    def is_hr(self):
        """Vérifie si l'utilisateur a le rôle RH"""
        return self.role_id == 1  # 1 = RH
    
    def is_manager(self):
        """Vérifie si l'utilisateur a le rôle Manager"""
        return self.role_id == 2  # 2 = MANAGER
    
    def __repr__(self):
        return f'<User {self.username}>'


class InterviewRequest(db.Model):
    """Modèle pour les demandes d'entretien"""
    __tablename__ = 'InterviewRequest'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('Application.id'), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)
    requested_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, APPROVED, REFUSED, COMPLETED
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    application = db.relationship('Application', backref='interview_requests')
    manager = db.relationship('User', backref='managed_interview_requests', overlaps="interview_requests,requester")
    
    def __repr__(self):
        return f'<InterviewRequest {self.id} for Application {self.application_id}>'
