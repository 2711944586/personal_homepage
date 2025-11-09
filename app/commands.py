import click
from flask.cli import with_appcontext
from . import db
from .models import Major, User

@click.command('init-db')
@with_appcontext
def init_db_command():
    """清除现有数据并创建新表和默认用户。"""
    db.create_all()
    
    # 1. 添加专业
    if not Major.query.first():
        click.echo("添加初始专业...")
        majors_list = [
            '计算机科学与技术', '软件工程', '数据科学', '人工智能', '网络安全',
            '金融学', '会计学', '工商管理', '法学', '汉语言文学'
        ]
        for m_name in majors_list:
            db.session.add(Major(major_name=m_name))
        db.session.commit()
    else:
        click.echo('专业数据已存在。')
        
    # 2. 添加默认用户 (V6 升级)
    if not User.query.first():
        click.echo("创建默认用户...")
        # (V6 升级) 更改管理员用户名和密码
        admin = User(username='constantine', role='admin')
        admin.set_password('zs123456ty') 
        
        guest = User(username='guest', role='guest')
        guest.set_password('123456') # 访客密码保持不变
        
        db.session.add_all([admin, guest])
        db.session.commit()
        
        click.echo("\n" + "="*30)
        click.echo("默认用户创建成功！")
        # (V6 升级) 更新输出提示
        click.echo("管理员: constantine, 密码: zs123456ty")
        click.echo("访  客: guest, 密码: 123456")
        click.echo("="*30 + "\n")
    else:
        click.echo('用户数据已存在。')
    
    click.echo('数据库初始化完成！')