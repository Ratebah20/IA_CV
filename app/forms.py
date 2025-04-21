from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, ValidationError
from flask_wtf.file import FileField, FileRequired, FileAllowed

class HrLoginForm(FlaskForm):
    """Formulaire de connexion simple pour la partie RH"""
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class ApplicationForm(FlaskForm):
    """Formulaire de candidature complet incluant les informations du candidat"""
    # Informations du candidat
    first_name = StringField('Prénom', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Nom', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Téléphone', validators=[Length(max=20)])
    
    # Documents de candidature
    cv = FileField('CV (PDF)', validators=[
        FileRequired(),
        FileAllowed(['pdf'], 'Les fichiers PDF uniquement sont acceptés')
    ])
    cover_letter = TextAreaField('Lettre de motivation (optionnelle)', validators=[Length(max=5000)])
    
    submit = SubmitField('Envoyer ma candidature')

class JobPositionForm(FlaskForm):
    """Formulaire pour les offres d'emploi"""
    title = StringField('Titre du poste', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description du poste', validators=[DataRequired()])
    requirements = TextAreaField('Exigences / Compétences requises')
    department = SelectField('Département', validators=[DataRequired()])
    is_active = BooleanField('Poste actif')
    submit = SubmitField('Enregistrer')
