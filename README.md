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

## 项目亮点

**1. 混合路由架构：规则匹配 + Agent 自动决策**

不是所有问题都值得调用 LLM。项目在 Agent 之前插入一层规则匹配，对问候、致谢、时间查询等高频简单对话直接返回预设响应（< 10ms），避免为"你好"花费一次 API 调用。识别不了的请求再交给 LangGraph ReAct Agent 做工具调用决策。这种两级路由在保持智能化的同时，有效控制 API 成本和响应延迟。

**2. 三层记忆体系：短期上下文 + 智能压缩 + 长期向量记忆**

- **短期记忆**：基于 `FileChatMessageHistory` 持久化，按 session 隔离，重启不丢失
- **上下文压缩**：对历史消息做多因子评分（语义相关性 60% + 位置权重 30% + 消息类型 10%），结合动态窗口算法，在不超过 Token 预算的前提下保留最有价值的上下文
- **长期记忆**：通过 FAISS 向量库存储用户偏好和关键知识点，跨会话检索复用。会话结束时自动触发 LLM 摘要，提取偏好和待办事项存入长期记忆

**3. 解耦的专家系统：换领域只需改配置**

专家人设通过 `expert_profile.yaml` 定义，预置知识库从 `knowledge_base/` 目录自动加载到向量库，Agent 的 system prompt 由配置动态拼装。不关心代码审查的场景下，替换 YAML 和知识库文档，同一套代码即可切换为法律顾问、技术支持等角色——LLM、RAG、Agent 三条链都没有领域耦合。

**4. 文档去重与并发 Embedding**

上传文档时基于内容 SHA256 哈希检测重复，避免同一文档被重复向量化。Embedding 调用使用 `asyncio.Semaphore` 控制并发（默认 3），大文档分块后并发处理，相比串行提速约 2-3 倍，同时通过信号量避免触发 API 限流。

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
│   ├── agent.py               # Agent 路由 + 对话记忆 + 简单对话快速响应
│   ├── tools.py               # Tool 定义（文档问答、文档总结等）
│   ├── context_compressor.py  # 智能上下文压缩（多因子评分 + 动态窗口）
│   ├── long_term_memory.py    # 长期记忆（FAISS 向量存储 + 过期清理）
│   └── session_summarizer.py  # 会话自动总结（LLM 摘要 + 偏好提取）
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
| `/api/memory/stats` | GET | 用户记忆统计 |
| `/api/memory/retrieve` | GET | 检索相关记忆 |
| `/api/memory/add` | POST | 手动添加记忆 |
| `/api/memory/{memory_id}` | DELETE | 删除指定记忆 |
| `/api/sessions/{id}/summary` | GET | 获取会话总结 |

## 配置说明

### 环境变量（.env）

```env
# Embedding 模型（阿里云 DashScope）
EMBEDDING_MODEL=text-embedding-v4

# LLM 模型（阿里云百炼）
DASHSCOPE_API_KEY=your-dashscope-api-key
LLM_MODEL=qwen3.6-plus

# 可选配置
EMBEDDING_CONCURRENCY=3
MEMORY_WINDOW_K=3        # 短期记忆窗口（轮数）
MEMORY_EXPIRE_DAYS=30     # 长期记忆过期天数
MEMORY_RETRIEVE_K=3       # 检索返回记忆数量
MEMORY_SUMMARY_THRESHOLD=5 # 触发会话总结的消息数
```

### 专家配置（expert_profile.yaml）

修改 `persona` 字段可自定义专家人设，修改 `knowledge_files` 可调整预置知识库。换领域（如法律、医疗）只需修改此文件和对应的知识库文档，代码无需改动。

## License

MIT
