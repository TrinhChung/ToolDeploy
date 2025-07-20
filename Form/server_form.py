from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, IPAddress


class ServerForm(FlaskForm):
    name = StringField("Tên server", validators=[DataRequired()])
    ip = StringField("IP server", validators=[DataRequired(), IPAddress()])
    admin_username = StringField("Tài khoản quản trị")
    admin_password = PasswordField("Mật khẩu quản trị")
    db_name = StringField("Tên DB")
    db_user = StringField("User DB")
    db_password = PasswordField("Password DB")
    note = StringField("Ghi chú")
    submit = SubmitField("Lưu")
