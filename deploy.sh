#!/bin/bash

# ============================================
# CodeLens 阿里云一键部署脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  CodeLens 阿里云部署脚本${NC}"
echo -e "${GREEN}============================================${NC}"

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
  echo -e "${YELLOW}提示：建议使用 sudo 运行此脚本${NC}"
  exit 1
fi

# 1. 更新系统
echo -e "${YELLOW}[1/6] 更新系统软件包...${NC}"
yum update -y || apt update -y

# 2. 安装 Docker
echo -e "${YELLOW}[2/6] 安装 Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker 已安装${NC}"
else
    echo -e "${YELLOW}正在安装 Docker...${NC}"
    # CentOS/RHEL
    if [ -f /etc/redhat-release ]; then
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    # Ubuntu/Debian
    elif [ -f /etc/debian_version ]; then
        apt install -y ca-certificates curl gnupg lsb-release
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt update
        apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    fi
    
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}✓ Docker 安装完成${NC}"
fi

# 3. 检查项目文件
echo -e "${YELLOW}[3/6] 检查项目文件...${NC}"
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}✗ 错误：未找到 docker-compose.yml 文件${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ 警告：未找到 .env 文件，请确保已配置环境变量${NC}"
fi

# 4. 构建 Docker 镜像
echo -e "${YELLOW}[4/6] 构建 Docker 镜像...${NC}"
docker compose build --no-cache

# 5. 启动服务
echo -e "${YELLOW}[5/6] 启动服务...${NC}"
docker compose up -d

# 6. 检查服务状态
echo -e "${YELLOW}[6/6] 检查服务状态...${NC}"
sleep 10

if docker ps | grep -q code-analysis-assistant; then
    echo -e "${GREEN}✓ CodeLens 服务已成功启动！${NC}"
    echo ""
    echo -e "${GREEN}访问地址：${NC}"
    echo "  - 前端：http://$(curl -s ifconfig.me)"
    echo "  - API 文档：http://$(curl -s ifconfig.me)/docs"
    echo "  - 健康检查：http://$(curl -s ifconfig.me)/health"
    echo ""
    echo -e "${YELLOW}查看日志：${NC}docker logs -f code-analysis-assistant"
    echo -e "${YELLOW}停止服务：${NC}docker compose down"
    echo -e "${YELLOW}重启服务：${NC}docker compose restart"
else
    echo -e "${RED}✗ 服务启动失败，请检查日志：${NC}"
    docker logs code-analysis-assistant
    exit 1
fi

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
