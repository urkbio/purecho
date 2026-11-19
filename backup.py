#!/usr/bin/env python3
"""
PurEcho 数据备份工具
支持导出和导入所有博客数据
"""

import os
import sys
import json
import argparse

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.data_manager import export_data as export_backup_data
from services.data_manager import import_data as import_backup_data
from services.data_manager import load_backup


def export_data(output_file=None):
    """导出所有数据到JSON文件"""
    with app.app_context():
        try:
            output_path, post_count, tag_count = export_backup_data(output_file)
            display_file = output_file or os.path.basename(output_path)

            print('✅ 数据导出成功！')
            print(f'📁 文件：backups/{display_file}')
            print(f'📊 统计：{post_count} 篇文章，{tag_count} 个标签')
        except Exception as e:
            print(f'❌ 导出失败：{str(e)}')
            return False

    return True


def import_data(input_file, force=False):
    """从JSON文件导入数据"""
    with app.app_context():
        try:
            backup_data, source_path = load_backup(input_file)
            print(f'📖 正在读取备份文件：{source_path or input_file}')
            print(f'📊 备份包含：{len(backup_data["posts"])} 篇文章，{len(backup_data["tags"])} 个标签')

            if not force:
                confirm = input('⚠️  这将导入数据到当前数据库，是否继续？(y/N): ')
                if confirm.lower() != 'y':
                    print('❌ 操作已取消')
                    return False

            imported_count = import_backup_data(backup_data)
            print(f'✅ 数据导入成功！共导入 {imported_count} 条记录')
        except FileNotFoundError:
            print(f'❌ 文件不存在：{input_file}')
            print('💡 提示：可以尝试将文件放在 backups/ 文件夹中')
            return False
        except json.JSONDecodeError:
            print('❌ 文件格式错误：不是有效的JSON文件')
            return False
        except ValueError as e:
            print(f'❌ {str(e)}')
            return False
        except Exception as e:
            print(f'❌ 导入失败：{str(e)}')
            return False

    return True


def main():
    parser = argparse.ArgumentParser(description='PurEcho 数据备份工具')
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
