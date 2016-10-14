from dino import environ
from dino.config import ConfigKeys

_required = environ.env.DataRequired
_select = environ.env.SelectField
_string = environ.env.StringField

choice_gender = [('m', 'male'), ('f', 'female'), ('ts', 'TS')]
choice_membership = [('0', '0'), ('1', '1'), ('2', '2')]
choice_yes_no = [('y', 'Yes'), ('n', 'No')]
choice_country = [('cn', 'China'), ('de', 'Germany'), ('se', 'Sweden')]


class LoginForm(object):
    @staticmethod
    def create():
        if environ.env.config.get(ConfigKeys.TESTING):
            return _MockLoginForm()
        return _LoginForm()


class _MockLoginForm(object):
    def __init__(self, formdata=None, obj=None, prefix='', csrf_context=None,
                 secret_key=None, csrf_enabled=None, *args, **kwargs):
        self.user_name = _string('User name', validators=[_required()])
        self.gender = _select('Gender', choices=choice_gender, validators=[_required()])
        self.membership = _select('Membership', choices=choice_membership, validators=[_required()])
        self.image = _select('Has image?', choices=choice_yes_no, validators=[_required()])
        self.has_webcam = _select('Has webcam?', choices=choice_yes_no, validators=[_required()])
        self.fake_checked = _select('Fake checked?', choices=choice_yes_no, validators=[_required()])
        self.country = _select('Country', choices=choice_country, validators=[_required()])
        self.age = _string('Age', validators=[_required()])
        self.city = _string('City', validators=[_required()])
        self.submit = environ.env.SubmitField('Login')

    def validate_on_submit(self):
        return self.user_name.data is not None


class _LoginForm(environ.env.Form):
    user_name = _string('User name', validators=[_required()])
    gender = _select('Gender', choices=choice_gender, validators=[_required()])
    membership = _select('Membership', choices=choice_membership, validators=[_required()])
    image = _select('Has image?', choices=choice_yes_no, validators=[_required()])
    has_webcam = _select('Has webcam?', choices=choice_yes_no, validators=[_required()])
    fake_checked = _select('Fake checked?', choices=choice_yes_no, validators=[_required()])
    country = _select('Country', choices=choice_country, validators=[_required()])
    age = _string('Age', validators=[_required()])
    city = _string('City', validators=[_required()])
    submit = environ.env.SubmitField('Login')
