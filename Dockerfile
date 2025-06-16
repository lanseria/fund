# Dockerfile

# --- Stage 1: Builder ---
# 使用官方 Python 镜像作为基础
FROM docker.m.daocloud.io/python:3.12-slim-bookworm AS builder

# 设置环境变量，提升Docker内Python应用的性能和稳定性
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    # 告诉 uv 在构建时不要使用缓存，保持构建环境纯净
    UV_NO_CACHE=1

# (可选，但推荐) 设置 apt 使用国内镜像源
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# 安装 tzdata 并设置时区
RUN apt-get update && apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 使用 pip 安装 uv (使用国内源加速)
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple

# 利用 Docker 层缓存：先复制配置文件并安装依赖
COPY ./pyproject.toml ./
RUN uv pip install --system --no-cache . -i https://pypi.tuna.tsinghua.edu.cn/simple

# --- Stage 2: Final Image ---
# 使用一个干净的基础镜像来减小最终镜像体积
FROM docker.m.daocloud.io/python:3.12-slim-bookworm AS final

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8

# 从 builder 阶段复制时区信息
COPY --from=builder /etc/localtime /etc/localtime
COPY --from=builder /usr/share/zoneinfo/${TZ} /usr/share/zoneinfo/${TZ}

# 创建一个非 root 用户来运行应用，增强安全性
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser
WORKDIR /home/appuser/app

# 从 builder 阶段复制已安装的依赖
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用源代码和启动脚本
COPY --chown=appuser:appgroup ./src ./src
COPY --chown=appuser:appgroup ./run_scheduler.py ./

# EXPOSE 端口（仅用于文档目的，实际端口映射在 docker-compose.yml 中定义）
EXPOSE 8000