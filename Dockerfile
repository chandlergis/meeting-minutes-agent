FROM python:3.11-slim

WORKDIR /app

# 复制项目文件
COPY requirements.txt .
COPY config/ ./config/
COPY core/ ./core/
COPY utils/ ./utils/
COPY app.py .

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 暴露端口
EXPOSE 8502

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]