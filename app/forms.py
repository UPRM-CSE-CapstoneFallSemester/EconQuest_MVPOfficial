from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, ValidationError

# Usamos Email() solo para registro (alta de usuarios).
EMAIL_DEV = Email(check_deliverability=False)

NAME_RE = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ' -]{2,60}$"  # letras, espacios, apóstrofo y guion

class RegisterForm(FlaskForm):
    name = StringField(
        "Nombre",
        validators=[
            DataRequired(),
            Length(min=2, max=60),
            Regexp(NAME_RE, message="Nombre inválido (solo letras, espacios, apóstrofo o guion).")
        ]
    )
    email = StringField("Email", validators=[DataRequired(), EMAIL_DEV, Length(max=255)])
    password = PasswordField(
        "Contraseña",
        validators=[
            DataRequired(),
            Length(min=8, message="Mínimo 8 caracteres."),
            Regexp(r"(?=.*[A-Za-z])(?=.*\d)", message="Debe incluir al menos 1 letra y 1 número.")
        ]
    )
    confirm = PasswordField("Confirmar", validators=[DataRequired(), EqualTo("password", message="Las contraseñas no coinciden.")])
    submit = SubmitField("Crear cuenta")

class LoginForm(FlaskForm):
    # 💡 SIN Email(): evita el “Invalid email address.” en dev
    email = StringField("Email", validators=[DataRequired(), Length(max=255)])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    remember = BooleanField("Recordarme")
    submit = SubmitField("Entrar")
