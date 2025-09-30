from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo

# Usamos Email() solo para registro (alta de usuarios).
EMAIL_DEV = Email(check_deliverability=False)

class RegisterForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), EMAIL_DEV, Length(max=255)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField("Confirmar", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Crear cuenta")

class LoginForm(FlaskForm):
    # 💡 SIN Email(): evita el “Invalid email address.” en dev
    email = StringField("Email", validators=[DataRequired(), Length(max=255)])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    remember = BooleanField("Recordarme")
    submit = SubmitField("Entrar")

