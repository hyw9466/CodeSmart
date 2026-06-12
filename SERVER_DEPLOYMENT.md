# 🚀 CodeSmart 服务器部署指南

## 📋 服务器信息

| 项目 | 值 |
|-----|-----|
| **服务器地址** | 139.224.163.81 |
| **操作系统** | Ubuntu 24.04 |
| **配置** | 2核 CPU / 2GB 内存 / 40GB 系统盘 |
| **GitHub 仓库** | https://github.com/hyw9466/CodeSmart |

---

## 🔧 第一步：连接服务器

```bash
# 在本地 PowerShell 执行
ssh root@139.224.163.81
# 密码：Hyw9466...（你知道的）
```

---

## 🔧 第二步：安装依赖

```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Git 和 Docker
apt install -y git docker.io docker-compose

# 启动 Docker 服务
systemctl start docker
systemctl enable docker
```

---

## 🔧 第三步：配置 Docker 加速

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

## 📂 第四步：克隆代码

```bash
cd /root
git clone https://github.com/hyw9466/CodeSmart.git CodeLens
cd CodeLens
```

---

## 🔑 第五步：配置 API Key

```bash
# 编辑 .env 文件
nano .env

# 将 sk-your-actual-api-key-here 替换为你的阿里云 DashScope API Key
```

**修改后的 .env 文件示例：**
```bash
EMBEDDING_MODEL=tongyi-embedding-vision-plus
DASHSCOPE_API_KEY=sk-你的真实API密钥
LLM_MODEL=qwen3.6-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

按 `Ctrl+X` → `Y` → `Enter` 保存

---

## 🐳 第六步：构建并启动服务

```bash
# 构建 Docker 镜像
docker compose build

# 启动服务（后台运行）
docker compose up -d

# 查看运行状态
docker ps
```

---

## ✅ 第七步：验证部署

```bash
# 测试健康检查
curl http://localhost:8000/health

# 成功响应：{"status":"ok","version":"0.2.0"}

# 查看日志
docker logs --tail 20 code-analysis-assistant
```

---

## 🔒 第八步：配置阿里云安全组

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
2. 找到你的 ECS 实例
3. 点击"安全组" → "配置规则" → "入方向"
4. 添加规则：

| 协议 | 端口范围 | 授权对象 |
|-----|---------|---------|
| TCP | 8000 | 0.0.0.0/0 |
| TCP | 22 | 0.0.0.0/0 |

---

## 🎉 访问服务

| 服务 | 地址 |
|-----|------|
| 前端页面 | http://139.224.163.81:8000 |
| API 文档 | http://139.224.163.81:8000/docs |

---

## 🔄 更新代码

当 GitHub 代码更新后，执行：

```bash
cd /root/CodeLens
git pull
docker compose build --no-cache
docker compose up -d
```

---

## 🆘 常见问题

| 问题 | 解决方法 |
|-----|---------|
| Docker 构建失败 | 检查网络，确保 Docker 镜像加速已配置 |
| 无法访问网站 | 检查安全组是否开放 8000 端口 |
| 容器启动失败 | 查看日志：`docker logs code-analysis-assistant` |
| API Key 错误 | 检查 .env 文件中的 API Key 是否正确 |

---

## 📊 资源使用预估

| 资源 | 使用量 | 状态 |
|-----|------|------|
| CPU | ~10-20% | ✅ 正常 |
| 内存 | ~500MB | ✅ 正常 |
| 磁盘 | ~5GB | ✅ 正常 |

---

## 📝 快捷命令

```bash
# 查看容器状态
docker ps

# 查看日志
docker logs -f code-analysis-assistant

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 查看端口占用
netstat -tlnp | grep 8000
```
