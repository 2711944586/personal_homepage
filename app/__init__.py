import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

# 1. (任务二) 在全局实例化扩展，但不初始化
db = SQLAlchemy()
login_manager = LoginManager()
# (V5 新功能 1) 实例化 CSRF
csrf = CSRFProtect()

# 4. (任务四修复) 配置 login_manager
login_manager.login_view = 'auth.login' # 必须指向蓝图端点
login_manager.login_message = '请先登录以访问此页面。'
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    """
    (任务二) 定义应用工厂
    """
    # 2. 定义应用工厂
    # (V5) instance_relative_config=True 允许从 instance 文件夹加载
    app = Flask(__name__, instance_relative_config=True) 
    app.config.from_object(config_class) # 从 config.py 加载配置

    # (V5 最佳实践) 确保 instance 文件夹存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # 3. (任务二) 延迟初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    # (V5 新功能 1) 初始化 CSRF
    csrf.init_app(app)

    # 5. (任务三) 注册蓝图
    
    # 认证蓝图
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # 主功能蓝图
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # (V5 新结构) 注册 CLI 命令
    from . import commands
    app.cli.add_command(commands.init_db_command)

    return app

# (V5) 在 app 包的末尾导入 models
# 这是一个常见的模式，以避免循环导入
from . import models