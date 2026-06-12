# 阿里云部署检查清单 ✅

## 📋 部署前准备

- [ ] **阿里云账号**
  - [ ] 已注册阿里云账号
  - [ ] 已完成实名认证
  - [ ] 账户余额充足（至少 50 元）

- [ ] **ECS 服务器**
  - [ ] 已创建 ECS 实例
  - [ ] 实例规格：2 核 4GB 或更高
  - [ ] 操作系统：Ubuntu 22.04 或 CentOS 7.9
  - [ ] 存储：40GB 或更高
  - [ ] 带宽：1 Mbps 或更高

- [ ] **安全组配置**
  - [ ] 已开放 22 端口（SSH）
  - [ ] 已开放 80 端口（HTTP）
  - [ ] 已开放 443 端口（HTTPS）

- [ ] **API Key**
  - [ ] 已开通 DashScope 服务
  - [ ] 已获取 API Key
  - [ ] 已配置到 `.env` 文件

---

## 🚀 部署流程

### 阶段一：本地准备

- [ ] 项目代码已提交到 Git 仓库
- [ ] `.env` 文件已配置 API Key
- [ ] 已安装 Git 客户端
- [ ] 已安装 SSH 客户端

### 阶段二：服务器连接

- [ ] 使用 SSH 连接到服务器
  ```bash
  ssh root@你的服务器 IP
  ```
- [ ] 确认连接成功
- [ ] 更新系统包
  ```bash
  yum update -y  # CentOS
  apt update -y  # Ubuntu
  ```

### 阶段三：上传代码

- [ ] 方式一：Git 克隆（推荐）
  ```bash
  git clone https://github.com/你的用户名/CodeLens.git
  cd CodeLens
  ```

- [ ] 方式二：SCP 上传
  ```bash
  scp -r ./* root@服务器 IP:/root/CodeLens
  ```

### 阶段四：环境配置

- [ ] 检查 `.env` 文件
  ```bash
  cat .env
  ```
- [ ] 确认 API Key 已正确配置
- [ ] 确认模型配置正确

### 阶段五：Docker 部署

- [ ] 安装 Docker
  ```bash
  # 执行部署脚本
  chmod +x deploy.sh
  sudo ./deploy.sh
  ```

- [ ] 等待构建完成（约 5-10 分钟）
- [ ] 确认服务启动成功

### 阶段六：验证测试

- [ ] 检查容器状态
  ```bash
  docker ps
  ```

- [ ] 查看服务日志
  ```bash
  docker logs code-analysis-assistant
  ```

- [ ] 测试健康检查
  ```bash
  curl http://localhost:8000/health
  ```
  应返回：`{"status":"ok","version":"0.2.0"}`

- [ ] 浏览器访问
  - [ ] 访问 `http://服务器 IP`
  - [ ] 前端页面正常显示
  - [ ] API 文档可访问 `http://服务器 IP/docs`

---

## 🔧 故障排查

### 问题 1：SSH 无法连接

- [ ] 检查服务器公网 IP 是否正确
- [ ] 检查安全组是否开放 22 端口
- [ ] 检查服务器是否运行中
- [ ] 尝试使用阿里云 Workbench 连接

### 问题 2：Docker 安装失败

- [ ] 检查网络连接
  ```bash
  ping www.aliyun.com
  ```
- [ ] 使用阿里云镜像源
  ```bash
  # CentOS
  sudo yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
  ```

### 问题 3：容器启动失败

- [ ] 查看错误日志
  ```bash
  docker logs code-analysis-assistant
  ```
- [ ] 检查 `.env` 文件是否存在
- [ ] 检查 API Key 是否正确
- [ ] 检查内存是否充足
  ```bash
  free -h
  ```

### 问题 4：无法访问服务

- [ ] 检查端口监听
  ```bash
  netstat -tlnp | grep :8000
  ```
- [ ] 检查安全组规则
- [ ] 检查防火墙状态
  ```bash
  systemctl status firewalld  # CentOS
  ufw status  # Ubuntu
  ```

### 问题 5：API 调用失败

- [ ] 验证 API Key
  ```bash
  docker exec code-analysis-assistant cat /app/.env
  ```
- [ ] 检查网络连接
  ```bash
  docker exec code-analysis-assistant ping dashscope.aliyuncs.com
  ```
- [ ] 检查 DNS 配置
  ```bash
  docker inspect code-analysis-assistant | grep -A 5 Dns
  ```

---

## 📊 部署后检查

### 性能检查

- [ ] CPU 使用率正常（< 80%）
  ```bash
  top
  ```
- [ ] 内存使用正常（< 80%）
  ```bash
  free -h
  ```
- [ ] 磁盘空间充足
  ```bash
  df -h
  ```

### 服务检查

- [ ] 容器运行正常
  ```bash
  docker ps
  ```
- [ ] 健康检查通过
  ```bash
  curl http://localhost:8000/health
  ```
- [ ] 日志无错误
  ```bash
  docker logs --tail 100 code-analysis-assistant
  ```

### 功能测试

- [ ] 前端页面可访问
- [ ] API 文档可访问
- [ ] 文件上传功能正常
- [ ] 对话功能正常
- [ ] 知识库加载成功

---

## 🔒 安全加固（可选）

- [ ] 修改 SSH 端口
- [ ] 禁用 root 登录
- [ ] 配置 SSH 密钥认证
- [ ] 安装 Fail2ban
- [ ] 配置 HTTPS（使用 Let's Encrypt）
- [ ] 定期更新系统包
- [ ] 配置自动备份

---

## 📝 重要信息记录

请记录以下信息以备后用：

```
服务器公网 IP：_________________
SSH 端口：_____________________
登录用户名：___________________
登录密码/密钥：_________________

阿里云账号：___________________
DashScope API Key：_____________

服务访问地址：http://___________
API 文档地址：http://___________/docs

Docker 容器名：code-analysis-assistant
```

---

## 🆘 获取帮助

遇到问题时：

1. 查看项目文档：`README.md`
2. 查看详细部署指南：`DEPLOYMENT.md`
3. 查看 Docker 日志：`docker logs code-analysis-assistant`
4. 阿里云工单：https://workorder.console.aliyun.com/

---

**部署完成后，恭喜！🎉 你的 CodeLens 已成功上线！**
