# 🎯 CodeLens 完整部署流程

> 本文档将指导你完成从连接服务器到访问网站的全部步骤

---

## 📋 部署前准备清单

在开始之前，请确认你已准备好以下信息：

- [ ] 服务器公网 IP 地址
- [ ] 服务器登录密码
- [ ] 阿里云 DashScope API Key
- [ ] 本地已配置好 `.env` 文件

---

## 🚀 第一阶段：连接服务器

### 方式一：使用 PowerShell（推荐）

#### 步骤 1：打开 PowerShell

在 Windows 系统上，按 `Win + X`，选择"Windows PowerShell"或"终端"

#### 步骤 2：连接服务器

```powershell
ssh root@你的服务器公网IP

# 例如：
ssh root@47.92.123.456
```

#### 步骤 3：输入密码

屏幕会提示输入密码：
```
root@47.92.123.456's password:
```

输入你的密码（输入时不会显示字符，输入完按回车即可）

**首次连接提示**：如果显示以下内容，输入 `yes` 并按回车：
```
Are you sure you want to continue connecting (yes/no)?
```

### 方式二：使用阿里云 Workbench（最简单）

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
2. 找到你的 ECS 实例
3. 点击"远程连接"
4. 选择"Workbench"
5. 点击"立即登录"
6. 输入密码

---

## 📦 第二阶段：系统环境准备

### 步骤 1：检查系统信息

连接成功后，先检查系统环境：

```bash
# 查看系统版本
cat /etc/os-release

# 查看 CPU 和内存
free -h

# 查看磁盘空间
df -h
```

### 步骤 2：更新系统软件包

**对于 Ubuntu 系统：**
```bash
apt update && apt upgrade -y
```

**对于 CentOS/Alibaba Cloud Linux 系统：**
```bash
yum update -y
```

### 步骤 3：安装必要工具

```bash
# 安装常用工具
apt install -y curl wget git vim unzip
```

---

## 🔧 第三阶段：配置环境变量文件

### 步骤 1：创建项目目录

```bash
mkdir -p /root/CodeLens
```

### 步骤 2：创建 .env 文件

```bash
nano /root/CodeLens/.env
```

### 步骤 3：写入配置内容

```bash
# 嵌入模型配置（阿里云 DashScope）
EMBEDDING_MODEL=tongyi-embedding-vision-plus

# 聊天模型配置（阿里云 DashScope）
DASHSCOPE_API_KEY=sk-your-actual-api-key-here
LLM_MODEL=qwen3.6-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

**重要**：将 `sk-your-actual-api-key-here` 替换为你的真实 API Key

### 步骤 4：保存文件

按 `Ctrl + X` 退出

输入 `Y` 确认保存

按 `Enter` 确认文件名

---

## 📂 第四阶段：上传项目代码

### 方式一：使用 SCP 上传（推荐）

在**本地 PowerShell**（不是服务器）执行：

```powershell
# 上传整个项目目录
scp -r .\CodeLens\* root@你的服务器IP:/root/CodeLens

# 示例：
scp -r .\CodeLens\* root@47.92.123.456:/root/CodeLens
```

### 方式二：使用 Git 克隆

在**服务器**上执行：

```bash
cd /root/CodeLens

# 如果代码在 GitHub
git clone https://github.com/你的用户名/CodeLens.git .

# 如果代码在 Gitee
git clone https://gitee.com/你的用户名/CodeLens.git .
```

### 方式三：使用宝塔面板

1. 安装宝塔面板：
```bash
yum install -y wget && wget -O install.sh http://download.bt.cn/install/install_6.0.sh && sh install.sh
```

2. 登录宝塔面板
3. 使用文件管理功能上传代码

---

## 🐳 第五阶段：安装 Docker

### 步骤 1：安装 Docker（Ubuntu 系统）

```bash
# 1. 安装依赖
apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release

# 2. 添加 Docker GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 3. 添加 Docker APT 源
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. 更新 APT
apt update

# 5. 安装 Docker
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 6. 启动 Docker
systemctl start docker
systemctl enable docker
```

### 步骤 2：安装 Docker（CentOS/Alibaba Cloud Linux 系统）

```bash
# 1. 安装依赖
yum install -y yum-utils

# 2. 添加 Docker YUM 源
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 3. 安装 Docker
yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 4. 启动 Docker
systemctl start docker
systemctl enable docker
```

### 步骤 3：验证 Docker 安装

```bash
# 检查 Docker 版本
docker --version

# 检查 Docker 是否运行
systemctl status docker

# 运行测试镜像
docker run hello-world
```

---

## ⚙️ 第六阶段：配置 Docker 加速（重要！）

### 步骤 1：创建配置目录

```bash
mkdir -p /etc/docker
```

### 步骤 2：配置 Docker 镜像加速

```bash
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF
```

### 步骤 3：重启 Docker

```bash
systemctl daemon-reload
systemctl restart docker
```

### 步骤 4：验证加速配置

```bash
docker info | grep -A 5 "Registry Mirrors"
```

---

## 🚀 第七阶段：部署应用

### 步骤 1：进入项目目录

```bash
cd /root/CodeLens
```

### 步骤 2：构建 Docker 镜像

```bash
# 构建镜像（需要 5-10 分钟）
docker compose build

# 如果 docker-compose 不可用，使用：
docker compose build

# 或使用：
docker-compose build
```

**耐心等待**：构建过程需要下载基础镜像和安装依赖，请耐心等待。

### 步骤 3：启动服务

```bash
# 后台启动服务
docker compose up -d

# 如果 docker-compose 不可用，使用：
docker compose up -d
```

### 步骤 4：检查服务状态

```bash
# 查看运行中的容器
docker ps

# 应该看到类似输出：
# CONTAINER ID   IMAGE                    STATUS
# xxxxxxxx       codelens-app             Up 2 minutes
```

### 步骤 5：查看启动日志

```bash
# 查看最近 50 行日志
docker logs --tail 50 code-analysis-assistant

# 实时查看日志
docker logs -f code-analysis-assistant
```

**首次启动**：会加载预置知识库，可能需要 3-5 分钟。等待看到类似输出：
```
Application startup complete.
```

---

## ✅ 第八阶段：验证部署

### 步骤 1：测试健康检查

```bash
curl http://localhost:8000/health
```

应该返回：
```json
{"status":"ok","version":"0.2.0"}
```

### 步骤 2：测试 API 文档

在浏览器中访问：
```
http://你的服务器公网IP:8000/docs
```

应该能看到 FastAPI 自动生成的 API 文档页面。

### 步骤 3：访问前端页面

打开浏览器访问：
```
http://你的服务器公网IP:8000
```

应该能看到 CodeLens 前端界面。

---

## 🔒 第九阶段：配置安全组（重要！）

### 步骤 1：登录阿里云控制台

1. 访问 [阿里云 ECS 控制台](https://ecs.console.aliyun.com/)
2. 找到你的实例
3. 点击"安全组"

### 步骤 2：配置入方向规则

点击"配置规则" → "入方向" → "快速添加"

| 协议 | 端口 | 授权对象 |
|-----|------|---------|
| HTTP | 80 | 0.0.0.0/0 |
| HTTPS | 443 | 0.0.0.0/0 |
| 自定义 TCP | 8000 | 0.0.0.0/0 |

### 步骤 3：确认端口开放

```bash
# 在服务器上检查端口监听
netstat -tlnp | grep :8000

# 应该看到：
# tcp6  0  0 :::8000  :::*  LISTEN  xxxx/docker-proxy
```

---

## 🎉 部署完成！

恭喜！你已经成功部署了 CodeLens 应用！

### 访问地址

| 服务 | 地址 |
|-----|------|
| 前端页面 | http://你的服务器公网IP:8000 |
| API 文档 | http://你的服务器公网IP:8000/docs |
| 健康检查 | http://你的服务器公网IP:8000/health |

---

## 🛠️ 常用运维命令

### 查看服务状态
```bash
docker ps
```

### 查看日志
```bash
# 实时日志
docker logs -f code-analysis-assistant

# 最近 100 行
docker logs --tail 100 code-analysis-assistant
```

### 重启服务
```bash
docker compose restart
```

### 停止服务
```bash
docker compose down
```

### 启动服务
```bash
docker compose up -d
```

### 更新代码并重新部署
```bash
# 1. 拉取最新代码
cd /root/CodeLens
git pull

# 2. 重新构建
docker compose build --no-cache

# 3. 重启服务
docker compose up -d
```

### 备份数据
```bash
# 备份向量数据库
tar -czf faiss_backup_$(date +%Y%m%d).tar.gz vectorstore/

# 备份聊天记录
tar -czf chat_history_backup_$(date +%Y%m%d).tar.gz chat_history/
```

---

## 🔧 常见问题排查

### 问题 1：SSH 连接失败

**检查**：
- 服务器公网 IP 是否正确
- 安全组是否开放 22 端口
- 密码是否输入正确

**解决**：使用阿里云 Workbench 连接

### 问题 2：Docker 构建失败

**检查日志**：
```bash
docker compose build 2>&1
```

**常见原因**：
- 网络问题（配置 Docker 加速）
- 内存不足（增加 swap）
- 磁盘空间不足（清理日志）

### 问题 3：容器启动失败

**查看日志**：
```bash
docker logs code-analysis-assistant
```

**常见原因**：
- `.env` 文件不存在
- API Key 无效
- 端口被占用

### 问题 4：无法访问网站

**检查**：
```bash
# 检查容器是否运行
docker ps

# 检查端口监听
netstat -tlnp | grep :8000

# 检查防火墙
ufw status  # Ubuntu
firewall-cmd --list-all  # CentOS
```

**解决**：在阿里云安全组开放 8000 端口

### 问题 5：API 调用失败

**检查**：
```bash
# 检查 API Key 配置
docker exec code-analysis-assistant cat /app/.env

# 检查网络连接
docker exec code-analysis-assistant ping dashscope.aliyuncs.com
```

---

## 📊 性能监控

### 查看资源使用
```bash
# CPU 和内存
top

# 内存使用
free -h

# 磁盘使用
df -h

# Docker 资源使用
docker stats
```

### 查看网络连接
```bash
# 查看网络连接数
netstat -an | wc -l

# 查看端口连接
netstat -tlnp
```

---

## 🔄 后续维护建议

1. **定期备份数据**
   ```bash
   tar -czf backup_$(date +%Y%m%d).tar.gz vectorstore/ chat_history/
   ```

2. **配置日志轮转**
   ```bash
   cat > /etc/logrotate.d/codelens << 'EOF'
   /root/CodeLens/logs/*.log {
       daily
       rotate 7
       compress
       delaycompress
       notifempty
       create 0644 root root
   }
   EOF
   ```

3. **设置定时任务**
   ```bash
   crontab -e
   
   # 添加定时备份（每天凌晨 3 点）
   0 3 * * * tar -czf /root/backup_$(date +\%Y\%m\%d).tar.gz /root/CodeLens/vectorstore /root/CodeLens/chat_history
   ```

---

## 📞 获取帮助

遇到问题时：

1. 查看详细日志：`docker logs code-analysis-assistant`
2. 查看 Docker 状态：`docker ps -a`
3. 查看系统资源：`top` 和 `free -h`
4. 查阅官方文档：[阿里云 ECS 文档](https://help.aliyun.com/product/25365.html)

---

**祝你部署顺利！🎉**
