from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Email, EqualTo, Length


class RegisterForm(FlaskForm):
    username = StringField(
        "Tên đăng nhập", validators=[InputRequired(), Length(min=3, max=80)]
    )
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=120)])
    password = PasswordField("Mật khẩu", validators=[InputRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Xác nhận mật khẩu",
        validators=[
            InputRequired(),
            EqualTo("password", message="Mật khẩu xác nhận không khớp"),
        ],
    )
