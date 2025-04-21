from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.manager import bp
from app.models.models import JobPosition, Application, Candidate
from app.models.auth_models import InterviewRequest
from app.auth.routes import manager_required
from app.manager.forms import InterviewRequestForm
import os

@bp.route('/dashboard')
@login_required
@manager_required
def dashboard():
    """Tableau de bord du manager"""
    # Récupérer les postes du département du manager
    department_jobs = JobPosition.query.filter_by(department=current_user.department).all()
    
    # Récupérer les candidatures pour ces postes
    job_ids = [job.id for job in department_jobs]
    applications = Application.query.filter(Application.job_position_id.in_(job_ids)).all()
    
    # Récupérer les demandes d'entretien du manager
    interview_requests = InterviewRequest.query.filter_by(manager_id=current_user.id).all()
    
    return render_template('manager/dashboard.html', 
                          title='Tableau de bord Manager',
                          jobs=department_jobs,
                          applications=applications,
                          interview_requests=interview_requests)

@bp.route('/applications')
@login_required
@manager_required
def applications():
    """Liste des candidatures pour le département du manager"""
    # Récupérer les postes du département du manager
    department_jobs = JobPosition.query.filter_by(department=current_user.department).all()
    job_ids = [job.id for job in department_jobs]
    
    # Récupérer les candidatures pour ces postes
    applications = Application.query.filter(Application.job_position_id.in_(job_ids)).all()
    
    # Préparer les données pour l'affichage
    application_data = []
    for app in applications:
        job = JobPosition.query.get(app.job_position_id)
        candidate = Candidate.query.get(app.candidate_id)
        application_data.append({
            'id': app.id,
            'candidate_name': f"{candidate.first_name} {candidate.last_name}",
            'job_title': job.title,
            'status': app.status,
            'created_at': app.created_at
        })
    
    return render_template('manager/applications.html', 
                          title='Candidatures',
                          applications=application_data)

@bp.route('/application/<int:application_id>')
@login_required
@manager_required
def view_application(application_id):
    """Voir les détails d'une candidature"""
    application = Application.query.get_or_404(application_id)
    job = JobPosition.query.get(application.job_position_id)
    
    # Vérifier que le job appartient au département du manager
    if job.department != current_user.department:
        flash('Vous n\'avez pas accès à cette candidature.', 'danger')
        return redirect(url_for('manager.applications'))
    
    candidate = Candidate.query.get(application.candidate_id)
    
    # Vérifier si une demande d'entretien existe déjà
    existing_request = InterviewRequest.query.filter_by(
        application_id=application_id,
        manager_id=current_user.id
    ).first()
    
    # Formulaire de demande d'entretien
    form = InterviewRequestForm()
    
    # Chemin du CV
    cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], application.cv_filename)
    cv_exists = os.path.exists(cv_path)
    
    return render_template('manager/application_detail.html',
                          title=f'Candidature de {candidate.first_name} {candidate.last_name}',
                          application=application,
                          candidate=candidate,
                          job=job,
                          form=form,
                          existing_request=existing_request,
                          cv_exists=cv_exists)

@bp.route('/application/<int:application_id>/request_interview', methods=['POST'])
@login_required
@manager_required
def request_interview(application_id):
    """Demander un entretien pour une candidature"""
    application = Application.query.get_or_404(application_id)
    job = JobPosition.query.get(application.job_position_id)
    
    # Vérifier que le job appartient au département du manager
    if job.department != current_user.department:
        flash('Vous n\'avez pas accès à cette candidature.', 'danger')
        return redirect(url_for('manager.applications'))
    
    # Vérifier si une demande d'entretien existe déjà
    existing_request = InterviewRequest.query.filter_by(
        application_id=application_id,
        manager_id=current_user.id
    ).first()
    
    if existing_request:
        flash('Vous avez déjà fait une demande d\'entretien pour cette candidature.', 'warning')
        return redirect(url_for('manager.view_application', application_id=application_id))
    
    form = InterviewRequestForm()
    if form.validate_on_submit():
        interview_request = InterviewRequest(
            application_id=application_id,
            manager_id=current_user.id,
            requested_date=form.requested_date.data,
            comments=form.comments.data,
            status='PENDING'
        )
        
        db.session.add(interview_request)
        db.session.commit()
        
        flash('Votre demande d\'entretien a été envoyée aux RH.', 'success')
    
    return redirect(url_for('manager.view_application', application_id=application_id))

@bp.route('/interview_requests')
@login_required
@manager_required
def interview_requests():
    """Liste des demandes d'entretien du manager"""
    requests = InterviewRequest.query.filter_by(manager_id=current_user.id).all()
    
    # Préparer les données pour l'affichage
    request_data = []
    for req in requests:
        application = Application.query.get(req.application_id)
        candidate = Candidate.query.get(application.candidate_id)
        job = JobPosition.query.get(application.job_position_id)
        
        request_data.append({
            'id': req.id,
            'application_id': req.application_id,
            'candidate_name': f"{candidate.first_name} {candidate.last_name}",
            'job_title': job.title,
            'requested_date': req.requested_date,
            'status': req.status,
            'created_at': req.created_at
        })
    
    return render_template('manager/interview_requests.html',
                          title='Demandes d\'entretien',
                          requests=request_data)
