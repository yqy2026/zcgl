# 生产环境 Docker 配置
# 专为地产资产管理系统优化的多阶段构建，支持高并发部署

# 构建阶段
FROM python:3.12-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 UV 包管理器
RUN pip install --upgrade pip && \
    pip install uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 创建虚拟环境并安装依赖
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache -r uv.lock

# 生产阶段
FROM python:3.12-slim as production

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    supervisor \
    nginx \
    tini \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建应用用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY backend/src ./src
COPY backend/pyproject.toml .
COPY backend/uv.lock .

# 创建必要的目录
RUN mkdir -p /app/logs \
             /app/data \
             /app/uploads \
             /app/cache \
             /app/static \
             /app/ssl && \
    chown -R appuser:appuser /app

# 编译 Python 字节码
RUN python -m compileall src/ && \
    find src/ -name "*.pyc" -delete

# 复制配置文件
COPY docker/production/supervisor.conf /etc/supervisor/conf.d/supervisor.conf
COPY docker/production/nginx-site.conf /etc/nginx/sites-available/default

# 复制启动脚本
COPY docker/production/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 创建非 root 用户使用
RUN touch /app/uwsgi.log && \
    chown appuser:appuser /app/uwsgi.log

# 暴露端口
EXPOSE 8002 80 443

# 切换到非 root 用户
USER appuser

# 设置环境变量
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai
ENV LANG=zh_CN.UTF-8
ENV LC_ALL=zh_CN.UTF-8

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/api/v1/health || exit 1

# 启动命令
ENTRYPOINT ["/entrypoint.sh"]

# 默认命令
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisor.conf"]