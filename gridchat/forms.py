from flask_wtf import Form
from wtforms.fields import StringField, SubmitField
from wtforms.validators import Required


class LoginForm(Form):
    """Accepts a nickname and a room."""
    user_name = StringField('user_name', validators=[Required()])
    # room = StringField('Room', validators=[Required()])
    submit = SubmitField('Enter Chatroom')
