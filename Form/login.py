from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired


class LoginForm(FlaskForm):
    username = StringField("Tên đăng nhập", validators=[InputRequired()])
    password = PasswordField("Mật khẩu", validators=[InputRequired()])
    remember_me = BooleanField("Nhớ tôi")
