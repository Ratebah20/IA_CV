from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

# Initialisation de l'extension SQLAlchemy
db = SQLAlchemy()

class Candidate(db.Model):
    """Modèle pour les informations des candidats"""
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    applications = db.relationship('Application', backref='candidate', lazy='dynamic')
    
    def __repr__(self):
        return f'<Candidate {self.first_name} {self.last_name}>'

class JobPosition(db.Model):
    """Modèle pour les offres d'emploi"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    applications = db.relationship('Application', backref='job_position', lazy='dynamic')
    
    def __repr__(self):
        return f'<JobPosition {self.title}>'

class ApplicationStatus(enum.Enum):
    """Statuts possibles pour une candidature"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    ACCEPTED = "accepted"

class Application(db.Model):
    """Modèle pour les candidatures"""
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    job_position_id = db.Column(db.Integer, db.ForeignKey('job_position.id'), nullable=False)
    cv_filename = db.Column(db.String(255), nullable=False)
    cover_letter = db.Column(db.Text)
    status = db.Column(db.Enum(ApplicationStatus), default=ApplicationStatus.SUBMITTED)
    ai_analysis = db.Column(db.Text)
    ai_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Application {self.id}>'
