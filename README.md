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

pip install flask markdown gunicorn
```

3. 确认依赖安装
```
pip freeze
```

4. 在虚拟环境中启动应用
```
gunicorn --workers 3 app:app
```

5. 使用 Nginx 反代 Flask 应用

