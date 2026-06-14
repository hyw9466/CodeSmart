# 服务器部署指南

## 一、登录服务器

```bash
# 使用 SSH 登录服务器
ssh root@139.224.163.81

# 输入密码登录
```

## 二、拉取代码

```bash
# 进入项目目录
cd /root/CodeSmart

# 如果是首次部署，克隆仓库
git clone https://github.com/hyw9466/CodeSmart.git

# 如果已有仓库，拉取最新代码
cd CodeSmart
git pull origin main
```

## 三、配置环境变量

```bash
# 复制配置文件模板
cp .env.example .env

# 编辑配置文件（输入你的 API Key）
nano .env
```

配置内容说明：

```env
# 阿里云 DashScope 嵌入模型（文档向量化用）
EMBEDDING_MODEL=text-embedding-v4

# 阿里云 DashScope（LLM 问答用）
DASHSCOPE_API_KEY=your-dashscope-api-key-here
LLM_MODEL=qwen3.6-plus
```

## 四、启动服务

### 方式一：Docker Compose（推荐）

```bash
# 构建并启动容器
docker compose up -d --build

# 查看容器状态
docker compose ps

# 查看日志
docker logs code-analysis-assistant -f

# 停止服务
docker compose down
```

### 方式二：手动运行

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 五、访问服务

```bash
# 服务启动后，访问地址
# http://139.224.163.81:8000

# 健康检查
curl http://localhost:8000/health
```

## 六、常用命令

```bash
# 重启服务
docker compose restart

# 查看运行日志
docker logs -f code-analysis-assistant --tail 100

# 进入容器
docker exec -it code-analysis-assistant /bin/bash

# 备份数据
tar -czf backup.tar.gz vectorstore uploads chat_history
```

---

## 附录：注意事项

### 1. 端口安全

- 默认端口：8000
- 确保防火墙开放此端口
- 生产环境建议配置 Nginx 反向代理 + HTTPS

### 2. 数据持久化

容器会自动挂载以下目录：
- `./data/vectorstore` - 向量索引（FAISS）
- `./data/uploads` - 上传的文档
- `./data/chat_history` - 对话历史

### 3. API Key 安全

- 不要将 API Key 提交到 Git
- 定期更换 API Key
- 监控 API 使用量

### 4. 性能优化

- 建议服务器配置：2核4G以上
- 上传大文件时可能需要调整超时时间
- 定期清理不需要的文档

### 5. 常见问题

**问题**：容器启动失败
**解决**：检查 .env 文件配置是否正确

**问题**：访问超时
**解决**：检查防火墙设置，确认端口开放

**问题**：文档上传失败
**解决**：检查文件格式是否支持（.docx/.pdf/.txt/.md）

### 6. 升级步骤

```bash
# 1. 停止服务
docker compose down

# 2. 拉取最新代码
git pull origin main

# 3. 更新配置（如有必要）
cp .env.example .env.new
# 对比并合并配置

# 4. 重新构建并启动
docker compose up -d --build
```