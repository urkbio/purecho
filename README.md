# plog

非常极简的博客

### 部署

1. 进入文件夹并创建虚拟环境
```
cd plog
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

4. 运行初始化脚本
```
python init_db.py
```

5. 在虚拟环境中启动应用
```
gunicorn --workers 3 -b 0.0.0.0:5000 app:app

# 后台运行
nohup gunicorn --workers 3 -b 0.0.0.0:5000 app:app > gunicorn.log 2>&1 &
```

6. 使用 Nginx 反代 Flask 应用

### 停止/重启

```
# 查看对应端口运行程序的 PID
lsof -i :5000

kill {PID}

# 重新启动
gunicorn --workers 3 -b 0.0.0.0:5000 app:app

```
