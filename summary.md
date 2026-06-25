# CodeSmart - 智能代码分析助手

> 基于 RAG（检索增强生成）+ LangGraph ReAct Agent 架构的智能代码分析系统
> 版本：0.2.0 | 部署地址：http://139.224.163.81:8000

---

## 一、项目概述

CodeSmart 是一个面向开发者的智能代码分析助手，支持代码审查、安全分析、性能诊断、重构建议等功能。内置 6 大专家知识库，可通过上传文档持续扩展知识。采用 **混合路由架构**（规则引擎 + ReAct Agent）实现智能决策，**SSE 流式输出**提供实时交互体验。

### 核心能力

| 能力 | 说明 |
|------|------|
| 代码审查 | 从正确性、安全性、性能、可读性、可维护性五个维度分析 |
| 安全分析 | 识别 SQL 注入、XSS、敏感信息泄露、认证缺陷等安全漏洞 |
| 性能诊断 | 发现算法复杂度问题、内存泄漏、N+1 查询、缺失缓存等 |
| 重构建议 | 基于设计模式和重构手法，给出具体改进方案和示例代码 |
| 架构评审 | 评估模块划分、耦合度、可扩展性 |
| RAG 文档问答 | 上传文档构建知识库，基于检索增强生成回答问题 |
| 错误日志分析 | 分析错误日志，定位问题根因并给出修复建议 |

---

## 二、技术栈

### 后端

| 技术 | 用途 |
|------|------|
| FastAPI + Uvicorn | Web 框架与 ASGI 服务器 |
| LangChain | LLM 应用框架（Chain、Tool、Agent） |
| LangGraph | ReAct Agent 编排（`create_react_agent`） |
| FAISS | 向量相似度检索（RAG 知识库） |
| 阿里云 DashScope | LLM（`qwen3.6-plus`）+ Embedding（`text-embedding-v4`） |
| PyMuPDF + python-docx | 文档解析（PDF、DOCX） |

### 前端

| 技术 | 用途 |
|------|------|
| Vue 3 + Vite | 前端框架与构建工具 |
| SSE（Server-Sent Events） | 流式实时输出 |
| marked.js | Markdown 渲染 |
| CodeMirror 6 | 代码编辑器 |

### 部署

| 技术 | 用途 |
|------|------|
| Docker + Docker Compose | 容器化部署 |
| FastAPI StaticFiles | 内置前端静态文件托管 |

---

## 三、目录结构

```
CodeSmart/
├── main.py                          # FastAPI 应用入口，启动事件
├── config.py                        # 全局配置（环境变量、路径管理）
├── expert_profile.yaml              # 专家人设配置（领域可切换）
├── requirements.txt                 # Python 依赖
├── Dockerfile                       # Docker 镜像构建
├── docker-compose.yml               # Docker Compose 编排
├── .env.example                     # 环境变量模板
├── DEPLOYMENT_GUIDE.md              # 部署指南
├── README.md                        # 项目说明
├── 学习路线.md                       # 学习路线
│
├── agent/                           # Agent 核心模块
│   ├── __init__.py
│   ├── agent.py                     # ReAct Agent 组装、路由、流式推理
│   ├── tools.py                     # 5 个专业工具定义
│   ├── context_compressor.py        # 智能上下文压缩
│   ├── long_term_memory.py          # 长期记忆管理（FAISS）
│   └── session_summarizer.py        # 会话自动总结
│
├── api/                             # API 接口层
│   ├── __init__.py
│   ├── routes.py                    # 所有 REST + SSE 接口
│   └── schemas.py                   # Pydantic 请求/响应模型
│
├── chains/                          # LangChain Chain 模块
│   ├── __init__.py
│   ├── rag_chain.py                 # RAG 检索问答链
│   ├── summary_chain.py             # 文档总结链
│   └── code_completion_chain.py     # 代码补全链
│
├── models/                          # 模型层
│   ├── __init__.py
│   ├── llm.py                       # LLM 客户端（DashScope OpenAI 兼容）
│   └── embedding.py                 # Embedding 客户端（异步并发）
│
├── vectorstore/                     # 向量库层
│   ├── __init__.py
│   ├── store.py                     # FAISS 向量存储（CRUD + 去重）
│   └── registry.py                  # 文档元数据注册表
│
├── document/                        # 文档处理
│   ├── __init__.py
│   └── loader.py                    # 文档加载、分割、验证
│
├── expert/                          # 专家配置
│   ├── __init__.py
│   ├── profile.py                   # YAML 专家人设加载
│   └── knowledge_loader.py          # 预置知识库自动加载
│
├── knowledge_base/                  # 预置知识库（启动时自动加载）
│   ├── code_quality.md              # 代码质量通用原则
│   ├── security.md                  # 安全漏洞模式与防御
│   ├── performance.md               # 性能优化模式
│   ├── design_patterns.md           # 设计模式
│   ├── refactoring.md               # 重构手法
│   └── code_review.md               # Code Review Checklist
│
├── web/                             # 前端（Vue 3 + Vite）
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── App.vue                  # 主应用组件
│   │   ├── api.js                   # SSE 流式 API 客户端
│   │   ├── main.js                  # Vue 应用入口
│   │   ├── markdown.js              # Markdown 渲染
│   │   ├── style.css                # 全局样式
│   │   └── components/
│   │       ├── ChatMessage.vue      # 聊天消息组件
│   │       ├── CodeEditor.vue       # 代码编辑器组件
│   │       ├── FileUpload.vue       # 文件上传组件
│   │       └── Sidebar.vue          # 侧边栏组件
│   ├── index.html                   # HTML 入口
│   ├── package.json                 # 前端依赖
│   ├── vite.config.js               # Vite 构建配置
│   └── README.md
│
└── data/                            # 持久化数据（Docker volume 挂载）
    ├── base_knowledge/faiss_index/  # 基础知识库向量索引
    ├── users/                       # 用户隔离数据
    ├── uploads/                     # 上传文件
    └── chat_history/                # 对话历史 JSON
```

---

## 四、架构设计

### 4.1 混合路由架构

```
                      ┌──────────────────────┐
                      │     用户输入           │
                      └──────────┬───────────┘
                                 │
                      ┌──────────▼───────────┐
                      │   第1层：快速路径匹配   │
                      │   _is_simple_message() │
                      │   问候/感谢/告别       │
                      │   → 直接返回，零延迟    │
                      └──────────┬───────────┘
                                 │ 非简单消息
                      ┌──────────▼───────────┐
                      │   第2层：ReAct Agent   │
                      │   LLM 自主决策         │
                      │   Think → Act → Observe│
                      └──────────┬───────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
  ┌───────▼───────┐     ┌───────▼───────┐      ┌───────▼───────┐
  │ 直接回答       │     │ 调用工具       │      │ 不调用工具      │
  │ (概念解释等)   │     │ (代码分析等)   │      │ (中间状态)     │
  └───────────────┘     └───────────────┘      └───────────────┘
                                 │
                      ┌──────────▼───────────┐
                      │   第3层：持久化 & 记忆  │
                      │   对话历史 → 长期记忆   │
                      │   → 会话总结           │
                      └──────────────────────┘
```

**第1层 - 快速路径匹配**：通过 `_is_simple_message()` 函数用正则匹配简单问候、感谢、告别、身份询问等，命中后直接返回预设响应，跳过 LLM 调用，实现零延迟响应。

**第2层 - ReAct Agent**：使用 LangGraph 的 `create_react_agent` 模板，基于 `qwen3.6-plus` 模型，LLM 自主决策是否需要调用工具、调用哪个工具。

**第3层 - 持久化 & 记忆**：对话结束后，自动持久化历史记录、更新长期记忆、检查是否需要会话总结。

### 4.2 System Prompt 三段式构造

System Prompt 在 `_get_system_prompt()` 中动态拼接，由三段组成：

```
┌─────────────────────────────────────────────────────┐
│  ① 专家人设（expert_profile.yaml）                    │
│  "资深全栈代码分析专家，五维度分析..."                  │
│  领域可切换，只需修改 YAML 配置                        │
├─────────────────────────────────────────────────────┤
│  ② 用户长期记忆（动态注入）                            │
│  FAISS 检索用户偏好："Python 优先"、"FastAPI 项目"     │
│  每次对话后自动更新，30天过期                           │
├─────────────────────────────────────────────────────┤
│  ③ 工具决策指南（_TOOL_INSTRUCTIONS）                  │
│  - 工具表：列出每个工具的用途和使用场景                  │
│  - 决策流程：什么场景该用什么工具                       │
│  - 典型场景示例（Few-shot 变体）                       │
└─────────────────────────────────────────────────────┘
```

**工具决策指南**是核心设计，它不是简单的工具列表，而是一份自然语言的决策指南：

```markdown
## 🤔 工具调用决策指南

**✅ 直接回答（不需要工具）**：
- 简单问候或闲聊（如"你好"、"今天天气"）
- 一般性知识问答（如"什么是 Python"、"解释什么是 REST API"）
- 概念解释（如"什么是 SQL 注入"、"什么是异步编程"）
- 不需要外部知识的问题
- 简短的技术问题（如"Python 中如何读取文件"）

**🔧 调用工具**：
- **code_security_analysis**：用户说"分析这段代码的安全性"、"检查漏洞"、"安全审计"
- **code_optimization**：用户说"优化这段代码"、"改进性能"、"代码重构建议"
- **document_qa**：用户上传文档后提问"文档中提到了什么"、"根据文档回答..."
- **document_summary**：用户说"总结这段文本"、"概括内容"
- **error_log_analysis**：用户粘贴错误日志，说"帮我看看这个错误"、"分析日志"

**💡 思考过程**：
1. 先理解用户的核心需求
2. 判断是否需要外部工具获取信息
3. 如果需要，选择最合适的工具
4. 如果不确定，尝试直接回答（保守策略）
```

### 4.3 5 个专业工具

每个工具在 `tools.py` 中使用 `@tool` 装饰器定义，是独立的 LLM Chain：

| 工具 | 底层实现 | System Prompt 人格 | Temperature | 参数 |
|------|---------|-------------------|-------------|------|
| `document_qa` | RAG Chain（FAISS 检索 + LLM） | 知识库问答专家 | 0.3 | `query: str` |
| `document_summary` | LLM Chain（专用 Prompt） | 文档总结专家 | 0.3 | `text: str` |
| `code_security_analysis` | LLM Chain（安全 Prompt） | 代码安全分析师 | **0** | `code: str, language: str` |
| `code_optimization` | LLM Chain（架构师 Prompt） | 软件架构师 | **0.3** | `code: str, language: str` |
| `error_log_analysis` | LLM Chain（运维 Prompt） | 运维调试专家 | **0** | `log_text: str` |

**设计要点**：
- 每个工具是独立的 LLM Chain，有自己的 System Prompt 人格，实现角色隔离
- temperature 差异化：安全分析用 0（严格一致），优化建议用 0.3（允许创意）
- 可独立升级：每个工具的 Prompt 可以独立调优，不影响其他工具
- 工具描述（docstring）被 LangChain 自动转化为 function calling 的 description

### 4.4 代码安全分析工具详解

```python
@tool
def code_security_analysis(code: str, language: str = "python") -> str:
    """分析代码中的安全漏洞。当用户需要检查代码安全性、发现潜在安全问题时使用此工具。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一位资深的代码安全分析师。请分析以下代码中的安全漏洞。\n"
                   "检测范围：SQL注入、XSS攻击、敏感信息泄露、硬编码密钥、命令注入、路径遍历、认证绕过。\n"
                   "对于每个发现的问题，请给出：问题描述、风险等级（高/中/低）、修复建议。\n"
                   "语言: {language}"),
        ("user", "请分析以下代码的安全性：\n```\n{code}\n```")
    ])
    llm = get_llm(temperature=0)  # 严格一致性
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"code": code, "language": language})
```

---

## 五、API 接口

### 5.1 基础接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 → `{"status":"ok","version":"0.2.0"}` |
| `GET` | `/` | 前端页面（Vue SPA） |

### 5.2 文档管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/documents/upload` | 上传文档（支持 md/txt/pdf/docx） |
| `GET` | `/api/documents` | 列出已上传文档（含去重） |
| `DELETE` | `/api/documents/{doc_id}` | 删除文档及向量数据 |

### 5.3 聊天 & Agent

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/agent/chat` | 同步对话（返回完整响应） |
| `POST` | `/api/agent/chat/stream` | **SSE 流式对话**（实时输出） |
| `GET` | `/api/sessions` | 列出所有会话 |
| `GET` | `/api/sessions/{id}/history` | 获取会话历史 |

### 5.4 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/document/summary` | 文档总结 |
| `POST` | `/api/code/completion` | 代码补全 |
| `GET` | `/api/memory/stats` | 长期记忆统计 |
| `POST` | `/api/sessions/{id}/summarize` | 手动触发会话总结 |

### 5.5 SSE 流式事件类型

| 事件 | 说明 | 前端表现 |
|------|------|---------|
| `thinking` | Agent 开始思考 | ⏳ 正在分析您的问题... |
| `tool_call` | 调用工具 | 🔧 正在调用工具：xxx |
| `tool_result` | 工具返回 | ✅ 工具调用完成：xxx |
| `token` | LLM 逐字输出 | 打字机效果 |
| `error` | 异常 | 显示错误信息 |
| `done` | 流结束 | 停止加载动画 |

### 5.6 流式响应实现

```python
# api/routes.py - agent_chat_stream 接口
async def generate():
    try:
        async for event in stream_agent(query, session_id, user_id):
            yield _sse_event(event, event.get("type", "message"))
        yield _sse_done()
    except Exception as e:
        yield _sse_event({"type": "error", "content": f"处理请求时出错：{str(e)}"}, "error")
        yield _sse_done()

return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 六、记忆系统

### 三层记忆架构

```
┌─────────────────────────────────────────────────┐
│  第1层：对话窗口（MEMORY_WINDOW_K=3）              │
│  最近 3 轮对话作为上下文，保证实时性                 │
│  FileChatMessageHistory 持久化到 JSON 文件         │
├─────────────────────────────────────────────────┤
│  第2层：智能上下文压缩                              │
│  context_compressor.py 实现                      │
│  - analyze_context(): 分析是否需要压缩             │
│  - compress(): 根据查询语义选择相关历史             │
│  - dynamic_window(): 动态调整窗口大小               │
├─────────────────────────────────────────────────┤
│  第3层：长期记忆（FAISS 向量库）                    │
│  long_term_memory.py 实现                        │
│  - 存储用户偏好、关键知识点                         │
│  - 30 天过期自动清理（MEMORY_EXPIRE_DAYS）          │
│  - 每次对话后自动更新（_update_long_term_memory）    │
│  - 检索时返回最相关的 K 条（MEMORY_RETRIEVE_K=3）    │
├─────────────────────────────────────────────────┤
│  第4层：会话总结                                   │
│  session_summarizer.py 实现                      │
│  - 消息数超过阈值（MEMORY_SUMMARY_THRESHOLD=5）     │
│    时自动触发                                      │
│  - 摘要注入后续对话的 System Prompt                │
│  - 支持手动触发（POST /api/sessions/{id}/summarize）│
└─────────────────────────────────────────────────┘
```

### 记忆数据流

```
用户输入
  │
  ▼
_get_compressed_messages()  ← 从 FileChatMessageHistory 读取
  │                           + 智能压缩
  ▼
stream_agent()  ← 压缩后的上下文传给 LLM
  │
  ├─► history.add_user_message(query)      ← 持久化用户消息
  ├─► history.add_ai_message(full_answer)  ← 持久化 AI 回复
  ├─► _update_long_term_memory()           ← 更新长期记忆
  └─► _should_summarize_session()          ← 检查是否需要总结
       └─► _summarize_and_store()          ← 生成并存储摘要
```

---

## 七、配置系统

### 7.1 环境变量（.env / docker-compose.yml）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DASHSCOPE_API_KEY` | - | 阿里云百炼 API Key（**必填**） |
| `LLM_MODEL` | `qwen3.6-plus` | 对话模型 |
| `EMBEDDING_MODEL` | `text-embedding-v4` | 向量化模型 |
| `LLM_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | LLM 接口地址 |
| `MEMORY_WINDOW_K` | `3` | 对话记忆窗口大小（轮数） |
| `EMBEDDING_CONCURRENCY` | `3` | Embedding 并发数 |
| `MEMORY_EXPIRE_DAYS` | `30` | 长期记忆过期天数 |
| `MEMORY_RETRIEVE_K` | `3` | 每次检索返回的记忆数量 |
| `MEMORY_SUMMARY_THRESHOLD` | `5` | 会话总结触发阈值（消息数） |

### 7.2 专家人设配置（expert_profile.yaml）

```yaml
name: "代码分析助手"
version: "1.0.0"

persona: |
  你是一位资深全栈代码分析专家，精通多种编程语言...

  你的核心能力：
  1. 代码审查：从正确性、安全性、性能、可读性、可维护性五个维度分析代码
  2. 安全分析：识别注入攻击、XSS、敏感信息泄露、认证缺陷等安全漏洞
  3. 性能诊断：发现算法复杂度问题、内存泄漏、N+1 查询、缺失缓存等性能瓶颈
  4. 重构建议：基于设计模式和重构手法，给出具体的改进方案和示例代码
  5. 架构评审：评估模块划分、耦合度、可扩展性

  回答规范：
  - 自动识别代码语言，针对该语言的特性和生态给出建议
  - 问题按严重程度分级：🔴 严重（必须修复）、🟡 警告（建议修复）、🟢 建议（可选优化）
  - 每个问题给出：问题描述 → 风险说明 → 修复方案（含代码示例）
  - 先结合知识库中的最佳实践，再结合自身知识给出全面分析
  - 回答使用中文

knowledge_base_dir: "knowledge_base"

knowledge_files:
  - code_quality.md
  - security.md
  - performance.md
  - design_patterns.md
  - refactoring.md
  - code_review.md
```

**领域可切换**：只需修改 `persona` 和 `knowledge_base_dir` 即可将系统切换到其他领域（如法律咨询、医疗助手等）。

### 7.3 多租户隔离

```python
# config.py
USERS_DIR: str = os.path.join(DATA_DIR, "users")

def get_user_dir(user_id: str) -> str:
    return os.path.join(USERS_DIR, user_id)

def get_user_faiss_dir(user_id: str) -> str:
    return os.path.join(USERS_DIR, user_id, "faiss_index")
```

每个用户的数据物理隔离：
- 向量索引：`data/users/{user_id}/faiss_index/`
- 上传文件：`data/users/{user_id}/uploads/`
- 对话历史：`data/users/{user_id}/chat_history/`

---

## 八、部署方案

### 8.1 Docker Compose 部署

```yaml
# docker-compose.yml
services:
  code-analysis-assistant:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: code-analysis-assistant
    ports:
      - "8000:8000"
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - LLM_MODEL=${LLM_MODEL:-qwen3.6-plus}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL:-text-embedding-v4}
    volumes:
      - ./data/vectorstore:/app/vectorstore/faiss_index
      - ./data/uploads:/app/uploads
      - ./data/chat_history:/app/chat_history
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 8.2 部署命令

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DASHSCOPE_API_KEY

# 2. 构建并启动
docker compose up -d --build

# 3. 查看日志
docker logs -f code-analysis-assistant --tail 100

# 4. 健康检查
curl http://localhost:8000/health
# → {"status":"ok","version":"0.2.0"}

# 5. 重启服务
docker compose restart

# 6. 停止服务
docker compose down
```

### 8.3 Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 使用阿里云镜像加速 apt
RUN echo 'Acquire::AllowInsecureRepositories "true";' > /etc/apt/apt.conf.d/99allow-unauthenticated \
    && echo "deb https://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list \
    && apt-get update && apt-get install -y --allow-unauthenticated build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

# 使用清华镜像加速 pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.4 持久化数据

| 卷 | 宿主机路径 | 容器路径 | 用途 |
|----|-----------|---------|------|
| FAISS 索引 | `./data/vectorstore` | `/app/vectorstore/faiss_index` | 向量索引持久化 |
| 上传文件 | `./data/uploads` | `/app/uploads` | 用户上传文档 |
| 对话历史 | `./data/chat_history` | `/app/chat_history` | 会话历史 JSON |

---

## 九、以"代码审查"为例的完整推理链

```
用户输入: "帮我审查这段代码：password='admin123'; sql='SELECT * FROM users WHERE name='+username"

Step 1: 快速路径判断
  _is_simple_message("帮我审查这段代码...") → False
  跳过 → 进入 ReAct Agent

Step 2: System Prompt 构建
  ① 专家人设: "你是一位资深全栈代码分析专家..."
  ② 长期记忆: 检索用户偏好（如有）
  ③ 工具指南: 告诉 LLM 代码审查场景该用哪些工具

Step 3: ReAct Think（思考）
  LLM 分析输入:
  - 用户提供了代码片段
  - 代码中有硬编码密码 + SQL 字符串拼接
  - 这涉及"安全性"和"代码质量"两个维度
  → 决策: 先调用 code_security_analysis，再调用 code_optimization

Step 4: Act - code_security_analysis
  输入: code="password='admin123'; sql='SELECT * FROM users WHERE name='+username", language="python"
  
  工具内部:
  ┌─────────────────────────────────────┐
  │ System: "你是一位资深代码安全分析师"    │
  │ 检测范围: SQL注入、硬编码密钥、命令注入  │
  ├─────────────────────────────────────┤
  │ LLM (temperature=0) 分析:            │
  │ 🔴 严重: 硬编码密码 'admin123'        │
  │   风险: 密码泄露可导致未授权访问        │
  │   修复: 使用 os.environ.get('DB_PWD') │
  │ 🔴 严重: SQL 字符串拼接 → 注入风险     │
  │   风险: 攻击者可执行任意 SQL          │
  │   修复: 使用参数化查询 cursor.execute(  │
  │         sql, (username,))            │
  └─────────────────────────────────────┘
  
  → 返回结构化安全分析报告

Step 5: Act - code_optimization
  输入: 同一段代码, language="python"
  
  工具内部:
  ┌─────────────────────────────────────┐
  │ System: "你是一位资深软件架构师"        │
  │ 维度: 可读性/性能/规范/架构             │
  ├─────────────────────────────────────┤
  │ LLM (temperature=0.3) 分析:          │
  │ 🟡 建议: 使用 os.getenv() 读取配置     │
  │ 🟡 建议: 使用参数化查询防注入           │
  │ 🟢 建议: 添加类型注解和异常处理          │
  │ 🟢 建议: 使用上下文管理器管理连接         │
  └─────────────────────────────────────┘
  
  → 返回结构化优化建议

Step 6: Observe（综合输出）
  LLM 将两个工具的结果整合，按专家人设格式输出:
  🔴 严重 → 🟡 警告 → 🟢 建议
  问题描述 → 风险说明 → 修复方案（含代码示例）

Step 7: 持久化
  - 对话历史写入 JSON 文件
  - 更新长期记忆（FAISS 向量库）
  - 检查是否需要会话总结

---

前端展示（SSE 流式事件）:

┌──────────────────────────────────────┐
│  ⏳ 正在分析您的问题...               │  ← event: thinking
│                                      │
│  🔧 正在调用工具：code_security_analysis│  ← event: tool_call
│  ✅ 工具调用完成：code_security_analysis│  ← event: tool_result
│                                      │
│  🔧 正在调用工具：code_optimization    │  ← event: tool_call
│  ✅ 工具调用完成：code_optimization     │  ← event: tool_result
│                                      │
│  🔴 严重：硬编码密码                   │  ← event: token（逐字流式）
│  🟡 建议：使用参数化查询...            │
└──────────────────────────────────────┘
```

---

## 十、预置知识库

启动时自动加载 6 个专家知识库到 FAISS 向量库：

| 知识库文件 | 内容 | 片段数 |
|-----------|------|--------|
| `code_quality.md` | 命名规范、函数设计、复杂度控制、DRY 原则、注释与文档 | ~12 |
| `security.md` | 注入攻击、认证授权、敏感信息保护、输入校验、依赖安全 | ~18 |
| `performance.md` | 性能优化模式与反模式 | ~15 |
| `design_patterns.md` | 常用设计模式及适用场景 | ~20 |
| `refactoring.md` | 重构手法与最佳实践 | ~15 |
| `code_review.md` | Code Review Checklist（5 维度评审清单） | ~25 |

RAG 检索时，从知识库中检索最相关的片段作为上下文注入 LLM，实现"先结合知识库中的最佳实践，再结合自身知识给出全面分析"。

---

## 十一、设计亮点

| 编号 | 设计点 | 实现方式 | 价值 |
|------|--------|---------|------|
| 1 | **混合路由** | 规则引擎 + ReAct Agent | 简单消息零延迟，复杂任务智能决策 |
| 2 | **工具人格化** | 每个工具独立 System Prompt + temperature | 安全分析严谨，优化建议灵活 |
| 3 | **决策指南** | 自然语言场景→工具映射表 | 比纯 function description 准确率更高 |
| 4 | **专家可切换** | YAML 配置驱动人设 | 换领域只需改配置文件 |
| 5 | **流式状态透明** | thinking/tool_call/tool_result/token 事件 | 用户可见 Agent 思考过程 |
| 6 | **三层记忆** | 窗口 + 压缩 + 长期记忆 | 短对话快速、长对话不丢上下文 |
| 7 | **异步 Embedding** | 并发调用 API | 大文档上传显著加速 |
| 8 | **文档去重** | SHA256 哈希 + 注册表 | 防止重复上传浪费 token |
| 9 | **多租户隔离** | 按 user_id 分目录 | 用户数据物理隔离 |
| 10 | **单容器部署** | FastAPI 内置静态文件托管 | 无需 Nginx，简化部署 |
| 11 | **异常安全** | SSE 流 try/except + error 事件 | 异常时流正常关闭，前端可展示错误 |
| 12 | **知识库预加载** | 启动时自动加载 6 个知识库 | 开箱即用，无需手动上传 |

---

## 十二、依赖清单

```
fastapi>=0.115.0              # Web 框架
uvicorn>=0.30.0               # ASGI 服务器
python-dotenv>=1.0.0          # 环境变量加载
langchain>=0.3.0              # LLM 应用框架
langchain-openai>=0.2.0       # OpenAI 兼容 LLM 客户端
langchain-community>=0.3.0    # 社区扩展（FileChatMessageHistory 等）
dashscope>=1.20.0             # 阿里云百炼 SDK
faiss-cpu>=1.8.0              # 向量相似度检索
python-multipart>=0.0.9       # 文件上传支持
pydantic>=2.0.0               # 数据校验
pymupdf>=1.24.0               # PDF 文档解析
python-docx>=1.0.0            # DOCX 文档解析
pyyaml>=6.0                   # YAML 配置解析
```

---

## 十三、核心文件职责速查

| 文件 | 行数 | 核心职责 |
|------|------|---------|
| `main.py` | 65 | FastAPI 应用入口，启动/健康检查/静态文件托管 |
| `config.py` | 80+ | 全局配置管理，多租户路径，环境变量 |
| `agent/agent.py` | 558 | ReAct Agent 核心：组装、路由、流式推理、记忆管理 |
| `agent/tools.py` | 123 | 5 个专业工具定义 |
| `api/routes.py` | 300+ | 所有 REST + SSE 接口实现 |
| `api/schemas.py` | - | Pydantic 请求/响应数据模型 |
| `chains/rag_chain.py` | - | RAG 检索增强生成链 |
| `chains/summary_chain.py` | - | 文档总结链 |
| `models/llm.py` | - | LLM 客户端封装（DashScope OpenAI 兼容） |
| `models/embedding.py` | - | Embedding 客户端（异步并发） |
| `vectorstore/store.py` | - | FAISS 向量存储 CRUD |
| `document/loader.py` | - | 文档加载/分割/验证 |
| `expert/profile.py` | - | YAML 专家人设加载 |
| `expert/knowledge_loader.py` | - | 预置知识库自动加载 |
| `agent/context_compressor.py` | - | 智能上下文压缩算法 |
| `agent/long_term_memory.py` | - | 长期记忆管理（FAISS） |
| `agent/session_summarizer.py` | - | 会话自动总结 |
| `expert_profile.yaml` | 30 | 专家人设 + 知识库配置 |
| `docker-compose.yml` | 31 | Docker 容器编排 |
| `Dockerfile` | 24 | Docker 镜像构建 |
| `web/src/App.vue` | - | 前端主应用组件 |
| `web/src/api.js` | - | SSE 流式 API 客户端 |