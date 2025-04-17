from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from app.models.models import JobPosition, Application, ApplicationStatus, Candidate
from app import db
from app.forms import JobPositionForm, HrLoginForm
from app.utils.ai_analysis import analyze_cv
import os

bp = Blueprint('hr', __name__, url_prefix='/hr')

# Décorateur pour vérifier si l'accès RH est autorisé
def hr_login_required(view_function):
    def decorated_function(*args, **kwargs):
        if not session.get('hr_logged_in'):
            flash('Vous devez vous connecter pour accéder à cette zone.', 'warning')
            return redirect(url_for('hr.login'))
        return view_function(*args, **kwargs)
    decorated_function.__name__ = view_function.__name__
    return decorated_function

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion pour la partie RH"""
    if session.get('hr_logged_in'):
        return redirect(url_for('hr.dashboard'))
        
    form = HrLoginForm()
    if form.validate_on_submit():
        hr_password = current_app.config['HR_PASSWORD']
        if form.password.data == hr_password:
            session['hr_logged_in'] = True
            flash('Connexion réussie.', 'success')
            return redirect(url_for('hr.dashboard'))
        else:
            flash('Mot de passe incorrect', 'danger')
            
    return render_template('hr/login.html', form=form)

@bp.route('/logout')
def logout():
    """Déconnexion de la partie RH"""
    session.pop('hr_logged_in', None)
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@hr_login_required
def dashboard():
    """Tableau de bord RH"""
    # Récupérer les statistiques des candidatures
    total_applications = Application.query.count()
    new_applications = Application.query.filter_by(status=ApplicationStatus.SUBMITTED).count()
    job_positions = JobPosition.query.filter_by(is_active=True).count()
    
    return render_template('hr/dashboard.html', 
                          total_applications=total_applications,
                          new_applications=new_applications,
                          job_positions=job_positions)

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
    if form.validate_on_submit():
        job = JobPosition(
            title=form.title.data,
            description=form.description.data,
            requirements=form.requirements.data,
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
    job = JobPosition.query.get_or_404(job_id)
    form = JobPositionForm()
    
    if form.validate_on_submit():
        job.title = form.title.data
        job.description = form.description.data
        job.requirements = form.requirements.data
        job.is_active = form.is_active.data
        
        db.session.commit()
        
        flash('L\'offre d\'emploi a été mise à jour avec succès !', 'success')
        return redirect(url_for('hr.job_positions'))
    elif request.method == 'GET':
        form.title.data = job.title
        form.description.data = job.description
        form.requirements.data = job.requirements
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
    
    return render_template('hr/applications.html', 
                          applications=applications, 
                          jobs=jobs,
                          ApplicationStatus=ApplicationStatus,
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
    
    return render_template('hr/application_detail.html', 
                          application=application,
                          candidate=candidate,
                          ApplicationStatus=ApplicationStatus)

@bp.route('/application/<int:application_id>/update_status', methods=['POST'])
@hr_login_required
def update_application_status(application_id):
    """Mise à jour du statut d'une candidature"""
    application = Application.query.get_or_404(application_id)
    
    new_status = request.form.get('status')
    if new_status and hasattr(ApplicationStatus, new_status.upper()):
        status_enum = getattr(ApplicationStatus, new_status.upper())
        application.status = status_enum
        db.session.commit()
        flash('Le statut de la candidature a été mis à jour.', 'success')
    
    return redirect(url_for('hr.view_application', application_id=application_id))

@bp.route('/application/<int:application_id>/analyze', methods=['POST'])
@hr_login_required
def analyze_application(application_id):
    """Analyse d'une candidature par l'IA"""
    application = Application.query.get_or_404(application_id)
    job = JobPosition.query.get(application.job_position_id)
    
    # Chemin du CV
    cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], application.cv_filename)
    
    try:
        # Appel à la fonction d'analyse IA
        analysis_result, score = analyze_cv(cv_path, job.description, job.requirements)
        
        # Mise à jour des résultats de l'analyse
        application.ai_analysis = analysis_result
        application.ai_score = score
        db.session.commit()
        
        flash('L\'analyse du CV a été effectuée avec succès.', 'success')
    except Exception as e:
        flash(f'Erreur lors de l\'analyse du CV: {str(e)}', 'danger')
    
    return redirect(url_for('hr.view_application', application_id=application_id))
