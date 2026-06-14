# Docker支持

本项目支持Docker容器化部署。

## 快速启动

### 使用Docker Compose（推荐）

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 使用Docker

```bash
# 构建镜像
docker build -t alliance-pioneer .

# 运行容器
docker run -d \
  --name alliance-pioneer \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  alliance-pioneer

# 查看日志
docker logs -f alliance-pioneer

# 停止容器
docker stop alliance-pioneer
```

## 环境变量

可以在`docker-compose.yml`中配置环境变量：

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - OPENAI_API_KEY=your_key_here
  - DEEPSEEK_API_KEY=your_key_here
```

## 数据持久化

以下目录会持久化存储：

- `./data` - 数据库和知识库
- `./config` - 配置文件
- `./logs` - 日志文件

## Ollama集成

docker-compose.yml包含Ollama服务，如果已有本地Ollama，可以移除该服务。

### 下载模型

```bash
# 进入Ollama容器
docker exec -it ollama bash

# 下载模型
ollama pull mindchat
ollama pull qwen2.5-coder:1.5b
```

## 健康检查

容器包含健康检查，每30秒检查一次：

```bash
# 查看健康状态
docker inspect --format='{{.State.Health.Status}}' alliance-pioneer
```

## 性能调优

### 资源限制

```yaml
services:
  alliance-pioneer:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### 多实例部署

```bash
# 启动多个实例
docker-compose up -d --scale alliance-pioneer=3
```

## 生产环境建议

1. 使用环境变量管理敏感信息
2. 配置日志轮转
3. 设置资源限制
4. 使用外部数据库（如PostgreSQL）
5. 配置反向代理（如Nginx）