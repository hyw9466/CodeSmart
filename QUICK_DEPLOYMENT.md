# ⚡ 快速部署命令卡

> 粘贴即用，快速部署 CodeLens

---

## 🚀 服务器连接

```powershell
# PowerShell 连接服务器
ssh root@你的服务器IP

# 例如：
ssh root@47.92.123.456
```

---

## 🔧 第一步：系统准备（Ubuntu）

```bash
# 更新系统
apt update && apt upgrade -y

# 安装工具
apt install -y curl wget git vim unzip
```

---

## 📝 第二步：配置环境变量

```bash
# 创建目录
mkdir -p /root/CodeLens

# 创建 .env 文件
nano /root/CodeLens/.env
```

**写入以下内容**（将 API Key 替换为你的）：
```bash
EMBEDDING_MODEL=tongyi-embedding-vision-plus
DASHSCOPE_API_KEY=sk-your-api-key-here
LLM_MODEL=qwen3.6-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

按 `Ctrl+X` → `Y` → `Enter` 保存

---

## 📂 第三步：上传代码

**在本地 PowerShell 执行**：
```powershell
scp -r .\CodeLens\* root@你的服务器IP:/root/CodeLens
```

---

## 🐳 第四步：安装 Docker

```bash
# Ubuntu 系统安装 Docker
apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl start docker
systemctl enable docker
```

---

## ⚡ 第五步：配置 Docker 加速

```bash
mkdir -p /etc/docker

cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker
```

---

## 🚀 第六步：构建并启动

```bash
cd /root/CodeLens

# 构建镜像（5-10分钟）
docker compose build

# 启动服务
docker compose up -d
```

---

## ✅ 第七步：验证部署

```bash
# 检查容器状态
docker ps

# 测试健康检查
curl http://localhost:8000/health

# 查看日志
docker logs --tail 20 code-analysis-assistant
```

**成功响应**：
```json
{"status":"ok","version":"0.2.0"}
```

---

## 🌐 第八步：开放端口

在阿里云控制台 → 安全组 → 入方向规则：

| 协议 | 端口 | 授权对象 |
|-----|------|---------|
| 自定义 TCP | 8000 | 0.0.0.0/0 |

---

## 🎉 访问地址

| 服务 | 地址 |
|-----|------|
| 前端页面 | http://你的服务器IP:8000 |
| API 文档 | http://你的服务器IP:8000/docs |

---

## 🛠️ 常用命令

```bash
# 查看状态
docker ps

# 查看日志
docker logs -f code-analysis-assistant

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 启动服务
docker compose up -d
```

---

## ⚠️ 常见问题

| 问题 | 解决 |
|-----|------|
| SSH 连接失败 | 使用阿里云 Workbench |
| Docker 安装失败 | 使用阿里云镜像源 |
| 容器启动失败 | 检查 `.env` 文件和日志 |
| 无法访问网站 | 开放安全组 8000 端口 |

---

**💡 遇到问题查看完整日志**：`docker logs code-analysis-assistant`
