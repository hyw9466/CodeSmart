# CodeLens 阿里云部署指南

本指南将帮助你将 CodeLens 代码分析助手部署到阿里云 ECS 服务器。

## 📋 目录

- [部署方案对比](#部署方案对比)
- [方案一：Docker 容器化部署（推荐）](#方案一 docker-容器化部署推荐)
- [方案二：手动部署](#方案二手动部署)
- [常见问题](#常见问题)

---

## 部署方案对比

| 方案 | 适用场景 | 优点 | 缺点 |
|-----|---------|------|------|
| **Docker 容器化** | 生产环境、团队协作 | 环境一致、易扩缩容、一键部署 | 需要学习 Docker |
| **手动部署** | 个人项目、学习测试 | 完全控制、资源占用少 | 配置复杂、易出错 |

---

## 方案一：Docker 容器化部署（推荐）

### 步骤 1：准备阿里云 ECS 服务器

#### 1.1 创建实例

1. 登录 [阿里云 ECS 控制台](https://ecs.console.aliyun.com/)
2. 点击"创建实例"
3. **推荐配置**：
   ```
   地域：华东 1（杭州）或离用户最近的区域
   镜像：Ubuntu 22.04 LTS 或 CentOS 7.9
   实例规格：2 核 4GB（最低 2 核 2GB）
   存储：40GB ESSD 云盘
   网络：VPC 专有网络
   带宽：按使用流量计费（1-5 Mbps）
   ```

#### 1.2 配置安全组

在阿里云控制台配置安全组规则：

| 端口范围 | 授权对象 | 说明 |
|---------|---------|------|
| 22/tcp | 0.0.0.0/0 | SSH 远程连接 |
| 80/tcp | 0.0.0.0/0 | HTTP 访问 |
| 443/tcp | 0.0.0.0/0 | HTTPS 访问 |

### 步骤 2：连接服务器

#### 方式一：使用 SSH 客户端（推荐）

```bash
# Windows 用户可使用 PowerShell 或 PuTTY
ssh root@你的服务器公网 IP

# 首次连接会提示确认指纹，输入 yes
# 然后输入密码（输入时不显示）
```

#### 方式二：阿里云 Workbench

1. 登录阿里云控制台
2. 进入 ECS 实例列表
3. 点击"远程连接" -> "Workbench"

### 步骤 3：上传项目文件

#### 方式一：使用 Git（推荐）

```bash
# 在服务器上安装 Git
yum install -y git  # CentOS
apt install -y git  # Ubuntu

# 克隆项目
git clone https://github.com/你的用户名/CodeLens.git
cd CodeLens
```

#### 方式二：使用 SCP 上传

```bash
# 在本地 PowerShell 执行
scp -r ./* root@你的服务器公网 IP:/root/CodeLens
```

#### 方式三：使用宝塔面板

1. 安装宝塔面板：
   ```bash
   yum install -y wget && wget -O install.sh http://download.bt.cn/install/install_6.0.sh && sh install.sh
   ```
2. 登录面板，使用文件管理功能上传

### 步骤 4：配置环境变量

```bash
# 编辑 .env 文件
cd CodeLens
nano .env

# 修改以下内容：
DASHSCOPE_API_KEY=你的阿里云 API Key
LLM_MODEL=qwen3.6-plus
EMBEDDING_MODEL=tongyi-embedding-vision-plus
```

**获取 API Key**：
1. 访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 开通服务并创建 API Key
3. 复制 Key 到 `.env` 文件

### 步骤 5：一键部署

```bash
# 赋予执行权限
chmod +x deploy.sh

# 执行部署脚本
sudo ./deploy.sh
```

部署脚本会自动完成：
- ✅ 更新系统
- ✅ 安装 Docker
- ✅ 构建镜像
- ✅ 启动服务

### 步骤 6：验证部署

```bash
# 查看服务状态
docker ps

# 查看运行日志
docker logs -f code-analysis-assistant

# 测试健康检查
curl http://localhost:8000/health

# 应该返回：{"status":"ok","version":"0.2.0"}
```

### 步骤 7：访问服务

打开浏览器访问：
```
http://你的服务器公网 IP
http://你的服务器公网 IP/docs  # API 文档
```

---

## 方案二：手动部署

### 步骤 1：安装依赖

```bash
# 安装 Python 3.11
yum install -y python3.11  # CentOS
apt install -y python3.11 python3.11-venv python3-pip  # Ubuntu

# 安装 Node.js（用于构建前端）
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -  # CentOS
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -  # Ubuntu
yum install -y nodejs  # CentOS
apt install -y nodejs  # Ubuntu
```

### 步骤 2：构建前端

```bash
cd web
npm install
npm run build
cd ..
```

### 步骤 3：安装 Python 依赖

```bash
# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤 4：创建 Systemd 服务

```bash
sudo nano /etc/systemd/system/codelens.service
```

写入以下内容：

```ini
[Unit]
Description=CodeLens Code Analysis Assistant
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/CodeLens
Environment="PATH=/root/CodeLens/venv/bin"
ExecStart=/root/CodeLens/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 步骤 5：启动服务

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start codelens
sudo systemctl enable codelens

# 查看状态
sudo systemctl status codelens
```

### 步骤 6：配置 Nginx 反向代理（可选）

```bash
# 安装 Nginx
yum install -y nginx  # CentOS
apt install -y nginx  # Ubuntu

# 配置
sudo nano /etc/nginx/conf.d/codelens.conf
```

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# 重启 Nginx
sudo systemctl restart nginx
```

---

## 常见问题

### Q1: 服务无法访问

**检查安全组**：
```bash
# 查看端口监听
netstat -tlnp | grep :8000
```

确保阿里云安全组已开放 8000 端口。

### Q2: Docker 容器启动失败

```bash
# 查看日志
docker logs code-analysis-assistant

# 重启容器
docker compose restart

# 重新构建
docker compose build --no-cache
docker compose up -d
```

### Q3: API Key 无效

确保 `.env` 文件配置正确：
```bash
# 验证配置
docker exec code-analysis-assistant cat /app/.env
```

### Q4: 内存不足

调整 `docker-compose.yml` 中的资源限制：
```yaml
mem_limit: 1g  # 降低内存限制
cpus: 1.0
```

### Q5: 向量数据库加载慢

首次启动会加载知识库，需要等待 3-5 分钟。可以查看日志：
```bash
docker logs -f code-analysis-assistant
```

---

## 部署后维护

### 查看日志

```bash
# 实时日志
docker logs -f code-analysis-assistant

# 最近 100 行
docker logs --tail 100 code-analysis-assistant
```

### 更新代码

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker compose build --no-cache
docker compose up -d
```

### 备份数据

```bash
# 备份向量数据库
tar -czf faiss_backup.tar.gz vectorstore/faiss_index

# 备份聊天记录
tar -czf chat_history_backup.tar.gz chat_history
```

### 停止服务

```bash
# Docker 方式
docker compose down

# 手动部署方式
sudo systemctl stop codelens
```

---

## 性能优化建议

1. **使用 Gunicorn 替代 Uvicorn**（生产环境）
   ```bash
   pip install gunicorn
   # 修改 docker-compose.yml 的 CMD
   CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
   ```

2. **配置 HTTPS**
   ```bash
   # 使用 Let's Encrypt 免费证书
   sudo yum install -y certbot python3-certbot-nginx  # CentOS
   sudo certbot --nginx -d your-domain.com
   ```

3. **启用 Redis 缓存**（可选）
   在 `docker-compose.yml` 中添加 Redis 服务

---

## 技术支持

- 项目文档：[README.md](./README.md)
- 阿里云文档：[ECS 用户指南](https://help.aliyun.com/product/25362.html)
- Docker 文档：[Docker 官方文档](https://docs.docker.com/)
