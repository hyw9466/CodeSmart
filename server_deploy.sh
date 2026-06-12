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

# 1. 更新系统
echo -e "${YELLOW}[1/8] 更新系统软件包...${NC}"
apt update && apt upgrade -y

# 2. 安装必要的软件
echo -e "${YELLOW}[2/8] 安装 Docker 和相关工具...${NC}"
apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# 3. 安装 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}安装 Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}✓ Docker 安装完成${NC}"
else
    echo -e "${GREEN}✓ Docker 已安装${NC}"
fi

# 4. 配置 Docker 镜像加速
echo -e "${YELLOW}[3/8] 配置 Docker 镜像加速...${NC}"
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
echo -e "${GREEN}✓ Docker 镜像加速配置完成${NC}"

# 5. 克隆代码
echo -e "${YELLOW}[4/8] 克隆代码...${NC}"
cd /root
if [ -d "CodeSmart" ]; then
    echo -e "${YELLOW}代码目录已存在，更新代码...${NC}"
    cd CodeSmart
    git pull origin main
else
    echo -e "${YELLOW}克隆代码...${NC}"
    git clone https://github.com/hyw9466/CodeSmart.git CodeSmart
    cd CodeSmart
fi
echo -e "${GREEN}✓ 代码克隆/更新完成${NC}"

# 6. 创建 .env 文件
echo -e "${YELLOW}[5/8] 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# 嵌入模型配置
EMBEDDING_MODEL=tongyi-embedding-vision-plus

# 阿里云 DashScope API Key (请替换为你的真实API Key)
DASHSCOPE_API_KEY=sk-your-api-key-here

# LLM 模型配置
LLM_MODEL=qwen3.6-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EOF
    echo -e "${YELLOW}⚠ 请编辑 .env 文件，替换 DASHSCOPE_API_KEY 为你的真实API Key${NC}"
else
    echo -e "${GREEN}✓ .env 文件已存在${NC}"
fi

# 7. 构建并启动服务
echo -e "${YELLOW}[6/8] 构建 Docker 镜像...${NC}"
docker compose build --no-cache

echo -e "${YELLOW}[7/8] 启动服务...${NC}"
docker compose up -d

# 8. 检查服务状态
echo -e "${YELLOW}[8/8] 检查服务状态...${NC}"
sleep 10

if docker ps | grep -q codesmart; then
    echo -e "${GREEN}✓ CodeLens 服务已成功启动！${NC}"
    echo ""
    echo -e "${GREEN}访问地址：${NC}"
    echo "  - 前端：http://139.224.163.81:8000"
    echo "  - API 文档：http://139.224.163.81:8000/docs"
    echo "  - 健康检查：http://139.224.163.81:8000/health"
    echo ""
    echo -e "${YELLOW}查看日志：${NC}docker compose logs -f"
    echo -e "${YELLOW}停止服务：${NC}docker compose down"
    echo -e "${YELLOW}重启服务：${NC}docker compose restart"
else
    echo -e "${RED}✗ 服务启动失败，请检查日志：${NC}"
    docker compose logs
    exit 1
fi

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
