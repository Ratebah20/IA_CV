from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_
from app.models.models import JobPosition, Application, Candidate, InterviewRequest
from app.forms.interview_forms import InterviewRequestForm
from app import db
from datetime import datetime
import os

manager = Blueprint('manager', __name__)

def manager_required(view_function):
    """Décorateur pour restreindre l'accès aux managers uniquement"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_manager():
            flash('Vous devez vous connecter en tant que manager pour accéder à cette zone.', 'warning')
            return redirect(url_for('auth.login'))
        return view_function(*args, **kwargs)
    return decorated_function

@manager.route('/dashboard')
@login_required
@manager_required
def dashboard():
    """Tableau de bord du manager"""
    # Récupérer les offres d'emploi du département du manager
    jobs = JobPosition.query.filter_by(department=current_user.department).all()
    
    # Récupérer les candidatures pour ces offres
    job_ids = [job.id for job in jobs]
    applications = Application.query.filter(Application.job_id.in_(job_ids)).all()
    
    # Récupérer les demandes d'entretien du manager
    interview_requests = InterviewRequest.query.filter_by(manager_id=current_user.id).all()
    
    # Statistiques
    total_jobs = len(jobs)
    total_applications = len(applications)
    pending_applications = sum(1 for app in applications if app.status in [1, 2])  # Soumise ou En cours d'examen
    interview_applications = sum(1 for app in applications if app.status == 3)  # Entretien
    
    return render_template('manager/dashboard.html', 
                          jobs=jobs,
                          applications=applications,
                          interview_requests=interview_requests,
                          total_jobs=total_jobs,
                          total_applications=total_applications,
                          pending_applications=pending_applications,
                          interview_applications=interview_applications)

@manager.route('/applications')
@login_required
@manager_required
def applications():
    """Liste des candidatures pour les offres du département du manager"""
    # Récupérer les offres d'emploi du département du manager
    jobs = JobPosition.query.filter_by(department=current_user.department).all()
    job_ids = [job.id for job in jobs]
    
    # Récupérer toutes les candidatures pour ces offres
    query = db.session.query(
        Application.id,
        Application.status,
        Application.created_at,
        Candidate.first_name,
        Candidate.last_name,
        JobPosition.title,
        JobPosition.department
    ).join(
        Candidate, Application.candidate_id == Candidate.id
    ).join(
        JobPosition, Application.job_id == JobPosition.id
    ).filter(
        Application.job_id.in_(job_ids)
    )
    
    # Construire une liste d'objets pour le template
    applications_list = []
    for app in query.all():
        applications_list.append({
            'id': app[0],
            'status': app[1],
            'created_at': app[2],
            'candidate_name': f"{app[3]} {app[4]}",
            'job_title': app[5],
            'department': app[6]
        })
    
    return render_template('manager/applications.html', applications=applications_list)

@manager.route('/application/<int:application_id>')
@login_required
@manager_required
def view_application(application_id):
    """Afficher les détails d'une candidature"""
    # Récupérer la candidature
    application = Application.query.get_or_404(application_id)
    
    # Vérifier que la candidature appartient au département du manager
    if application.job.department != current_user.department:
        flash('Vous n\'avez pas accès à cette candidature.', 'danger')
        return redirect(url_for('manager.applications'))
    
    # Récupérer le candidat et le poste
    candidate = Candidate.query.get(application.candidate_id)
    job = JobPosition.query.get(application.job_id)
    
    # Vérifier si le CV existe
    cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"cv_{application.id}.pdf")
    cv_exists = os.path.exists(cv_path)
    
    # Vérifier s'il existe déjà une demande d'entretien
    existing_request = InterviewRequest.query.filter_by(
        application_id=application_id,
        manager_id=current_user.id
    ).first()
    
    # Formulaire de demande d'entretien
    form = InterviewRequestForm()
    
    return render_template('manager/application_detail.html',
                          application=application,
                          candidate=candidate,
                          job=job,
                          cv_exists=cv_exists,
                          existing_request=existing_request,
                          form=form)

@manager.route('/application/<int:application_id>/request-interview', methods=['POST'])
@login_required
@manager_required
def request_interview(application_id):
    """Demander un entretien pour une candidature"""
    # Récupérer la candidature
    application = Application.query.get_or_404(application_id)
    
    # Vérifier que la candidature appartient au département du manager
    if application.job.department != current_user.department:
        flash('Vous n\'avez pas accès à cette candidature.', 'danger')
        return redirect(url_for('manager.applications'))
    
    # Vérifier s'il existe déjà une demande d'entretien
    existing_request = InterviewRequest.query.filter_by(
        application_id=application_id,
        manager_id=current_user.id
    ).first()
    
    if existing_request:
        flash('Vous avez déjà fait une demande d\'entretien pour cette candidature.', 'warning')
        return redirect(url_for('manager.view_application', application_id=application_id))
    
    # Traiter le formulaire
    form = InterviewRequestForm()
    if form.validate_on_submit():
        # Créer une nouvelle demande d'entretien
        interview_request = InterviewRequest(
            application_id=application_id,
            manager_id=current_user.id,
            requested_date=form.requested_date.data,
            comments=form.comments.data,
            status='PENDING',
            created_at=datetime.now()
        )
        
        # Mettre à jour le statut de la candidature
        application.status = 3  # Entretien
        
        # Enregistrer dans la base de données
        db.session.add(interview_request)
        db.session.commit()
        
        flash('Votre demande d\'entretien a été envoyée avec succès.', 'success')
        return redirect(url_for('manager.view_application', application_id=application_id))
    
    # En cas d'erreur de validation
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('manager.view_application', application_id=application_id))

@manager.route('/interview-requests')
@login_required
@manager_required
def interview_requests():
    """Liste des demandes d'entretien du manager"""
    # Récupérer toutes les demandes d'entretien du manager
    requests = InterviewRequest.query.filter_by(manager_id=current_user.id).all()
    
    return render_template('manager/interview_requests.html', requests=requests)
