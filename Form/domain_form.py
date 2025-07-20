from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL


class DomainForm(FlaskForm):
    name = StringField("Domain (example.com)", validators=[DataRequired()])
    submit = SubmitField("Thêm Domain")
