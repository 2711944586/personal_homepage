from app import create_app, db
from app.models import User, StudentInfo, Major

#  从工厂创建 app
app = create_app()

#  添加 shell 上下文，方便调试
@app.shell_context_processor
def make_shell_context():
    """
    为 'flask shell' 命令自动导入
    """
    return dict(db=db, User=User, StudentInfo=StudentInfo, Major=Major)

if __name__ == '__main__':
    app.run(debug=True)