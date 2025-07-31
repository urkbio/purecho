# 标准库
import os
import markdown
import json
from datetime import datetime
from functools import wraps

# 第三方库
from flask import Flask, render_template, request, redirect, url_for, Response, session, flash, send_file
from dotenv import load_dotenv

# 本地应用模块
from models import db, Post, Tag, AdminPassword

# 加载环境变量
load_dotenv()

from config import Config
from feed import generate_feed
from sitemap import generate_sitemap

app = Flask(__name__)
app.config.from_object(Config)
# 使用配置文件中的SECRET_KEY
app.secret_key = app.config['SECRET_KEY']
db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    per_page = 10
    pagination = Post.query.filter_by(is_page=False).order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items
    pages = Post.query.filter_by(is_page=True).all()
    current_year = datetime.now().year
    return render_template('index.html', posts=posts, pages=pages, year=current_year, pagination=pagination, config=app.config)

@app.route('/post/<slug>')
def post(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    content = markdown.markdown(post.content)
    current_year = datetime.now().year
    return render_template('post.html', title=post.title, content=content, year=current_year, post=post, config=app.config)

@app.route('/tag/<name>')
def tag(name):
    tag = Tag.query.filter_by(name=name).first_or_404()
    # 获取该标签下的所有文章，按创建时间倒序排列
    posts = Post.query.join(Post.tags).filter(Tag.name == name).order_by(Post.created_at.desc()).all()
    current_year = datetime.now().year
    return render_template('tag.html', tag=tag, posts=posts, year=current_year, config=app.config)

@app.route('/page/<slug>')
def page(slug):
    page = Post.query.filter_by(slug=slug, is_page=True).first_or_404()
    content = markdown.markdown(page.content)
    current_year = datetime.now().year
    return render_template('post.html', title=page.title, content=content, year=current_year, post=page, config=app.config)

@app.route('/feed.xml')
def feed():
    posts = Post.query.filter_by(is_page=False).order_by(Post.created_at.desc()).limit(10).all()
    feed_content = generate_feed(posts, Config())
    return Response(feed_content, mimetype='application/rss+xml')

@app.route('/sitemap.xml')
def sitemap():
    posts = Post.query.order_by(Post.updated_at.desc()).all()
    sitemap_content = generate_sitemap(posts, Config())
    return Response(sitemap_content, mimetype='application/xml')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        admin_pwd = AdminPassword.query.first()
        
        if admin_pwd and admin_pwd.check_password(password):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        flash('密码错误')
    
    current_year = datetime.now().year
    return render_template('login.html', year=current_year, config=app.config)

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    admin_pwd = AdminPassword.query.first()
    
    if admin_pwd and admin_pwd.check_password(old_password):
        admin_pwd.set_password(new_password)
        db.session.commit()
        flash('密码修改成功')
    else:
        flash('原密码错误')
    
    return redirect(url_for('admin'))

@app.route('/plog-admin')
@login_required
def admin():
    return redirect(url_for('admin_posts'))

@app.route('/plog-admin/password')
@login_required
def admin_password():
    current_year = datetime.now().year
    return render_template('admin_password.html', year=current_year, config=app.config)

@app.route('/plog-admin/write', methods=['GET', 'POST'])
@login_required
def admin_write():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content']
        tags = request.form['tags'].strip()
        is_page = 'is_page' in request.form
        slug = request.form['slug'].strip() or datetime.now().strftime('%Y-%m-%d-%H%M%S')
        
        post = Post(title=title, content=content, is_page=is_page, slug=slug)
        
        # 处理标签
        if tags:
            tag_names = [t.strip() for t in tags.split(',')]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                post.tags.append(tag)
        
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('admin_posts'))
    
    current_year = datetime.now().year
    return render_template('admin_write.html', year=current_year, config=app.config)

@app.route('/plog-admin/posts')
@login_required
def admin_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    current_year = datetime.now().year
    return render_template('admin_posts.html', posts=posts, year=current_year, config=app.config)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    post = Post.query.get_or_404(id)
    if request.method == 'POST':
        post.title = request.form['title'].strip()
        post.content = request.form['content']
        post.is_page = 'is_page' in request.form
        post.tags.clear()
        
        tags = request.form['tags'].strip()
        if tags:
            tag_names = [t.strip() for t in tags.split(',')]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                post.tags.append(tag)
        
        db.session.commit()
        
        # 自动清理没有文章的标签
        cleanup_empty_tags()
        
        return redirect(url_for('admin'))
    
    current_year = datetime.now().year
    return render_template('edit.html', post=post, year=current_year, config=app.config)

@app.route('/delete/<int:id>')
def delete(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    
    # 自动清理没有文章的标签
    cleanup_empty_tags()
    
    return redirect(url_for('admin'))

def cleanup_empty_tags():
    """自动清理没有文章的标签"""
    try:
        # 查找所有标签
        all_tags = Tag.query.all()
        deleted_count = 0
        
        for tag in all_tags:
            # 检查标签下是否有文章
            if tag.posts.count() == 0:
                db.session.delete(tag)
                deleted_count += 1
        
        if deleted_count > 0:
            db.session.commit()
            print(f'自动清理了 {deleted_count} 个空标签')
        
    except Exception as e:
        print(f'清理空标签时出错：{str(e)}')
        db.session.rollback()

@app.route('/tags')
def tags():
    # 获取所有标签，按名称排序
    tags = Tag.query.order_by(Tag.name).all()
    current_year = datetime.now().year
    return render_template('tags.html', tags=tags, year=current_year, config=app.config)

@app.route('/plog-admin/export')
@login_required
def admin_export():
    """导出所有数据为JSON文件"""
    try:
        # 获取所有数据
        posts = Post.query.all()
        tags = Tag.query.all()
        
        # 构建导出数据结构
        export_data = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'posts': [],
            'tags': []
        }
        
        # 导出标签
        for tag in tags:
            tag_data = {
                'id': tag.id,
                'name': tag.name
            }
            export_data['tags'].append(tag_data)
        
        # 导出文章
        for post in posts:
            post_data = {
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'created_at': post.created_at.isoformat(),
                'updated_at': post.updated_at.isoformat(),
                'is_page': post.is_page,
                'slug': post.slug,
                'tags': [tag.name for tag in post.tags]
            }
            export_data['posts'].append(post_data)
        
        # 创建临时文件到backups文件夹
        export_filename = f'plog_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        export_path = os.path.join(os.getcwd(), 'backups', export_filename)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        flash(f'数据导出成功！文件：{export_filename}')
        return send_file(export_path, as_attachment=True, download_name=export_filename)
        
    except Exception as e:
        flash(f'导出失败：{str(e)}')
        return redirect(url_for('admin'))

@app.route('/plog-admin/import', methods=['GET', 'POST'])
@login_required
def admin_import():
    """导入JSON数据文件"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择要导入的文件')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('请选择要导入的文件')
            return redirect(request.url)
        
        if not file.filename.endswith('.json'):
            flash('请选择JSON格式的文件')
            return redirect(request.url)
        
        try:
            # 读取JSON文件
            import_data = json.load(file)
            
            # 验证数据格式
            if not isinstance(import_data, dict) or 'posts' not in import_data or 'tags' not in import_data:
                flash('文件格式错误：缺少必要的数据字段')
                return redirect(request.url)
            
            # 开始导入
            imported_count = 0
            
            # 导入标签
            tag_map = {}  # 用于映射旧ID到新ID
            for tag_data in import_data.get('tags', []):
                existing_tag = Tag.query.filter_by(name=tag_data['name']).first()
                if not existing_tag:
                    new_tag = Tag(name=tag_data['name'])
                    db.session.add(new_tag)
                    db.session.flush()  # 获取新ID
                    tag_map[tag_data['id']] = new_tag.id
                    imported_count += 1
                else:
                    tag_map[tag_data['id']] = existing_tag.id
            
            # 导入文章
            for post_data in import_data.get('posts', []):
                # 检查是否已存在相同slug的文章
                existing_post = Post.query.filter_by(slug=post_data['slug']).first()
                if existing_post:
                    # 如果存在，跳过或更新（这里选择跳过）
                    continue
                
                # 创建新文章
                new_post = Post(
                    title=post_data['title'],
                    content=post_data['content'],
                    is_page=post_data['is_page'],
                    slug=post_data['slug']
                )
                
                # 设置时间
                try:
                    new_post.created_at = datetime.fromisoformat(post_data['created_at'])
                    new_post.updated_at = datetime.fromisoformat(post_data['updated_at'])
                except:
                    pass  # 使用默认时间
                
                # 添加标签
                for tag_name in post_data.get('tags', []):
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if tag:
                        new_post.tags.append(tag)
                
                db.session.add(new_post)
                imported_count += 1
            
            db.session.commit()
            flash(f'数据导入成功！共导入 {imported_count} 条记录')
            
        except json.JSONDecodeError:
            flash('文件格式错误：不是有效的JSON文件')
        except Exception as e:
            db.session.rollback()
            flash(f'导入失败：{str(e)}')
        
        return redirect(url_for('admin'))
    
    current_year = datetime.now().year
    return render_template('admin_import.html', year=current_year, config=app.config)

if __name__ == '__main__':
    app.run(debug=True)
