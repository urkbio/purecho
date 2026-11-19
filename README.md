# PurEcho

非常极简的博客

### Windows 本地调试

Windows 下直接使用 Flask 内置开发服务器，无需使用 Gunicorn。在项目根目录执行：

```powershell
# 首次创建并激活虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 首次运行：复制配置并初始化数据库
Copy-Item .env.example .env
python init_db.py

# 启动调试程序
python app.py
```

启动后访问 `http://127.0.0.1:5000`。

### Linux 服务器部署

1. 进入文件夹并创建虚拟环境
```
cd purecho
python3 -m venv venv 
```

2. 激活虚拟环境，安装依赖

```
source venv/bin/activate

pip install -r requirements.txt
```

3. 确认依赖安装
```
pip freeze
```

4. 配置环境变量
```
# 复制环境变量示例文件
cp .env.example .env

# 编辑.env文件，修改必要的配置
vim .env
```

5. 运行初始化脚本
```
python init_db.py
```

6. 在虚拟环境中启动应用
```
gunicorn --workers 3 -b 0.0.0.0:5000 app:app

# 后台运行
nohup gunicorn --workers 3 -b 0.0.0.0:5000 app:app > gunicorn.log 2>&1 &
```

7. 使用 Nginx 反代 Flask 应用

### Linux 停止/重启

```
# 查看对应端口运行程序的 PID
lsof -i :5000

kill {PID}

# 重新启动
source venv/bin/activate

nohup gunicorn --workers 3 -b 0.0.0.0:5000 app:app > gunicorn.log 2>&1 &

```

### 数据备份与恢复

网页及命令行的数据导出、导入方法，以及备份文件格式和注意事项，请参阅 [BACKUP_README.md](BACKUP_README.md)。

### 自定义代码
写在 `templates/_local_head.html` 比如统计代码、广告、字体...