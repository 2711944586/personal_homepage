import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, NumberRange, ValidationError

# --- App & DB Configuration ---
app = Flask(__name__)
# 确保在生产环境中使用更安全的密钥
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secure_secret_key_12345')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# --- Models ---
# 任务1：创建 Major 模型
class Major(db.Model):
    __tablename__ = 'majors'
    id = db.Column(db.Integer, primary_key=True)
    major_name = db.Column(db.String(100), unique=True, nullable=False)
    # 定义“一对多”关系
    students = db.relationship('StudentInfo', backref='major', lazy='dynamic')

    def __repr__(self):
        return f'<Major {self.major_name}>'

# 任务2 (1)：更新 StudentInfo 模型
class StudentInfo(db.Model):
    __tablename__ = 'student_info'
    student_id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    # 新增外键列，并设为不可为空
    major_id = db.Column(db.Integer, db.ForeignKey('majors.id'), nullable=False)

    def __repr__(self):
        return f'<StudentInfo ID:{self.student_id} Name:{self.student_name}>'


# --- Forms ---
# 任务2 (3)：修改表单
class StudentForm(FlaskForm):
    id = IntegerField('学号', validators=[DataRequired(), NumberRange(min=1, message="学号必须是正整数")])
    name = StringField('姓名', validators=[DataRequired()])
    # 新增 SelectField，coerce=int 确保表单返回的是整数ID
    major = SelectField('专业', coerce=int, validators=[DataRequired(message="请选择一个专业")])
    submit = SubmitField('提交')

# (新功能) 用于管理专业的表单
class MajorForm(FlaskForm):
    major_name = StringField('专业名称', validators=[DataRequired()])
    submit = SubmitField('提交')

    # 验证专业名称是否唯一
    def validate_major_name(self, field):
        if Major.query.filter_by(major_name=field.data).first():
            raise ValidationError('该专业名称已存在。')

# (新功能) 用于编辑专业的表单
class EditMajorForm(FlaskForm):
    major_name = StringField('专业名称', validators=[DataRequired()])
    submit = SubmitField('保存修改')
    
    # 允许名称和自己重复，但不能和别人重复
    def __init__(self, original_name, *args, **kwargs):
        super(EditMajorForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_major_name(self, field):
        if field.data != self.original_name and \
           Major.query.filter_by(major_name=field.data).first():
            raise ValidationError('该专业名称已被其他专业使用。')


# --- Routes (Student CRUD & Filtering) ---
@app.route("/")
def index():
    # 任务4 (2)：index 路由传递 majors 列表
    studs = StudentInfo.query.order_by(StudentInfo.student_id).all()
    majors = Major.query.all()
    # (新功能) 传递统计数据
    student_count = StudentInfo.query.count()
    major_count = Major.query.count()
    
    return render_template('index.html', studs=studs, majors=majors,
                           student_count=student_count, major_count=major_count,
                           title="学生信息仪表盘")

# 任务2 (4)：修改 new_stud 路由
@app.route("/new-student", methods=['GET', 'POST'])
def new_student():
    form = StudentForm()
    # 动态填充选项：(value, label)
    form.major.choices = [(m.id, m.major_name) for m in Major.query.order_by('major_name')]
    form.submit.label.text = "添加学生"

    if form.validate_on_submit():
        stu_id = form.id.data
        if StudentInfo.query.get(stu_id):
            flash("该学号已存在，请使用其他学号。", "danger")
            return redirect(url_for('new_student'))

        new_stu = StudentInfo(
            student_id=stu_id,
            student_name=form.name.data,
            major_id=form.major.data  # 直接使用 ID 赋值
        )
        db.session.add(new_stu)
        db.session.commit()
        flash(f"学生 {form.name.data} 的信息已成功添加！", "success")
        return redirect(url_for('index'))

    return render_template('new_student.html', form=form, title="添加新学生")

# 任务2 (4)：修改 edit_stud 路由
@app.route("/edit-student/<int:stu_id>", methods=['GET', 'POST'])
def edit_student(stu_id):
    stud = StudentInfo.query.get_or_404(stu_id)
    form = StudentForm(obj=stud) # 使用 obj 参数可以直接填充表单数据
    form.major.choices = [(m.id, m.major_name) for m in Major.query.order_by('major_name')]
    form.submit.label.text = "保存修改"

    if form.validate_on_submit():
        new_id = form.id.data
        if new_id != stu_id and StudentInfo.query.get(new_id):
            flash("修改后的学号已存在！", "danger")
            return redirect(url_for('edit_student', stu_id=stu_id))

        stud.student_id = new_id
        stud.student_name = form.name.data
        stud.major_id = form.major.data # 更新关联
        db.session.commit()
        flash("学生信息已成功更新！", "success")
        return redirect(url_for('index'))

    # GET 请求时，设置下拉框的默认选中项
    form.id.data = stud.student_id
    form.name.data = stud.student_name
    form.major.data = stud.major_id # 关键：设置默认选中的专业

    return render_template('edit_student.html', form=form, title="编辑学生信息", student=stud)

# (安全修复) 删除操作使用 POST
@app.route("/delete-student/<int:stu_id>", methods=['POST'])
def delete_student(stu_id):
    stud = StudentInfo.query.get_or_404(stu_id)
    db.session.delete(stud)
    db.session.commit()
    flash(f"学生 {stud.student_name} 的信息已删除。", "info")
    return redirect(url_for('index'))

# 任务4 (3)：创建新路由 filter_by_major
@app.route("/major/<int:major_id>")
def filter_by_major(major_id):
    major = Major.query.get_or_404(major_id)
    # 使用 'major' 关系的反向查询 'students'
    studs = major.students.order_by(StudentInfo.student_id).all()
    majors = Major.query.all()
    # (新功能) 传递统计数据
    student_count = len(studs) # 筛选后的学生总数
    major_count = Major.query.count()

    return render_template('index.html', studs=studs, majors=majors,
                           student_count=student_count, major_count=major_count,
                           title=f"{major.major_name}专业")


# --- (新功能) Routes (Major CRUD) ---
@app.route("/manage-majors", methods=['GET', 'POST'])
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
def delete_major(major_id):
    major = Major.query.get_or_404(major_id)
    
    # (系统稳定性) 检查该专业是否还有学生
    if major.students.first():
        flash(f"无法删除专业 '{major.major_name}'，仍有学生隶属于该专业。", "danger")
    else:
        db.session.delete(major)
        db.session.commit()
        flash(f"专业 '{major.major_name}' 已被删除。", "info")
        
    return redirect(url_for('manage_majors'))


# --- CLI Command for DB Initialization ---
# 任务1 (2) & (3) 的自动化版本
@app.cli.command('init-db')
def init_db_command():
    """创建数据库表并添加初始专业数据"""
    db.create_all()
    if not Major.query.first():
        print("数据库为空，正在添加初始专业...")
        # (新功能) 更全面的专业列表
        majors_list = [
            '计算机科学与技术', '软件工程', '数据科学与大数据技术', '人工智能', '网络空间安全',
            '电子信息工程', '自动化', '机械工程', '土木工程', '化学工程',
            '金融学', '会计学', '工商管理', '市场营销', '国际经济与贸易',
            '法学', '汉语言文学', '英语', '新闻学', '艺术设计', '心理学'
        ]
        for m_name in majors_list:
            db.session.add(Major(major_name=m_name))
        db.session.commit()
        print('数据库已成功初始化并添加了20+个初始专业！')
    else:
        print('数据库已存在，跳过初始化。')

if __name__ == '__main__':
    app.run(debug=True)