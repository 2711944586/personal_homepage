import os

#  将配置移入 Config 类
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    应用配置
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-super-secret-key-you-should-change'
    
    # 将数据库放入 instance 文件夹
    # instance 文件夹会自动在项目根目录创建
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'students_v5.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False