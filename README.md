# PurEcho

非常极简的博客

### 部署

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

### 停止/重启

```
# 查看对应端口运行程序的 PID
lsof -i :5000

kill {PID}

# 重新启动
source venv/bin/activate

nohup gunicorn --workers 3 -b 0.0.0.0:5000 app:app > gunicorn.log 2>&1 &

```

#### 如果自己修改了模板文件的话，使用以下方式先临时保留本地改动，pull 之后再合并回去
```
git stash
git pull
git stash pop
```
到这里只是恢复回来，但是不会提交，接着执行：
```
git status
git diff
git add XXX
git commit -m "Merge Local Code"

```

#### 或者直接这样
```
git pull --rebase
```