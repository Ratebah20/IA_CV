from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from app.models.models import Candidate, JobPosition, Application, ApplicationStatus
from app import db
from app.forms import ApplicationForm
from werkzeug.utils import secure_filename
import os
import uuid

bp = Blueprint('candidate', __name__, url_prefix='/candidate')

@bp.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    """Formulaire pour postuler à une offre d'emploi"""
    job = JobPosition.query.get_or_404(job_id)
    
    if not job.is_active:
        flash('Ce poste n\'est plus disponible.', 'warning')
        return redirect(url_for('main.index'))
    
    form = ApplicationForm()
    if form.validate_on_submit():
        # Créer d'abord le candidat
        candidate = Candidate(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data
        )
        db.session.add(candidate)
        db.session.flush()  # Pour obtenir l'ID du candidat avant le commit final
        
        # Gestion du téléchargement du CV
        cv_file = form.cv.data
        if cv_file:
            filename = secure_filename(cv_file.filename)
            # Utilisation d'un UUID pour éviter les collisions de noms de fichiers
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            cv_file.save(cv_path)
            
            # Création de la candidature
            application = Application(
                candidate_id=candidate.id,
                job_position_id=job.id,
                cv_filename=unique_filename,
                cover_letter=form.cover_letter.data,
                status=ApplicationStatus.SUBMITTED
            )
            
            db.session.add(application)
            db.session.commit()
            
            flash('Votre candidature a été soumise avec succès!', 'success')
            # Stocker l'ID de candidature dans la session pour la page de confirmation
            session['last_application_id'] = application.id
            return redirect(url_for('candidate.confirmation'))
    
    return render_template('candidate/apply.html', job=job, form=form)

@bp.route('/confirmation')
def confirmation():
    """Page de confirmation après soumission d'une candidature"""
    application_id = session.get('last_application_id')
    if not application_id:
        return redirect(url_for('main.index'))
    
    application = Application.query.get(application_id)
    job = None
    if application:
        job = JobPosition.query.get(application.job_position_id)
    
    # Effacer l'ID de la session
    session.pop('last_application_id', None)
    
    return render_template('candidate/confirmation.html', application=application, job=job)
