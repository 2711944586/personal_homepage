import io
import random
import string
from flask import (
    render_template, redirect, url_for, flash, request, session, 
    Response, make_response
)
from flask_login import login_user, logout_user, login_required, current_user
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from . import auth # (任务三) 导入当前蓝图
from .. import db   # (任务四) 导入 app 级别的 db
from ..models import User
from ..forms import LoginForm, RegistrationForm

# (任务三) 迁移所有认证路由
# (任务四修复) 路由装饰器改为 @auth.route
# (任务四修复) url_for() 添加 'main.' 或 'auth.' 命名空间

@auth.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, role='guest')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session.pop('captcha_code', None)
        flash('恭喜，您已注册成功！请登录。', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='注册', form=form)

@auth.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('用户名或密码无效。', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        # (V4) 智能重定向
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.index') # (任务四修复)
        flash(f'欢迎回来, {user.username}!', 'success')
        return redirect(next_page)
        
    return render_template('login.html', title='登录', form=form)

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash('您已成功登出。', 'info')
    return redirect(url_for('main.index')) # (任务四修复)

# --- (V4) 验证码 (现在属于 auth 蓝图) ---
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

@auth.route('/captcha')
def get_captcha():
    code = generate_captcha_code()
    session['captcha_code'] = code
    buf = generate_captcha_image(code)
    response = make_response(buf.getvalue())
    response.headers['Content-Type'] = 'image/png'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = '0'
    return response