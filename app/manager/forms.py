from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, DateTimeField
from wtforms.validators import DataRequired, Length
from datetime import datetime, timedelta

class InterviewRequestForm(FlaskForm):
    """Formulaire de demande d'entretien"""
    requested_date = DateTimeField('Date souhaitée', 
                                  format='%Y-%m-%dT%H:%M',
                                  validators=[DataRequired()],
                                  default=datetime.now() + timedelta(days=3))
    comments = TextAreaField('Commentaires', validators=[Length(max=1000)])
    submit = SubmitField('Demander un entretien')
