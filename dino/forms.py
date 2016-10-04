from dino.env import env
from dino.env import ConfigKeys


class LoginForm(object):
    @staticmethod
    def create():
        if env.config.get(ConfigKeys.TESTING):
            return _MockLoginForm()
        return _LoginForm()


class _MockLoginForm(object):
    def __init__(self, formdata=None, obj=None, prefix='', csrf_context=None,
                 secret_key=None, csrf_enabled=None, *args, **kwargs):
        self.user_name = env.StringField('User name', validators=[env.DataRequired()])
        self.gender = env.SelectField('Gender', choices=[('m', 'male'), ('f', 'female'), ('ts', 'TS')], validators=[env.DataRequired()])
        self.membership = env.SelectField('Membership', choices=[('0', '0'), ('1', '1'), ('2', '2')], validators=[env.DataRequired()])
        self.image = env.SelectField('Has image?', choices=[('y', 'Yes'), ('n', 'No')], validators=[env.DataRequired()])
        self.has_webcam = env.SelectField('Has webcam?', choices=[('y', 'Yes'), ('n', 'No')], validators=[env.DataRequired()])
        self.fake_checked = env.SelectField('Fake checked?', choices=[('y', 'Yes'), ('n', 'No')], validators=[env.DataRequired()])
        self.country = env.SelectField('Country', choices=[('cn', 'China'), ('de', 'Germany'), ('se', 'Sweden')], validators=[env.DataRequired()])
        self.age = env.StringField('Age', validators=[env.DataRequired()])
        self.city = env.StringField('City', validators=[env.DataRequired()])
        self.submit = env.SubmitField('Login')

    def validate_on_submit(self):
        return self.user_name.data is not None


class _LoginForm(env.Form):
    user_name = env.StringField('User name', validators=[env.DataRequired()])
    gender = env.SelectField('Gender', choices=[('m', 'male'), ('f', 'female'), ('ts', 'TS')], validators=[env.DataRequired()])
    membership = env.SelectField('Membership', choices=[('0', '0'), ('1', '1'), ('2', '2')], validators=[env.DataRequired()])
    image = env.SelectField('Has image?', choices=[('y', 'Yes'), ('n', 'No')], validators=[env.DataRequired()])
    has_webcam = env.SelectField('Has webcam?', choices=[('y', 'Yes'), ('n', 'No')], validators=[env.DataRequired()])
    fake_checked = env.SelectField('Fake checked?', choices=[('y', 'Yes'), ('n', 'No')], validators=[env.DataRequired()])
    country = env.SelectField('Country', choices=[('cn', 'China'), ('de', 'Germany'), ('se', 'Sweden')], validators=[env.DataRequired()])
    age = env.StringField('Age', validators=[env.DataRequired()])
    city = env.StringField('City', validators=[env.DataRequired()])
    submit = env.SubmitField('Login')
