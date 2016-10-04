from flask_wtf import Form
from wtforms.fields import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired


class LoginForm(Form):
    user_name = StringField('User name', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('m', 'male'), ('f', 'female'), ('ts', 'TS')], validators=[DataRequired()])
    membership = SelectField('Membership', choices=[('0', '0'), ('1', '1'), ('2', '2')], validators=[DataRequired()])
    image = SelectField('Has image?', choices=[('y', 'Yes'), ('n', 'No')], validators=[DataRequired()])
    has_webcam = SelectField('Has webcam?', choices=[('y', 'Yes'), ('n', 'No')], validators=[DataRequired()])
    fake_checked = SelectField('Fake checked?', choices=[('y', 'Yes'), ('n', 'No')], validators=[DataRequired()])
    country = SelectField('Country', choices=[('cn', 'China'), ('de', 'Germany'), ('se', 'Sweden')], validators=[DataRequired()])
    age = StringField('Age', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    submit = SubmitField('Login')
