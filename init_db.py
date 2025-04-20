from app import app, db, AdminPassword

def init_database():
    with app.app_context():
        # 创建所有数据库表
        db.create_all()
        
        # 检查是否已存在管理员密码
        if not AdminPassword.query.first():
            print('正在创建管理员账户...')
            admin_pwd = AdminPassword()
            admin_pwd.set_password('admin')  # 设置初始密码为'admin'
            db.session.add(admin_pwd)
            db.session.commit()
            print('管理员账户创建成功！初始密码为: admin')
        else:
            print('管理员账户已存在，跳过初始化。')

if __name__ == '__main__':
    print('开始初始化数据库...')
    init_database()
    print('数据库初始化完成！')