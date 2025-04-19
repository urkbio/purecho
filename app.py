from flask import Flask, render_template, request, redirect, url_for
import os
import markdown
from datetime import datetime

app = Flask(__name__)
POST_DIR = 'posts'

@app.route('/')
def index():
    posts = []
    for filename in sorted(os.listdir(POST_DIR), reverse=True):
        if filename.endswith('.md'):
            with open(os.path.join(POST_DIR, filename), 'r') as f:
                first_line = f.readline().strip()
            slug = filename[:-3]
            posts.append({'title': first_line, 'slug': slug})
    # 获取当前年份
    current_year = datetime.now().year

    return render_template('index.html', posts=posts, year=current_year)

@app.route('/post/<slug>')
def post(slug):
    path = os.path.join(POST_DIR, slug + '.md')
    if not os.path.exists(path):
        return '404 Not Found', 404
    with open(path, 'r') as f:
        lines = f.readlines()
    title = lines[0].strip()
    content = markdown.markdown(''.join(lines[1:]))
    return render_template('post.html', title=title, content=content)

# Joomaen SHA256加密小写
@app.route('/5f807bd5c7e70ed44f63449650207122eeb1eee910c67c80e24bbb83e7241228', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content']
        now = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        filename = f"{now}.md"
        with open(os.path.join(POST_DIR, filename), 'w') as f:
            f.write(title + '\n' + content)
        return redirect(url_for('index'))
    return render_template('admin.html')

if __name__ == '__main__':
    os.makedirs(POST_DIR, exist_ok=True)
    app.run(debug=True)
