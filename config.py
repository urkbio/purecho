import os

class Config:
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'blog.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 应用配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # RSS配置
    SITE_TITLE = "Joomaen's Blog"
    SITE_DESCRIPTION = "A simple blog powered by Flask"
    SITE_URL = 'http://localhost:5000'  # 请在生产环境中修改为实际URL