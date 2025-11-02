import os
import random
import string
import io
import csv
from flask import (
    Flask, render_template, redirect, url_for, flash, request, session, Response,
    make_response, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField, PasswordField, BooleanField
from wtforms.validators import DataRequired, NumberRange, ValidationError, EqualTo, Length
# (新) 导入 WTForms 文件字段
from flask_wtf.file import FileField, FileAllowed, FileRequired

from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from functools import wraps
# (新) 导入 SQLAlchemy 的 'or_' 'like' 'ilike'
from sqlalchemy import or_

# --- App & DB Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_v4_secret_key_that_is_very_secure')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students_v4.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '您必须登录才能访问此页面。'
login_manager.login_message_category = 'info'

# --- (V3) Models (无变动) ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='guest')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

class Major(db.Model):
    __tablename__ = 'majors'
    id = db.Column(db.Integer, primary_key=True)
    major_name = db.Column(db.String(100), unique=True, nullable=False)
    students = db.relationship('StudentInfo', backref='major', lazy='dynamic')

class StudentInfo(db.Model):
    __tablename__ = 'student_info'
    student_id = db.Column(db.Integer, primary_key=True) # 学号
    student_name = db.Column(db.String(100), nullable=False) # 姓名
    major_id = db.Column(db.Integer, db.ForeignKey('majors.id'), nullable=False)

# --- (V3) Auth Forms (无变动) ---
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

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('安全登录')

# --- (V3) CRUD Forms (无变动) ---
class StudentForm(FlaskForm):
    id = IntegerField('学号', validators=[DataRequired(), NumberRange(min=1)])
    name = StringField('姓名', validators=[DataRequired()])
    major = SelectField('专业', coerce=int, validators=[DataRequired()])
    submit = SubmitField('提交')

class MajorForm(FlaskForm):
    major_name = StringField('专业名称', validators=[DataRequired()])
    submit = SubmitField('提交')
    def validate_major_name(self, field):
        if Major.query.filter_by(major_name=field.data).first():
            raise ValidationError('该专业名称已存在。')

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

# --- (新功能 V4) CSV 导入表单 ---
class CSVImportForm(FlaskForm):
    csv_file = FileField('CSV 文件', validators=[
        FileRequired(),
        FileAllowed(['csv'], '只允许上传 CSV 文件！')
    ])
    submit = SubmitField('导入')

# --- (V3) 权限装饰器 (无变动) ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_admin():
            flash('您没有管理员权限执行此操作。', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- (V3) 验证码 (无变动) ---
def generate_captcha_code(length=4):
    return ''.join(random.choices(string.ascii_uppercase, k=length))
def generate_captcha_image(code):
    size = (130, 60)
    image = Image.new('RGB', size, (255, 255, 255))
    draw = ImageDraw.Draw(image)
    try: font = ImageFont.truetype("arial.ttf", 36)
    except IOError: font = ImageFont.load_default()
    for i, char in enumerate(code):
        color = (random.randint(0, 150), random.randint(0, 150), random.randint(0, 150))
        draw.text((10 + i * 30, 10), char, font=font, fill=color)
    for _ in range(50):
        draw.point((random.randint(0, size[0]), random.randint(0, size[1])), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    for _ in range(5):
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        draw.line((random.randint(0, size[0]), random.randint(0, size[1]), random.randint(0, size[0]), random.randint(0, size[1])), fill=color, width=1)
    image = image.filter(ImageFilter.SMOOTH)
    buf = io.BytesIO()
    image.save(buf, 'PNG')
    buf.seek(0)
    return buf

@app.route('/captcha')
def get_captcha():
    code = generate_captcha_code()
    session['captcha_code'] = code
    buf = generate_captcha_image(code)
    response = make_response(buf.getvalue())
    response.headers['Content-Type'] = 'image/png'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = '0'
    return response

# --- (V3) Auth Routes (无变动) ---
@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, role='guest')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session.pop('captcha_code', None)
        flash('恭喜，您已注册成功！请登录。', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='注册', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('用户名或密码无效。', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('index')
        flash(f'欢迎回来, {user.username}!', 'success')
        return redirect(next_page)
    return render_template('login.html', title='登录', form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('您已成功登出。', 'info')
    return redirect(url_for('index'))

# --- (V4) 首页/仪表盘/搜索/筛选 ---
@app.route("/")
def index():
    # 基础查询
    query = StudentInfo.query
    
    # (新功能 V4) 搜索
    search_query = request.args.get('q')
    if search_query:
        # 使用 ilike 进行不区分大小写的模糊搜索
        query = query.filter(or_(
            StudentInfo.student_name.ilike(f'%{search_query}%'),
            # 将学号转为字符串进行搜索，以匹配部分数字
            StudentInfo.student_id.cast(db.String).ilike(f'%{search_query}%')
        ))
    
    # (V3 功能) 筛选
    major_id = request.args.get('major_id', type=int)
    major_title = "所有学生"
    if major_id:
        major = Major.query.get_or_404(major_id)
        query = query.filter(StudentInfo.major_id == major_id)
        major_title = f"{major.major_name}专业"

    studs = query.order_by(StudentInfo.student_id).all()
    majors = Major.query.all()
    
    # 动态标题
    title = major_title
    if search_query:
        title = f'搜索 "{search_query}" 的结果'
    
    return render_template('index.html', studs=studs, majors=majors,
                           title=title, search_query=search_query, major_id=major_id)

# --- (新功能 V4) 仪表盘数据 API ---
@app.route("/dashboard-data")
@login_required
def dashboard_data():
    """为 Chart.js 提供 JSON 数据"""
    majors_data = db.session.query(
        Major.major_name, db.func.count(StudentInfo.student_id)
    ).outerjoin(StudentInfo, Major.id == StudentInfo.major_id)\
     .group_by(Major.major_name).all()

    labels = [data[0] for data in majors_data]
    data = [data[1] for data in majors_data]

    return jsonify({'labels': labels, 'data': data})

# --- (V3) Student CRUD (受保护, 无变动) ---
@app.route("/new-student", methods=['GET', 'POST'])
@admin_required
def new_student():
    form = StudentForm()
    form.major.choices = [(m.id, m.major_name) for m in Major.query.order_by('major_name')]
    if form.validate_on_submit():
        if StudentInfo.query.get(form.id.data):
            flash("该学号已存在。", "danger")
            return redirect(url_for('new_student'))
        new_stu = StudentInfo(student_id=form.id.data, student_name=form.name.data, major_id=form.major.data)
        db.session.add(new_stu)
        db.session.commit()
        flash(f"学生 {form.name.data} 的信息已成功添加！", "success")
        return redirect(url_for('index'))
    return render_template('new_student.html', form=form, title="添加新学生")

@app.route("/edit-student/<int:stu_id>", methods=['GET', 'POST'])
@admin_required
def edit_student(stu_id):
    stud = StudentInfo.query.get_or_404(stu_id)
    form = StudentForm(obj=stud)
    form.major.choices = [(m.id, m.major_name) for m in Major.query.order_by('major_name')]
    if form.validate_on_submit():
        new_id = form.id.data
        if new_id != stu_id and StudentInfo.query.get(new_id):
            flash("修改后的学号已存在！", "danger")
            return redirect(url_for('edit_student', stu_id=stu_id))
        stud.student_id = new_id
        stud.student_name = form.name.data
        stud.major_id = form.major.data
        db.session.commit()
        flash("学生信息已成功更新！", "success")
        return redirect(url_for('index'))
    form.id.data = stud.student_id
    form.name.data = stud.student_name
    form.major.data = stud.major_id
    return render_template('edit_student.html', form=form, title="编辑学生信息", student=stud)

@app.route("/delete-student/<int:stu_id>", methods=['POST'])
@admin_required
def delete_student(stu_id):
    stud = StudentInfo.query.get_or_404(stu_id)
    db.session.delete(stud)
    db.session.commit()
    flash(f"学生 {stud.student_name} 的信息已删除。", "info")
    return redirect(url_for('index'))

# --- (V3) Major CRUD (受保护, 无变动) ---
@app.route("/manage-majors", methods=['GET', 'POST'])
@admin_required
def manage_majors():
    form = MajorForm()
    majors = Major.query.order_by('major_name').all()
    if form.validate_on_submit():
        new_major = Major(major_name=form.major_name.data)
        db.session.add(new_major)
        db.session.commit()
        flash(f"专业 '{new_major.major_name}' 已成功添加！", "success")
        return redirect(url_for('manage_majors'))
    return render_template('manage_majors.html', form=form, majors=majors, title="专业管理")

@app.route("/edit-major/<int:major_id>", methods=['GET', 'POST'])
@admin_required
def edit_major(major_id):
    major = Major.query.get_or_404(major_id)
    form = EditMajorForm(original_name=major.major_name)
    if form.validate_on_submit():
        major.major_name = form.major_name.data
        db.session.commit()
        flash("专业名称已更新！", "success")
        return redirect(url_for('manage_majors'))
    form.major_name.data = major.major_name
    return render_template('edit_major.html', form=form, title="编辑专业", major=major)

@app.route("/delete-major/<int:major_id>", methods=['POST'])
@admin_required
def delete_major(major_id):
    major = Major.query.get_or_404(major_id)
    if major.students.first():
        flash(f"无法删除专业 '{major.major_name}'，仍有学生隶属于该专业。", "danger")
    else:
        db.session.delete(major)
        db.session.commit()
        flash(f"专业 '{major.major_name}' 已被删除。", "info")
    return redirect(url_for('manage_majors'))

# --- (新功能 V4) 数据工具 (CSV 导入/导出) ---
@app.route("/data-tools", methods=['GET', 'POST'])
@admin_required
def data_tools():
    form = CSVImportForm()
    if form.validate_on_submit():
        try:
            # 读取上传的文件
            file_storage = form.csv_file.data
            file_stream = io.StringIO(file_storage.stream.read().decode("utf-8"), newline=None)
            
            # 使用 csv.reader 解析
            csv_reader = csv.reader(file_stream)
            
            # (可选) 跳过表头
            # next(csv_reader) 
            
            added_count = 0
            failed_rows = []
            
            for row in csv_reader:
                if len(row) < 3: continue # 确保行数据完整
                
                stu_id = row[0].strip()
                stu_name = row[1].strip()
                major_name = row[2].strip()
                
                # 查找专业
                major = Major.query.filter_by(major_name=major_name).first()
                if not major:
                    failed_rows.append(f"{row} (专业 '{major_name}' 不存在)")
                    continue
                    
                # 检查学号是否已存在
                if StudentInfo.query.get(stu_id):
                    failed_rows.append(f"{row} (学号 {stu_id} 已存在)")
                    continue
                    
                # 创建新学生
                new_stu = StudentInfo(student_id=stu_id, student_name=stu_name, major_id=major.id)
                db.session.add(new_stu)
                added_count += 1
            
            db.session.commit()
            
            if added_count > 0:
                flash(f"成功导入 {added_count} 名学生。", 'success')
            if failed_rows:
                flash(f"有 {len(failed_rows)} 行数据导入失败: {', '.join(failed_rows[:5])}...", 'danger')
            
            return redirect(url_for('data_tools'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'导入时发生错误: {e}', 'danger')
            
    return render_template('data_tools.html', title="数据工具", form=form)

@app.route("/export-csv")
@admin_required
def export_csv():
    # (高级) 此导出也会尊重首页的搜索和筛选条件
    query = StudentInfo.query
    search_query = request.args.get('q')
    major_id = request.args.get('major_id', type=int)

    if search_query:
        query = query.filter(or_(
            StudentInfo.student_name.ilike(f'%{search_query}%'),
            StudentInfo.student_id.cast(db.String).ilike(f'%{search_query}%')
        ))
    if major_id:
        query = query.filter(StudentInfo.major_id == major_id)
        
    students = query.all()
    
    # 在内存中创建 CSV
    si = io.StringIO()
    cw = csv.writer(si)
    
    # 写入表头
    cw.writerow(['student_id', 'student_name', 'major_name'])
    
    # 写入数据
    for stud in students:
        cw.writerow([stud.student_id, stud.student_name, stud.major.major_name])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=students_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# --- (V3) CLI Command (无变动) ---
@app.cli.command('init-db')
def init_db_command():
    db.create_all()
    if not Major.query.first():
        print("添加初始专业...")
        majors_list = ['计算机科学与技术', '软件工程', '数据科学', '人工智能', '网络安全', '金融学', '会计学', '工商管理', '法学', '汉语言文学']
        for m_name in majors_list:
            db.session.add(Major(major_name=m_name))
        db.session.commit()
    else:
        print('专业数据已存在。')
        
    if not User.query.first():
        print("创建默认用户...")
        admin = User(username='constantine', role='admin')
        admin.set_password('zs123456ty')
        guest = User(username='guest', role='guest')
        guest.set_password('123456')
        db.session.add_all([admin, guest])
        db.session.commit()
        print("\n" + "="*30)
        print("默认用户创建成功！")
        print("管理员: constantine, 密码: zs123456ty")
        print("访  客: guest, 密码: 123456")
        print("="*30 + "\n")
    else:
        print('用户数据已存在。')
    print('数据库初始化完成！')

if __name__ == '__main__':
    app.run(debug=True)