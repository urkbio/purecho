# 标准库
import os
import json
import nh3
from datetime import datetime
from functools import wraps

# 第三方库
from flask import Flask, render_template, request, redirect, url_for, Response, session, flash, send_file
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy.pagination import Pagination


# 本地应用模块
from models import db, Post, Tag, AdminPassword
from services.data_manager import export_and_clear_data, export_data, import_data, load_backup
from services.markdown import render_html
from services.search import search_posts

# 加载环境变量
load_dotenv()

from config import Config
from feed import generate_feed
from sitemap import generate_sitemap

app = Flask(__name__)
app.config.from_object(Config)
# 使用配置文件中的SECRET_KEY
app.secret_key = app.config['SECRET_KEY']
# 启用 CSRF 全局保护
csrf = CSRFProtect(app)

db.init_app(app)


_EMBEDDED_RESIZE_SCRIPT = """
<script>
(function () {
    function sendHeight() {
        var height = Math.max(
            document.body ? document.body.scrollHeight : 0,
            document.documentElement.scrollHeight,
            document.body ? document.body.offsetHeight : 0,
            document.documentElement.offsetHeight
        );
        parent.postMessage({type: 'purecho-embedded-resize', height: height}, '*');
    }

    if (window.ResizeObserver) {
        var observer = new ResizeObserver(sendHeight);
        observer.observe(document.documentElement);
        if (document.body) {
            observer.observe(document.body);
        }
    }
    window.addEventListener('load', sendHeight);
    sendHeight();
})();
</script>
"""


class SearchPagination(Pagination):
    """为内存搜索结果提供与 ORM 分页一致的接口。"""

    def __init__(self, items, **kwargs):
        self._all_items = items
        super().__init__(**kwargs)

    def _query_items(self):
        start = (self.page - 1) * self.per_page
        return self._all_items[start:start + self.per_page]

    def _query_count(self):
        return len(self._all_items)


def _search_pagination(query, page, per_page, order_by):
    posts = Post.query.filter_by(is_page=False).order_by(order_by).all()
    results = search_posts(posts, query)
    return SearchPagination(results, page=page, per_page=per_page, error_out=False)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def render_markdown(text):
    html = render_html(text)

    return nh3.clean(
        html,
        tags={
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'br', 'hr', 'blockquote',
            'strong', 'em', 'del',
            'ul', 'ol', 'li',
            'pre', 'code',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'a', 'img'
        },
        attributes={
            'a': {'href', 'title'},
            'img': {'src', 'alt', 'title'}
        },
        tag_attribute_values={
            'th': {'style': {'text-align: left', 'text-align: center', 'text-align: right'}},
            'td': {'style': {'text-align: left', 'text-align: center', 'text-align: right'}}
        },
        url_schemes={'http', 'https', 'mailto'}
    )

@app.context_processor
def inject_navigation_pages():
    return {'pages': Post.query.filter_by(is_page=True).all()}

@app.route('/')
def index():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = 16
    query = request.args.get('q', '').strip()

    if query:
        pagination = _search_pagination(query, page, per_page, Post.created_at.desc())
        search_results = pagination.items
        posts = [result['post'] for result in search_results]
    else:
        pagination = Post.query.filter_by(is_page=False).order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        posts = pagination.items
        search_results = []

    current_year = datetime.now().year
    return render_template(
        'index.html', posts=posts, year=current_year, pagination=pagination,
        config=app.config, query=query, search_results=search_results
    )

@app.route('/post/<slug>')
def post(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    content = render_markdown(post.content)
    current_year = datetime.now().year
    return render_template('post.html', title=post.title, content=content, raw_html=None, year=current_year, post=post, config=app.config)

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
    source = page.content.lstrip('\ufeff \t\r\n')
    is_embedded = source.lower().startswith(('<!doctype html', '<html'))
    raw_html = (page.content + _EMBEDDED_RESIZE_SCRIPT) if is_embedded else None
    content = render_markdown(page.content) if raw_html is None else None
    current_year = datetime.now().year
    return render_template('post.html', title=page.title, content=content, raw_html=raw_html, year=current_year, post=page, config=app.config)

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

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

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

@app.route('/admin')
@login_required
def admin():
    return redirect(url_for('admin_posts'))

@app.route('/admin/password')
@login_required
def admin_password():
    current_year = datetime.now().year
    return render_template('admin_password.html', year=current_year, config=app.config)

@app.route('/admin/write', methods=['GET', 'POST'])
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

@app.route('/admin/posts')
@login_required
def admin_posts():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    query = request.args.get('q', '').strip()

    if query:
        pagination = _search_pagination(query, page, per_page, Post.updated_at.desc())
        search_results = pagination.items
        posts = [result['post'] for result in search_results]
    else:
        pagination = Post.query.filter_by(is_page=False).order_by(Post.updated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        posts = pagination.items
        search_results = []

    current_year = datetime.now().year
    return render_template(
        'admin_posts.html', posts=posts, pagination=pagination,
        view_type='posts', year=current_year, config=app.config,
        query=query, search_results=search_results
    )

@app.route('/admin/pages')
@login_required
def admin_pages():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Post.query.filter_by(is_page=True).order_by(Post.updated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    pages = pagination.items
    current_year = datetime.now().year
    return render_template('admin_posts.html', posts=pages, pagination=pagination, view_type='pages', year=current_year, config=app.config)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
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

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
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

@app.route('/api/tags')
@login_required
def api_tags():
    """返回所有标签的JSON列表，用于标签自动提示"""
    tags = Tag.query.order_by(Tag.name).all()
    tag_list = [tag.name for tag in tags]
    return {'tags': tag_list}

@app.route('/admin/export', methods=['GET', 'POST'])
@login_required
def admin_export():
    """显示导出选项或导出所有数据为JSON文件"""
    if request.method == 'GET':
        current_year = datetime.now().year
        return render_template('admin_export.html', year=current_year, config=app.config)

    try:
        export_path, _, _ = export_data()
        export_filename = os.path.basename(export_path)
        flash(f'数据导出成功！文件：{export_filename}')
        return send_file(export_path, as_attachment=True, download_name=export_filename)

    except Exception as e:
        flash(f'导出失败：{str(e)}')
        return redirect(url_for('admin_export'))


@app.route('/admin/export/clear', methods=['POST'])
@login_required
def admin_export_clear():
    """验证备份后清空全部文章、页面和标签"""
    if request.form.get('confirm_clear') != '1':
        flash('请先确认已了解清空范围，再执行导出并清空')
        return redirect(url_for('admin_export'))

    try:
        export_path, post_count, tag_count = export_and_clear_data()
    except Exception as e:
        flash(f'导出并清空失败：{str(e)}')
        return redirect(url_for('admin_export'))

    export_filename = os.path.basename(export_path)
    flash(
        f'数据导出并清空成功！文件：{export_filename}；'
        f'共备份 {post_count} 条内容记录和 {tag_count} 个标签'
    )
    return send_file(export_path, as_attachment=True, download_name=export_filename)

@app.route('/admin/import', methods=['GET', 'POST'])
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
            backup_data, _ = load_backup(file)
            imported_count = import_data(backup_data)
            flash(f'数据导入成功！共导入 {imported_count} 条记录')

        except json.JSONDecodeError:
            flash('文件格式错误：不是有效的JSON文件')
        except ValueError as e:
            flash(str(e))
        except Exception as e:
            flash(f'导入失败：{str(e)}')
        
        return redirect(url_for('admin'))
    
    current_year = datetime.now().year
    return render_template('admin_import.html', year=current_year, config=app.config)

if __name__ == '__main__':
    app.run(debug=True)
