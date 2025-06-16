# 使用官方 Python 镜像（建议3.12，确保与本地开发一致）
FROM python:3.12-slim-bookworm

ENV LANG=C.UTF-8 \
    TZ=Asia/Shanghai

# 安装 tzdata 并设置时区
RUN apt-get update && apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件到容器中
COPY ./src ./src
COPY ./pyproject.toml ./
COPY ./README.md ./

# 建议先安装 pipx 以便用 PEP 517/518 构建
RUN pip install --upgrade pip

# 安装项目依赖（推荐使用 PEP 517/518 标准，支持 pyproject.toml）
RUN pip install -e .

ENTRYPOINT ["cli", "hello"]