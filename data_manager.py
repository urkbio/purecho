"""PurEcho 数据导入导出核心逻辑"""

import json
import os
from datetime import datetime

from models import db, Post, Tag


def _validate_backup(data):
    """验证备份文件的数据结构"""
    if not isinstance(data, dict) or 'posts' not in data or 'tags' not in data:
        raise ValueError('文件格式错误：缺少必要的数据字段')


def load_backup(source):
    """从路径或文件对象读取并验证备份数据"""
    source_path = None
    if isinstance(source, (str, os.PathLike)):
        source_path = os.fspath(source)
        if not os.path.isabs(source_path):
            backups_path = os.path.join(os.getcwd(), 'backups', source_path)
            current_path = os.path.join(os.getcwd(), source_path)
            if os.path.exists(backups_path):
                source_path = backups_path
            elif os.path.exists(current_path):
                source_path = current_path

        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = json.load(source)

    _validate_backup(data)
    return data, source_path


def export_data(output_file=None):
    """导出所有数据，返回文件路径、文章数和标签数"""
    posts = Post.query.all()
    tags = Tag.query.all()
    export_data = {
        'version': '1.0',
        'exported_at': datetime.now().isoformat(),
        'posts': [],
        'tags': []
    }

    for tag in tags:
        export_data['tags'].append({
            'id': tag.id,
            'name': tag.name
        })

    for post in posts:
        export_data['posts'].append({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'created_at': post.created_at.isoformat(),
            'updated_at': post.updated_at.isoformat(),
            'is_page': post.is_page,
            'slug': post.slug,
            'tags': [tag.name for tag in post.tags]
        })

    if not output_file:
        output_file = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    backups_dir = os.path.join(os.getcwd(), 'backups')
    os.makedirs(backups_dir, exist_ok=True)
    output_path = os.path.join(backups_dir, output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    return output_path, len(posts), len(tags)


def import_data(data):
    """将验证后的备份数据导入数据库，返回导入记录数"""
    _validate_backup(data)
    imported_count = 0

    try:
        tag_map = {}
        for tag_data in data.get('tags', []):
            existing_tag = Tag.query.filter_by(name=tag_data['name']).first()
            if not existing_tag:
                new_tag = Tag(name=tag_data['name'])
                db.session.add(new_tag)
                db.session.flush()
                tag_map[tag_data['id']] = new_tag.id
                imported_count += 1
            else:
                tag_map[tag_data['id']] = existing_tag.id

        for post_data in data.get('posts', []):
            existing_post = Post.query.filter_by(slug=post_data['slug']).first()
            if existing_post:
                continue

            new_post = Post(
                title=post_data['title'],
                content=post_data['content'],
                is_page=post_data['is_page'],
                slug=post_data['slug']
            )

            try:
                new_post.created_at = datetime.fromisoformat(post_data['created_at'])
                new_post.updated_at = datetime.fromisoformat(post_data['updated_at'])
            except (KeyError, TypeError, ValueError):
                pass

            for tag_name in post_data.get('tags', []):
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag:
                    new_post.tags.append(tag)

            db.session.add(new_post)
            imported_count += 1

        db.session.commit()
        return imported_count
    except Exception:
        db.session.rollback()
        raise
