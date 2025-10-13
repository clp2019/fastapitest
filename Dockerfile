# 使用官方 Python 3.13 镜像，也可改为 3.12
FROM python:3.12


# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
COPY ./app /app/app
COPY .env env

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt pydantic[email] pydantic-settings python-multipart


# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动 FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


