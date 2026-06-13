# CodeSmart - 智能代码分析助手

基于 RAG（检索增强生成）与 LLM Agent 架构的智能代码分析系统。支持代码审查、安全分析、性能诊断、重构建议，内置多维度专家知识库，可通过上传文档持续扩展知识。

## 功能特性

- **智能代码分析**：自动识别代码语言，从正确性、安全性、性能、可读性、可维护性五个维度分析
- **RAG 文档问答**：上传文档构建知识库，基于检索增强生成回答问题，附带来源引用
- **文档总结**：对上传的文档自动生成结构化摘要
- **Agent 自动路由**：根据用户意图自动选择工具或直接对话
- **多轮对话记忆**：支持上下文窗口记忆（最近 3 轮），对话历史持久化存储
- **流式输出**：SSE 实时逐字输出，前端打字机效果
- **多格式文档**：支持 .md / .txt / .pdf / .docx 上传
- **文档去重**：基于内容 SHA256 哈希自动检测重复上传
- **预置知识库**：内置代码质量、安全、性能、设计模式、重构、Code Review 六大知识库，启动时自动加载
- **专家配置**：通过 YAML 配置文件定义专家人设，换领域只需改配置
- **异步并发 Embedding**：并发调用 Embedding API，上传大文档时显著加速

## 技术栈

- 前端：Vue 3 + Vite + Tailwind CSS
- 后端：Python + FastAPI + LangChain
- LLM：阿里云百炼 qwen3.6-plus（DashScope API）
- Embedding：阿里云 DashScope tongyi-embedding-vision-flash
- 向量数据库：FAISS（本地持久化）
- Agent 框架：LangGraph ReAct Agent

## 项目结构

```
CodeSmart/
├── main.py                    # FastAPI 应用入口
├── config.py                  # 全局配置（从 .env 读取）
├── expert_profile.yaml        # 专家人设配置
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── docker-compose.yml         # Docker 部署配置
├── Dockerfile                # Docker 镜像构建
├── agent/                     # Agent 核心
│   ├── agent.py               # Agent 逻辑 + 对话记忆管理
│   └── tools.py              # Tool 定义（文档问答、文档总结）
├── api/                       # API 接口层
│   ├── routes.py             # 全部路由（REST + SSE 流式）
│   └── schemas.py             # 请求/响应模型
├── chains/                    # LangChain 链
│   ├── rag_chain.py           # RAG 问答链
│   └── summary_chain.py      # 文档总结链
├── document/                  # 文档处理
│   └── loader.py             # 文档加载 + 语义分块
├── expert/                    # 专家系统
│   ├── profile.py            # 配置加载器
│   └── knowledge_loader.py   # 知识库自动加载
├── knowledge_base/            # 预置知识库（6 个维度）
├── models/                    # 模型封装
│   ├── llm.py                # LLM（DashScope OpenAI 兼容）
│   └── embedding.py          # Embedding（阿里云 DashScope，同步+异步并发）
└── web/                       # Vue 3 前端
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 1. 克隆项目

```bash
git clone https://github.com/hyw9466/CodeSmart.git
cd CodeSmart
```

### 2. 后端配置

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（Windows PowerShell）
.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
copy .env.example .env
# 编辑 .env，填入你的 API Key
```

### 3. 前端配置

```bash
cd web
npm install
cd ..
```

### 4. 启动服务

```powershell
# 终端 1：启动后端
.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 终端 2：启动前端
cd web
npm run dev
```

浏览器打开 http://localhost:5173

## Docker 部署

```bash
# 1. 复制并配置环境变量
cp .env.example .env
nano .env  # 填入 API Key

# 2. 构建并启动
docker compose up -d

# 3. 查看日志
docker logs code-analysis-assistant -f
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/upload` | POST | 上传文档（.md/.txt/.pdf/.docx） |
| `/api/documents` | GET | 已入库文档列表 |
| `/api/sessions` | GET | 会话列表 |
| `/api/sessions/{id}/messages` | GET | 会话历史消息 |
| `/api/chat` | POST | RAG 问答 |
| `/api/chat/stream` | POST | RAG 问答（流式 SSE） |
| `/api/agent/chat` | POST | Agent 智能对话 |
| `/api/agent/chat/stream` | POST | Agent 智能对话（流式 SSE） |
| `/api/summary` | POST | 文档总结 |
| `/api/summary/stream` | POST | 文档总结（流式 SSE） |

## 配置说明

### 环境变量（.env）

```env
# Embedding 模型（阿里云 DashScope）
EMBEDDING_MODEL=tongyi-embedding-vision-flash-2026-03-06
DASHSCOPE_API_KEY=your-dashscope-api-key

# LLM 模型（阿里云百炼）
DASHSCOPE_API_KEY=your-dashscope-api-key
LLM_MODEL=qwen3.6-plus

# 可选配置
EMBEDDING_CONCURRENCY=3
MEMORY_WINDOW_K=3
```

### 专家配置（expert_profile.yaml）

修改 `persona` 字段可自定义专家人设，修改 `knowledge_files` 可调整预置知识库。换领域（如法律、医疗）只需修改此文件和对应的知识库文档，代码无需改动。

## License

MIT
