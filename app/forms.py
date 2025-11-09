from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, IntegerField, SelectField, 
    PasswordField, BooleanField, TextAreaField
)
from wtforms.validators import (
    DataRequired, NumberRange, ValidationError, EqualTo, Length
)
from flask_wtf.file import FileField, FileAllowed, FileRequired
from .models import Major, User # 导入模型用于验证
from flask import session

# (任务一) 迁移所有表单

# V4 注册表单 (完全迁移)
class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码必须一致。')])
    captcha = StringField('验证码', validators=[DataRequired(), Length(min=4, max=4)], render_kw={'autocomplete': 'off'})
    submit = SubmitField('立即注册')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已被注册。')
    
    def validate_captcha(self, field):
        session_code = session.get('captcha_code')
        if not session_code or field.data.upper() != session_code:
            session.pop('captcha_code', None) # 验证失败后立即清除
            raise ValidationError('验证码错误。')

# V4 登录表单 (完全迁移)
class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('安全登录')

# V4 学生表单 (V5 升级)
class StudentForm(FlaskForm):
    id = IntegerField('学号', validators=[DataRequired(), NumberRange(min=1)])
    name = StringField('姓名', validators=[DataRequired()])
    major = SelectField('专业', coerce=int, validators=[DataRequired()])
    # (V5 新功能 3) 添加笔记表单
    notes = TextAreaField('备注', render_kw={'rows': 4})
    submit = SubmitField('提交')

# V4 专业表单 (完全迁移)
class MajorForm(FlaskForm):
    major_name = StringField('专业名称', validators=[DataRequired()])
    submit = SubmitField('提交')
    def validate_major_name(self, field):
        if Major.query.filter_by(major_name=field.data).first():
            raise ValidationError('该专业名称已存在。')

# V4 编辑专业表单 (完全迁移)
class EditMajorForm(FlaskForm):
    major_name = StringField('专业名称', validators=[DataRequired()])
    submit = SubmitField('保存修改')
    def __init__(self, original_name, *args, **kwargs):
        super(EditMajorForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
    def validate_major_name(self, field):
        if field.data != self.original_name and \
           Major.query.filter_by(major_name=field.data).first():
            raise ValidationError('该专业名称已被其他专业使用。')

# V4 CSV 导入表单 (完全迁移)
class CSVImportForm(FlaskForm):
    csv_file = FileField('CSV 文件', validators=[
        FileRequired(),
        FileAllowed(['csv'], '只允许上传 CSV 文件！')
    ])
    submit = SubmitField('导入')