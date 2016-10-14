from dino import environ
from dino.config import ConfigKeys


class LoginForm(object):
    @staticmethod
    def create():
        if environ.env.config.get(ConfigKeys.TESTING):
            return _MockLoginForm()
        return _LoginForm()


class _MockLoginForm(object):
    def __init__(self, formdata=None, obj=None, prefix='', csrf_context=None,
                 secret_key=None, csrf_enabled=None, *args, **kwargs):
        self.user_name = environ.env.StringField('User name', validators=[environ.env.DataRequired()])
        self.gender = environ.env.SelectField('Gender', choices=[('m', 'male'), ('f', 'female'), ('ts', 'TS')], validators=[environ.env.DataRequired()])
        self.membership = environ.env.SelectField('Membership', choices=[('0', '0'), ('1', '1'), ('2', '2')], validators=[environ.env.DataRequired()])
        self.image = environ.env.SelectField('Has image?', choices=[('y', 'Yes'), ('n', 'No')], validators=[environ.env.DataRequired()])
        self.has_webcam = environ.env.SelectField('Has webcam?', choices=[('y', 'Yes'), ('n', 'No')], validators=[environ.env.DataRequired()])
        self.fake_checked = environ.env.SelectField('Fake checked?', choices=[('y', 'Yes'), ('n', 'No')], validators=[environ.env.DataRequired()])
        self.country = environ.env.SelectField('Country', choices=[('cn', 'China'), ('de', 'Germany'), ('se', 'Sweden')], validators=[environ.env.DataRequired()])
        self.age = environ.env.StringField('Age', validators=[environ.env.DataRequired()])
        self.city = environ.env.StringField('City', validators=[environ.env.DataRequired()])
        self.submit = environ.env.SubmitField('Login')

    def validate_on_submit(self):
        return self.user_name.data is not None


class _LoginForm(environ.env.Form):
    user_name = environ.env.StringField('User name', validators=[environ.env.DataRequired()])
    gender = environ.env.SelectField('Gender', choices=[('m', 'male'), ('f', 'female'), ('ts', 'TS')], validators=[environ.env.DataRequired()])
    membership = environ.env.SelectField('Membership', choices=[('0', '0'), ('1', '1'), ('2', '2')], validators=[environ.env.DataRequired()])
    image = environ.env.SelectField('Has image?', choices=[('y', 'Yes'), ('n', 'No')], validators=[environ.env.DataRequired()])
    has_webcam = environ.env.SelectField('Has webcam?', choices=[('y', 'Yes'), ('n', 'No')], validators=[environ.env.DataRequired()])
    fake_checked = environ.env.SelectField('Fake checked?', choices=[('y', 'Yes'), ('n', 'No')], validators=[environ.env.DataRequired()])
    country = environ.env.SelectField('Country', choices=[('cn', 'China'), ('de', 'Germany'), ('se', 'Sweden')], validators=[environ.env.DataRequired()])
    age = environ.env.StringField('Age', validators=[environ.env.DataRequired()])
    city = environ.env.StringField('City', validators=[environ.env.DataRequired()])
    submit = environ.env.SubmitField('Login')
