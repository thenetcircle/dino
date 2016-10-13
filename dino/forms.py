import dino.environ


class LoginForm(object):
    @staticmethod
    def create():
        if dino.environ.env.config.get(dino.environ.env.ConfigKeys.TESTING):
            return _MockLoginForm()
        return _LoginForm()


class _MockLoginForm(object):
    def __init__(self, formdata=None, obj=None, prefix='', csrf_context=None,
                 secret_key=None, csrf_enabled=None, *args, **kwargs):
        self.user_name = dino.environ.env.StringField('User name', validators=[dino.environ.env.DataRequired()])
        self.gender = dino.environ.env.SelectField('Gender', choices=[('m', 'male'), ('f', 'female'), ('ts', 'TS')], validators=[dino.environ.env.DataRequired()])
        self.membership = dino.environ.env.SelectField('Membership', choices=[('0', '0'), ('1', '1'), ('2', '2')], validators=[dino.environ.env.DataRequired()])
        self.image = dino.environ.env.SelectField('Has image?', choices=[('y', 'Yes'), ('n', 'No')], validators=[dino.environ.env.DataRequired()])
        self.has_webcam = dino.environ.env.SelectField('Has webcam?', choices=[('y', 'Yes'), ('n', 'No')], validators=[dino.environ.env.DataRequired()])
        self.fake_checked = dino.environ.env.SelectField('Fake checked?', choices=[('y', 'Yes'), ('n', 'No')], validators=[dino.environ.env.DataRequired()])
        self.country = dino.environ.env.SelectField('Country', choices=[('cn', 'China'), ('de', 'Germany'), ('se', 'Sweden')], validators=[dino.environ.env.DataRequired()])
        self.age = dino.environ.env.StringField('Age', validators=[dino.environ.env.DataRequired()])
        self.city = dino.environ.env.StringField('City', validators=[dino.environ.env.DataRequired()])
        self.submit = dino.environ.env.SubmitField('Login')

    def validate_on_submit(self):
        return self.user_name.data is not None


class _LoginForm(dino.environ.env.Form):
    user_name = dino.environ.env.StringField('User name', validators=[dino.environ.env.DataRequired()])
    gender = dino.environ.env.SelectField('Gender', choices=[('m', 'male'), ('f', 'female'), ('ts', 'TS')], validators=[dino.environ.env.DataRequired()])
    membership = dino.environ.env.SelectField('Membership', choices=[('0', '0'), ('1', '1'), ('2', '2')], validators=[dino.environ.env.DataRequired()])
    image = dino.environ.env.SelectField('Has image?', choices=[('y', 'Yes'), ('n', 'No')], validators=[dino.environ.env.DataRequired()])
    has_webcam = dino.environ.env.SelectField('Has webcam?', choices=[('y', 'Yes'), ('n', 'No')], validators=[dino.environ.env.DataRequired()])
    fake_checked = dino.environ.env.SelectField('Fake checked?', choices=[('y', 'Yes'), ('n', 'No')], validators=[dino.environ.env.DataRequired()])
    country = dino.environ.env.SelectField('Country', choices=[('cn', 'China'), ('de', 'Germany'), ('se', 'Sweden')], validators=[dino.environ.env.DataRequired()])
    age = dino.environ.env.StringField('Age', validators=[dino.environ.env.DataRequired()])
    city = dino.environ.env.StringField('City', validators=[dino.environ.env.DataRequired()])
    submit = dino.environ.env.SubmitField('Login')
