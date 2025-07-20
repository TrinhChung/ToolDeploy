from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional


class DeployAppForm(FlaskForm):
    server_id = SelectField("Server", coerce=int, validators=[DataRequired()])
    domain_id = SelectField("Domain", coerce=int, validators=[DataRequired()])
    subdomain = StringField("Subdomain", validators=[Optional()])

    # ENV fields
    APP_ID = StringField("APP_ID", validators=[DataRequired()])
    APP_NAME = StringField("APP_NAME", validators=[DataRequired()])
    EMAIL = StringField("EMAIL", validators=[DataRequired()])
    ADDRESS = StringField("ADDRESS", validators=[DataRequired()])
    PHONE_NUMBER = StringField("PHONE_NUMBER", validators=[DataRequired()])
    DNS_WEB = StringField("DNS_WEB", validators=[DataRequired()])
    COMPANY_NAME = StringField("COMPANY_NAME", validators=[DataRequired()])
    TAX_NUMBER = StringField("TAX_NUMBER", validators=[DataRequired()])

    note = StringField("Ghi chú", validators=[Optional()])
    submit = SubmitField("Deploy")
