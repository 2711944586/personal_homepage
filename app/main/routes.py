import io
import csv
from functools import wraps
from flask import (
    render_template, redirect, url_for, flash, request, Response, 
    make_response, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import or_

from . import main
from .. import db, login_manager
# (V5 新功能 5) 导入 AuditLog
from ..models import User, Major, StudentInfo, AuditLog
from ..forms import (
    StudentForm, MajorForm, EditMajorForm, CSVImportForm
)

# (V5) 权限装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_admin():
            flash('您没有管理员权限执行此操作。', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# (V5 新功能 5) 日志辅助函数
def log_action(action, details=None):
    """创建并暂存一条审计日志"""
    try:
        log_entry = AuditLog(
            user_id=current_user.id,
            action=action,
            details=details
        )
        db.session.add(log_entry)
    except Exception as e:
        print(f"Error adding audit log: {e}")

# (V5) 首页
@main.route("/")
def index():
    query = StudentInfo.query
    search_query = request.args.get('q')
    if search_query:
        query = query.filter(or_(
            StudentInfo.student_name.ilike(f'%{search_query}%'),
            StudentInfo.student_id.cast(db.String).ilike(f'%{search_query}%')
        ))
    
    major_id = request.args.get('major_id', type=int)
    major_title = "所有学生"
    if major_id:
        major = Major.query.get_or_404(major_id)
        query = query.filter(StudentInfo.major_id == major_id)
        major_title = f"{major.major_name}专业"

    studs = query.order_by(StudentInfo.student_id).all()
    majors = Major.query.all()
    title = major_title
    if search_query:
        title = f'搜索 "{search_query}" 的结果'
    
    return render_template('index.html', studs=studs, majors=majors,
                           title=title, search_query=search_query, major_id=major_id)

# (V5) 学生详情页
@main.route('/profile/<int:student_id>')
@login_required 
def view_profile(student_id):
    student = StudentInfo.query.get_or_404(student_id)
    return render_template('view_profile.html', title=f"学生详情 - {student.student_name}", student=student)

# (V5) 仪表盘 API
@main.route("/dashboard-data")
@login_required
def dashboard_data():
    majors_data = db.session.query(
        Major.major_name, db.func.count(StudentInfo.student_id)
    ).outerjoin(StudentInfo, Major.id == StudentInfo.major_id)\
     .group_by(Major.major_name).all()
    labels = [data[0] for data in majors_data]
    data = [data[1] for data in majors_data]
    return jsonify({'labels': labels, 'data': data})

# (V5) 学生 CRUD (V6 升级: 添加日志)
@main.route("/new-student", methods=['GET', 'POST'])
@admin_required
def new_student():
    form = StudentForm()
    form.major.choices = [(m.id, m.major_name) for m in Major.query.order_by('major_name')]
    if form.validate_on_submit():
        if StudentInfo.query.get(form.id.data):
            flash("该学号已存在。", "danger")
            return redirect(url_for('main.new_student'))
        new_stu = StudentInfo(
            student_id=form.id.data, 
            student_name=form.name.data, 
            major_id=form.major.data,
            notes=form.notes.data
        )
        db.session.add(new_stu)
        
        # (V5 新功能 5) 添加日志
        log_action("Create Student", f"Added student: {new_stu.student_name} (ID: {new_stu.student_id})")
        
        db.session.commit()
        flash(f"学生 {form.name.data} 的信息已成功添加！", "success")
        return redirect(url_for('main.index'))
    return render_template('new_student.html', form=form, title="添加新学生")

@main.route("/edit-student/<int:stu_id>", methods=['GET', 'POST'])
@admin_required
def edit_student(stu_id):
    stud = StudentInfo.query.get_or_404(stu_id)
    form = StudentForm(obj=stud)
    form.major.choices = [(m.id, m.major_name) for m in Major.query.order_by('major_name')]
    
    if form.validate_on_submit():
        new_id = form.id.data
        if new_id != stu_id and StudentInfo.query.get(new_id):
            flash("修改后的学号已存在！", "danger")
            return redirect(url_for('main.edit_student', stu_id=stu_id))
        
        # (V5 新功能 5) 记录日志
        log_action("Edit Student", f"Edited student: {stud.student_name} (ID: {stud.student_id})")
        
        stud.student_id = new_id
        stud.student_name = form.name.data
        stud.major_id = form.major.data
        stud.notes = form.notes.data 
        
        db.session.commit()
        flash("学生信息已成功更新！", "success")
        return redirect(url_for('main.view_profile', student_id=stud.student_id))

    form.id.data = stud.student_id
    form.name.data = stud.student_name
    form.major.data = stud.major_id
    form.notes.data = stud.notes 
    
    return render_template('edit_student.html', form=form, title="编辑学生信息", student=stud)

@main.route("/delete-student/<int:stu_id>", methods=['POST'])
@admin_required
def delete_student(stu_id):
    stud = StudentInfo.query.get_or_404(stu_id)
    
    # (V5 新功能 5) 记录日志
    log_action("Delete Student", f"Deleted student: {stud.student_name} (ID: {stud.student_id})")
    
    db.session.delete(stud)
    db.session.commit()
    flash(f"学生 {stud.student_name} 的信息已删除。", "info")
    return redirect(url_for('main.index'))

# (V5) 专业 CRUD (V6 升级: 添加日志)
@main.route("/manage-majors", methods=['GET', 'POST'])
@admin_required
def manage_majors():
    form = MajorForm()
    majors = Major.query.order_by('major_name').all()
    if form.validate_on_submit():
        new_major = Major(major_name=form.major_name.data)
        db.session.add(new_major)
        
        # (V5 新功能 5) 记录日志
        log_action("Create Major", f"Added major: {new_major.major_name}")
        
        db.session.commit()
        flash(f"专业 '{new_major.major_name}' 已成功添加！", "success")
        return redirect(url_for('main.manage_majors'))
    return render_template('manage_majors.html', form=form, majors=majors, title="专业管理")

@main.route("/edit-major/<int:major_id>", methods=['GET', 'POST'])
@admin_required
def edit_major(major_id):
    major = Major.query.get_or_404(major_id)
    form = EditMajorForm(original_name=major.major_name)
    if form.validate_on_submit():
        
        # (V5 新功能 5) 记录日志
        log_action("Edit Major", f"Edited major '{major.major_name}' to '{form.major_name.data}'")
        
        major.major_name = form.major_name.data
        db.session.commit()
        flash("专业名称已更新！", "success")
        return redirect(url_for('main.manage_majors'))
    form.major_name.data = major.major_name
    return render_template('edit_major.html', form=form, title="编辑专业", major=major)

@main.route("/delete-major/<int:major_id>", methods=['POST'])
@admin_required
def delete_major(major_id):
    major = Major.query.get_or_404(major_id)
    if major.students.first():
        flash(f"无法删除专业 '{major.major_name}'，仍有学生隶属于该专业。", "danger")
    else:
        # (V5 新功能 5) 记录日志
        log_action("Delete Major", f"Deleted major: {major.major_name}")
        
        db.session.delete(major)
        db.session.commit()
        flash(f"专业 '{major.major_name}' 已被删除。", "info")
    return redirect(url_for('main.manage_majors'))

# (V5) 数据工具 (V6 升级: 添加日志)
@main.route("/data-tools", methods=['GET', 'POST'])
@admin_required
def data_tools():
    form = CSVImportForm()
    if form.validate_on_submit():
        try:
            # ... (V5 的 CSV 导入逻辑保持不变) ...
            file_storage = form.csv_file.data
            file_stream = io.StringIO(file_storage.stream.read().decode("utf-8"), newline=None)
            csv_reader = csv.reader(file_stream)
            added_count = 0
            failed_rows = []
            
            for row in csv_reader:
                if len(row) < 3: continue
                stu_id, stu_name, major_name = row[0].strip(), row[1].strip(), row[2].strip()
                major = Major.query.filter_by(major_name=major_name).first()
                if not major:
                    failed_rows.append(f"{row} (专业 '{major_name}' 不存在)")
                    continue
                if StudentInfo.query.get(stu_id):
                    failed_rows.append(f"{row} (学号 {stu_id} 已存在)")
                    continue
                new_stu = StudentInfo(student_id=stu_id, student_name=stu_name, major_id=major.id)
                db.session.add(new_stu)
                added_count += 1
            
            # (V5 新功能 5) 记录日志
            log_action("CSV Import", f"Imported {added_count} students. Failed {len(failed_rows)} rows.")
            
            db.session.commit()
            if added_count > 0: flash(f"成功导入 {added_count} 名学生。", 'success')
            if failed_rows: flash(f"有 {len(failed_rows)} 行数据导入失败: {', '.join(failed_rows[:5])}...", 'danger')
            return redirect(url_for('main.data_tools'))
        except Exception as e:
            db.session.rollback()
            flash(f'导入时发生错误: {e}', 'danger')
    return render_template('data_tools.html', title="数据工具", form=form)

@main.route("/export-csv")
@admin_required
def export_csv():
    # (V5 新功能 5) 记录日志
    log_action("Export CSV", "Exported student data.")
    db.session.commit() # 提交日志
    
    # ... (V5 的 CSV 导出逻辑保持不变) ...
    query = StudentInfo.query
    search_query = request.args.get('q')
    major_id = request.args.get('major_id', type=int)
    if search_query:
        query = query.filter(or_(StudentInfo.student_name.ilike(f'%{search_query}%'), StudentInfo.student_id.cast(db.String).ilike(f'%{search_query}%')))
    if major_id:
        query = query.filter(StudentInfo.major_id == major_id)
    students = query.all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['student_id', 'student_name', 'major_name', 'notes'])
    for stud in students:
        cw.writerow([stud.student_id, stud.student_name, stud.major.major_name, stud.notes])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=students_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# (V5 新功能 5) 审计日志页面
@main.route('/audit-log')
@admin_required
def audit_log():
    """显示所有操作日志，按时间倒序"""
    # .limit(100) 可以防止页面过载，可根据需要添加
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all() 
    return render_template('audit_log.html', title="审计日志", logs=logs)