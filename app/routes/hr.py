from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, abort
from app.models.models import JobPosition, Application, ApplicationStatus, Candidate
from app.models.auth_models import User
from app import db
from app.forms import JobPositionForm, HrLoginForm
from app.utils.ai_analysis import analyze_cv
import os

bp = Blueprint('hr', __name__, url_prefix='/hr')

# Décorateur pour vérifier si l'accès RH est autorisé
def hr_login_required(view_function):
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        if not current_user.is_authenticated or not current_user.is_hr():
            flash('Vous devez vous connecter en tant que RH pour accéder à cette zone.', 'warning')
            return redirect(url_for('auth.login'))
        return view_function(*args, **kwargs)
    decorated_function.__name__ = view_function.__name__
    return decorated_function

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Redirection vers le nouveau système d'authentification"""
    flash("Le système d'authentification a été mis à jour. Veuillez utiliser le nouveau système de connexion.", 'info')
    return redirect(url_for('auth.login'))

@bp.route('/logout')
def logout():
    """Redirection vers le nouveau système de déconnexion"""
    flash("Le système d'authentification a été mis à jour. Veuillez utiliser le nouveau système de déconnexion.", 'info')
    return redirect(url_for('auth.logout'))

@bp.route('/dashboard')
@hr_login_required
def dashboard():
    """Tableau de bord RH"""
    # Récupérer les statistiques
    job_count = JobPosition.query.count()
    application_count = Application.query.count()
    
    # Récupérer les dernières candidatures
    recent_applications = Application.query.order_by(Application.created_at.desc()).limit(5).all()
    
    return render_template('hr/dashboard.html', 
                          job_count=job_count,
                          application_count=application_count,
                          recent_applications=recent_applications)

@bp.route('/actions')
@hr_login_required
def actions():
    """Page d'actions RH"""
    return render_template('hr/actions.html')

@bp.route('/job_positions')
@hr_login_required
def job_positions():
    """Liste des offres d'emploi"""
    jobs = JobPosition.query.all()
    return render_template('hr/job_positions.html', jobs=jobs)

@bp.route('/job/add', methods=['GET', 'POST'])
@hr_login_required
def add_job():
    """Ajout d'une nouvelle offre d'emploi"""
    form = JobPositionForm()
    
    # Récupérer les départements existants pour le menu déroulant
    departments = db.session.query(User.department).filter(User.department.isnot(None)).distinct().all()
    department_list = [dept[0] for dept in departments]
    
    # Ajouter une option vide pour les postes sans département spécifique
    form.department.choices = [(d, d) for d in sorted(department_list)] + [('', 'Aucun département')]
    
    if form.validate_on_submit():
        job = JobPosition(
            title=form.title.data,
            description=form.description.data,
            requirements=form.requirements.data,
            department=form.department.data,
            is_active=form.is_active.data
        )
        
        db.session.add(job)
        db.session.commit()
        
        flash('L\'offre d\'emploi a été créée avec succès !', 'success')
        return redirect(url_for('hr.job_positions'))
    
    return render_template('hr/job_form.html', form=form, title="Ajouter une offre d'emploi")

@bp.route('/job/edit/<int:job_id>', methods=['GET', 'POST'])
@hr_login_required
def edit_job(job_id):
    """Modification d'une offre d'emploi"""
    # Récupération de l'objet pour l'affichage initial et les valeurs par défaut
    job = JobPosition.query.get_or_404(job_id)
    form = JobPositionForm()
    
    # Récupérer les départements existants pour le menu déroulant
    departments = db.session.query(User.department).filter(User.department.isnot(None)).distinct().all()
    department_list = [dept[0] for dept in departments]
    
    # Ajouter le département actuel du poste s'il n'est pas dans la liste
    if job.department and job.department not in department_list:
        department_list.append(job.department)
    
    # Ajouter une option vide pour les postes sans département spécifique
    form.department.choices = [(d, d) for d in sorted(department_list)] + [('', 'Aucun département')]
    
    if form.validate_on_submit():
        try:
            # Utilisation de l'approche bulk update avec synchronize_session='evaluate'
            # Cette option permet de contourner le problème de comptage de lignes
            # lorsque le trigger SQL Server renvoie -1 au lieu de 1
            db.session.query(JobPosition).filter_by(id=job_id).update(
                {
                    'title': form.title.data,
                    'description': form.description.data,
                    'requirements': form.requirements.data,
                    'department': form.department.data,
                    'is_active': form.is_active.data
                },
                synchronize_session='evaluate'  # Option clé pour éviter StaleDataError
            )
            
            # Commit des changements
            db.session.commit()
            
            # Rafraîchir l'objet pour obtenir les dernières valeurs depuis la base de données
            # y compris updated_at mis à jour par le trigger SQL Server
            db.session.refresh(job)
            
            flash('L\'offre d\'emploi a été mise à jour avec succès !', 'success')
            return redirect(url_for('hr.job_positions'))
        except Exception as e:
            # Log de l'erreur pour le débogage
            current_app.logger.error(f"Erreur lors de la mise à jour de l'offre d'emploi: {str(e)}")
            flash(f"Une erreur est survenue: {str(e)}", 'danger')
            
    elif request.method == 'GET':
        form.title.data = job.title
        form.description.data = job.description
        form.requirements.data = job.requirements
        form.department.data = job.department
        form.is_active.data = job.is_active
    
    return render_template('hr/job_form.html', form=form, title="Modifier l'offre d'emploi")

@bp.route('/applications')
@hr_login_required
def applications():
    """Liste de toutes les candidatures"""
    job_id = request.args.get('job_id', type=int)
    status = request.args.get('status')
    
    # Filtrage des candidatures
    query = Application.query
    
    if job_id:
        query = query.filter_by(job_position_id=job_id)
    
    if status and hasattr(ApplicationStatus, status.upper()):
        status_enum = getattr(ApplicationStatus, status.upper())
        query = query.filter_by(status=status_enum)
    
    applications = query.all()
    jobs = JobPosition.query.all()
    
    # Création d'une liste des statuts pour le template
    statuses = [
        {'id': ApplicationStatus.SUBMITTED, 'name': 'submitted', 'display_name': 'Soumise'},
        {'id': ApplicationStatus.UNDER_REVIEW, 'name': 'under_review', 'display_name': 'En cours d\'analyse'},
        {'id': ApplicationStatus.INTERVIEW, 'name': 'interview', 'display_name': 'Entretien'},
        {'id': ApplicationStatus.REJECTED, 'name': 'rejected', 'display_name': 'Rejetée'},
        {'id': ApplicationStatus.ACCEPTED, 'name': 'accepted', 'display_name': 'Acceptée'}
    ]
    
    return render_template('hr/applications.html', 
                          applications=applications, 
                          jobs=jobs,
                          ApplicationStatus=ApplicationStatus,
                          statuses=statuses,
                          current_job_id=job_id,
                          current_status=status)

@bp.route('/application/<int:application_id>')
@hr_login_required
def view_application(application_id):
    """Affichage du détail d'une candidature"""
    application = Application.query.get_or_404(application_id)
    candidate = Candidate.query.get(application.candidate_id)
    
    # Chemin du CV
    cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], application.cv_filename)
    
    # Création d'une liste des statuts pour le template
    statuses = [
        {'id': ApplicationStatus.SUBMITTED, 'name': 'submitted', 'display_name': 'Soumise'},
        {'id': ApplicationStatus.UNDER_REVIEW, 'name': 'under_review', 'display_name': 'En cours d\'analyse'},
        {'id': ApplicationStatus.INTERVIEW, 'name': 'interview', 'display_name': 'Entretien'},
        {'id': ApplicationStatus.REJECTED, 'name': 'rejected', 'display_name': 'Rejetée'},
        {'id': ApplicationStatus.ACCEPTED, 'name': 'accepted', 'display_name': 'Acceptée'}
    ]
    
    return render_template('hr/application_detail.html', 
                          application=application,
                          candidate=candidate,
                          ApplicationStatus=ApplicationStatus,
                          statuses=statuses)

@bp.route('/application/<int:application_id>/update_status', methods=['POST'])
@hr_login_required
def update_application_status(application_id):
    """Mise à jour du statut d'une candidature"""
    application = Application.query.get_or_404(application_id)
    
    new_status = request.form.get('status')
    if new_status and hasattr(ApplicationStatus, new_status.upper()):
        status_enum = getattr(ApplicationStatus, new_status.upper())
        
        try:
            # Utilisation de l'approche bulk update pour éviter les erreurs StaleDataError
            db.session.query(Application).filter_by(id=application_id).update(
                {'status_id': status_enum},  # Mise à jour de status_id au lieu de status
                synchronize_session='evaluate'
            )
            
            # Commit des changements
            db.session.commit()
            
            # Rafraîchir l'objet pour obtenir les dernières valeurs
            db.session.refresh(application)
            
            flash('Le statut de la candidature a été mis à jour.', 'success')
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la mise à jour du statut: {str(e)}")
            flash(f"Erreur lors de la mise à jour du statut: {str(e)}", 'danger')
    else:
        flash('Statut invalide.', 'warning')
    
    return redirect(url_for('hr.view_application', application_id=application_id))

@bp.route('/application/<int:application_id>/analyze', methods=['POST'])
@hr_login_required
def analyze_application(application_id):
    """Analyse d'une candidature par l'IA"""
    application = Application.query.get_or_404(application_id)
    job = JobPosition.query.get(application.job_position_id)
    
    # Chemin du CV
    cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], application.cv_filename)
    
    # Vérifier que le fichier CV existe
    if not os.path.exists(cv_path):
        flash(f'Erreur: Le fichier CV n\'a pas été trouvé à l\'emplacement {cv_path}', 'danger')
        return redirect(url_for('hr.view_application', application_id=application_id))
    
    try:
        # Appel à la fonction d'analyse IA
        analysis_result, score = analyze_cv(cv_path, job.description, job.requirements)
        
        # Mise à jour des résultats de l'analyse en utilisant l'approche bulk update
        # pour éviter l'erreur StaleDataError
        db.session.query(Application).filter_by(id=application_id).update(
            {
                'ai_analysis': analysis_result,
                'ai_score': score
            },
            synchronize_session='evaluate'  # Option clé pour éviter StaleDataError
        )
        
        # Commit des changements
        db.session.commit()
        
        # Rafraîchir l'objet pour obtenir les dernières valeurs depuis la base de données
        db.session.refresh(application)
        
        flash('L\'analyse du CV a été effectuée avec succès.', 'success')
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'analyse du CV: {str(e)}")
        flash(f'Erreur lors de l\'analyse du CV: {str(e)}', 'danger')
    
    return redirect(url_for('hr.view_application', application_id=application_id))
