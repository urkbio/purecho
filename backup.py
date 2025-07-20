#!/usr/bin/env python3
"""
Plog 数据备份工具
支持导出和导入所有博客数据
"""

import os
import sys
import json
import argparse
from datetime import datetime

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Post, Tag

def export_data(output_file=None):
    """导出所有数据到JSON文件"""
    with app.app_context():
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
            
            # 生成文件名到backups文件夹
            if not output_file:
                output_file = f'plog_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            # 确保backups文件夹存在
            backups_dir = os.path.join(os.getcwd(), 'backups')
            os.makedirs(backups_dir, exist_ok=True)
            
            # 写入文件到backups文件夹
            output_path = os.path.join(backups_dir, output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f'✅ 数据导出成功！')
            print(f'📁 文件：backups/{output_file}')
            print(f'📊 统计：{len(posts)} 篇文章，{len(tags)} 个标签')
            
        except Exception as e:
            print(f'❌ 导出失败：{str(e)}')
            return False
    
    return True

def import_data(input_file, force=False):
    """从JSON文件导入数据"""
    with app.app_context():
        try:
            # 检查文件路径
            if not os.path.isabs(input_file):
                # 如果不是绝对路径，先尝试在backups文件夹中查找
                backups_path = os.path.join(os.getcwd(), 'backups', input_file)
                if os.path.exists(backups_path):
                    input_file = backups_path
                else:
                    # 如果backups文件夹中没有，尝试当前目录
                    current_path = os.path.join(os.getcwd(), input_file)
                    if os.path.exists(current_path):
                        input_file = current_path
            
            # 读取JSON文件
            with open(input_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 验证数据格式
            if not isinstance(import_data, dict) or 'posts' not in import_data or 'tags' not in import_data:
                print('❌ 文件格式错误：缺少必要的数据字段')
                return False
            
            print(f'📖 正在读取备份文件：{input_file}')
            print(f'📊 备份包含：{len(import_data["posts"])} 篇文章，{len(import_data["tags"])} 个标签')
            
            if not force:
                confirm = input('⚠️  这将导入数据到当前数据库，是否继续？(y/N): ')
                if confirm.lower() != 'y':
                    print('❌ 操作已取消')
                    return False
            
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
                    print(f'  ➕ 创建标签：{tag_data["name"]}')
                else:
                    tag_map[tag_data['id']] = existing_tag.id
                    print(f'  ⏭️  跳过已存在标签：{tag_data["name"]}')
            
            # 导入文章
            for post_data in import_data.get('posts', []):
                # 检查是否已存在相同slug的文章
                existing_post = Post.query.filter_by(slug=post_data['slug']).first()
                if existing_post:
                    print(f'  ⏭️  跳过已存在文章：{post_data["title"]}')
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
                print(f'  ➕ 导入文章：{post_data["title"]}')
            
            db.session.commit()
            print(f'✅ 数据导入成功！共导入 {imported_count} 条记录')
            
        except FileNotFoundError:
            print(f'❌ 文件不存在：{input_file}')
            print('💡 提示：可以尝试将文件放在 backups/ 文件夹中')
            return False
        except json.JSONDecodeError:
            print('❌ 文件格式错误：不是有效的JSON文件')
            return False
        except Exception as e:
            db.session.rollback()
            print(f'❌ 导入失败：{str(e)}')
            return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Plog 数据备份工具')
    parser.add_argument('action', choices=['export', 'import'], help='操作类型')
    parser.add_argument('file', nargs='?', help='文件路径')
    parser.add_argument('--force', '-f', action='store_true', help='强制导入（跳过确认）')
    
    args = parser.parse_args()
    
    if args.action == 'export':
        export_data(args.file)
    elif args.action == 'import':
        if not args.file:
            print('❌ 导入操作需要指定文件路径')
            sys.exit(1)
        import_data(args.file, args.force)

if __name__ == '__main__':
    main() 