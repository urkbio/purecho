# 标准库
import os
import markdown
from datetime import datetime
from functools import wraps

# 第三方库
from flask import Flask, render_template, request, redirect, url_for, Response, session, flash
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
    return render_template('index.html', posts=posts, pages=pages, year=current_year, pagination=pagination)

@app.route('/post/<slug>')
def post(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    content = markdown.markdown(post.content)
    current_year = datetime.now().year
    return render_template('post.html', title=post.title, content=content, year=current_year, post=post)

@app.route('/tag/<name>')
def tag(name):
    tag = Tag.query.filter_by(name=name).first_or_404()
    current_year = datetime.now().year
    return render_template('tag.html', tag=tag, year=current_year)

@app.route('/page/<slug>')
def page(slug):
    page = Post.query.filter_by(slug=slug, is_page=True).first_or_404()
    content = markdown.markdown(page.content)
    current_year = datetime.now().year
    return render_template('post.html', title=page.title, content=content, year=current_year, post=page)

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
    return render_template('login.html', year=current_year)

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
    return render_template('admin_password.html', year=current_year)

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
    return render_template('admin_write.html', year=current_year)

@app.route('/plog-admin/posts')
@login_required
def admin_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    current_year = datetime.now().year
    return render_template('admin_posts.html', posts=posts, year=current_year)

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
        return redirect(url_for('admin'))
    
    current_year = datetime.now().year
    return render_template('edit.html', post=post, year=current_year)

@app.route('/delete/<int:id>')
def delete(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
