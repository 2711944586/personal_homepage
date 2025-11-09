from flask import Blueprint

# (任务三) 创建主蓝图
main = Blueprint('main', __name__)

# (任务三) 导入蓝图路由
# 放在末尾以避免循环导入
from . import routes