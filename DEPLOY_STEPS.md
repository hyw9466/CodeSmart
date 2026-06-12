# 服务器部署步骤

## 前提条件
在服务器终端中执行以下步骤。请在 **终端 8** 中手动输入这些命令。

---

## 步骤 1：更新系统
```bash
apt update && apt upgrade -y
```

## 步骤 2：安装必要软件
```bash
apt install -y apt-transport-https ca-certificates curl gnupg lsb-release git
```

## 步骤 3：安装 Docker
```bash
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker
```

## 步骤 4：配置 Docker 镜像加速
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

## 步骤 5：克隆代码
```bash
cd /root
git clone https://github.com/hyw9466/CodeSmart.git CodeSmart
cd CodeSmart
```

## 步骤 6：配置环境变量
```bash
cat > .env << 'EOF'
# 嵌入模型配置
EMBEDDING_MODEL=tongyi-embedding-vision-plus

# 阿里云 DashScope API Key (请替换为你的真实API Key)
DASHSCOPE_API_KEY=sk-your-api-key-here

# LLM 模型配置
LLM_MODEL=qwen3.6-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EOF
```

**重要：请编辑 .env 文件，替换 DASHSCOPE_API_KEY 为你的真实API Key：**
```bash
nano .env
```

## 步骤 7：构建并启动服务
```bash
docker compose build --no-cache
docker compose up -d
```

## 步骤 8：检查服务状态
```bash
docker ps
docker compose logs
```

## 步骤 9：测试服务
```bash
curl http://localhost:8000/health
```

---

## 部署完成！

访问地址：
- 前端页面：http://139.224.163.81:8000
- API 文档：http://139.224.163.81:8000/docs

常用命令：
- 查看日志：`docker compose logs -f`
- 停止服务：`docker compose down`
- 重启服务：`docker compose restart`
- 更新代码：`git pull && docker compose build && docker compose up -d`

---

## 常见问题

**1. Docker 构建失败**
- 检查网络连接
- 确认 Docker 镜像加速已配置
- 尝试：`docker info` 查看镜像源是否生效

**2. 无法访问网站**
- 检查安全组是否开放 8000 端口
- 在阿里云控制台 → 安全组 → 入方向规则，添加：
  - 协议：TCP
  - 端口：8000
  - 授权对象：0.0.0.0/0

**3. 服务启动失败**
- 查看日志：`docker compose logs`
- 检查 .env 文件配置是否正确
- 确认 API Key 是否有效

**4. 查看容器状态**
```bash
docker ps -a
docker compose ps
```
