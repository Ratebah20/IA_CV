from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from app.models.models import Application, Candidate, JobPosition
from app.models.auth_models import InterviewRequest, User
from app import db
from app.routes.hr import hr_login_required
from datetime import datetime

bp = Blueprint('hr_interview', __name__, url_prefix='/hr/interviews')

@bp.route('/')
@hr_login_required
def interview_requests():
    """Liste des demandes d'entretien"""
    # Récupérer toutes les demandes d'entretien
    requests = InterviewRequest.query.all()
    
    # Préparer les données pour l'affichage
    request_data = []
    for req in requests:
        application = Application.query.get(req.application_id)
        candidate = Candidate.query.get(application.candidate_id)
        job = JobPosition.query.get(application.job_position_id)
        manager = User.query.get(req.manager_id)
        
        request_data.append({
            'id': req.id,
            'candidate_name': f"{candidate.first_name} {candidate.last_name}",
            'job_title': job.title,
            'department': job.department,
            'manager_name': manager.username,
            'requested_date': req.requested_date,
            'status': req.status,
            'created_at': req.created_at,
            'application_id': application.id
        })
    
    return render_template('hr/interview_requests.html',
                          title='Demandes d\'entretien',
                          requests=request_data)

@bp.route('/<int:request_id>')
@hr_login_required
def view_interview_request(request_id):
    """Voir les détails d'une demande d'entretien"""
    interview_request = InterviewRequest.query.get_or_404(request_id)
    application = Application.query.get(interview_request.application_id)
    candidate = Candidate.query.get(application.candidate_id)
    job = JobPosition.query.get(application.job_position_id)
    manager = User.query.get(interview_request.manager_id)
    
    return render_template('hr/interview_request_detail.html',
                          title=f'Demande d\'entretien pour {candidate.first_name} {candidate.last_name}',
                          request=interview_request,
                          application=application,
                          candidate=candidate,
                          job=job,
                          manager=manager)

@bp.route('/<int:request_id>/update_status', methods=['POST'])
@hr_login_required
def update_interview_status(request_id):
    """Mise à jour du statut d'une demande d'entretien"""
    interview_request = InterviewRequest.query.get_or_404(request_id)
    
    new_status = request.form.get('status')
    if new_status in ['APPROVED', 'REFUSED', 'COMPLETED']:
        try:
            # Utilisation de l'approche bulk update pour éviter les erreurs StaleDataError
            db.session.query(InterviewRequest).filter_by(id=request_id).update(
                {'status': new_status},
                synchronize_session='evaluate'
            )
            
            # Si approuvé, mettre à jour le statut de la candidature à "INTERVIEW"
            if new_status == 'APPROVED':
                application_id = interview_request.application_id
                db.session.query(Application).filter_by(id=application_id).update(
                    {'status_id': 3},  # 3 = INTERVIEW dans ApplicationStatus
                    synchronize_session='evaluate'
                )
            
            # Commit des changements
            db.session.commit()
            
            # Rafraîchir l'objet pour obtenir les dernières valeurs
            db.session.refresh(interview_request)
            
            flash('Le statut de la demande d\'entretien a été mis à jour.', 'success')
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la mise à jour du statut: {str(e)}")
            flash(f"Erreur lors de la mise à jour du statut: {str(e)}", 'danger')
    else:
        flash('Statut invalide.', 'warning')
    
    return redirect(url_for('hr_interview.view_interview_request', request_id=request_id))

@bp.route('/<int:request_id>/schedule', methods=['POST'])
@hr_login_required
def schedule_interview(request_id):
    """Planifier un entretien"""
    interview_request = InterviewRequest.query.get_or_404(request_id)
    
    interview_date = request.form.get('interview_date')
    interview_time = request.form.get('interview_time')
    location = request.form.get('location')
    notes = request.form.get('notes')
    
    if interview_date and interview_time:
        try:
            # Convertir la date et l'heure en datetime
            interview_datetime = datetime.strptime(f"{interview_date} {interview_time}", "%Y-%m-%d %H:%M")
            
            # Mettre à jour la demande d'entretien
            db.session.query(InterviewRequest).filter_by(id=request_id).update(
                {
                    'status': 'APPROVED',
                    'requested_date': interview_datetime,
                    'comments': f"Lieu: {location}\nNotes: {notes}\n\n{interview_request.comments}"
                },
                synchronize_session='evaluate'
            )
            
            # Mettre à jour le statut de la candidature
            application_id = interview_request.application_id
            db.session.query(Application).filter_by(id=application_id).update(
                {'status_id': 3},  # 3 = INTERVIEW dans ApplicationStatus
                synchronize_session='evaluate'
            )
            
            # Commit des changements
            db.session.commit()
            
            flash('L\'entretien a été planifié avec succès.', 'success')
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la planification de l'entretien: {str(e)}")
            flash(f"Erreur lors de la planification de l'entretien: {str(e)}", 'danger')
    else:
        flash('Veuillez fournir une date et une heure pour l\'entretien.', 'warning')
    
    return redirect(url_for('hr_interview.view_interview_request', request_id=request_id))
