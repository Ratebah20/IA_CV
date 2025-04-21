"""
Filtres personnalisés pour les templates Jinja2
"""
from app.models.models import Candidate, JobPosition, ApplicationStatus, Application
from app.models.auth_models import User

def init_app(app):
    """Initialise les filtres personnalisés pour l'application Flask"""
    
    @app.template_filter('get_candidate')
    def get_candidate(candidate_id):
        """Récupère un objet Candidate à partir de son ID"""
        return Candidate.query.get(candidate_id)
    
    @app.template_filter('get_job')
    def get_job(job_id):
        """Récupère un objet JobPosition à partir de son ID"""
        return JobPosition.query.get(job_id)
        
    @app.template_filter('get_application')
    def get_application(application_id):
        """Récupère un objet Application à partir de son ID"""
        return Application.query.get(application_id)
    
    @app.template_filter('get_user')
    def get_user(user_id):
        """Récupère un objet User à partir de son ID"""
        return User.query.get(user_id)
    
    @app.template_filter('get_status_name')
    def get_status_name(status_id):
        """Récupère le nom d'un statut à partir de son ID"""
        status_map = {
            ApplicationStatus.SUBMITTED: "Soumise",
            ApplicationStatus.UNDER_REVIEW: "En cours d'examen",
            ApplicationStatus.INTERVIEW: "Entretien",
            ApplicationStatus.REJECTED: "Rejetée",
            ApplicationStatus.ACCEPTED: "Acceptée"
        }
        return status_map.get(status_id, "Inconnu")
    
    @app.template_filter('nl2br')
    def nl2br(value):
        """Convertit les sauts de ligne en balises <br>"""
        if value:
            return value.replace('\n', '<br>')
        return ""
