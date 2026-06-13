import os
from dotenv import load_dotenv

load_dotenv()

# 嵌入模型提供商：jina | dashscope | openai
EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "dashscope")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# 兼容旧配置（jina 专用）
JINA_API_KEY: str = os.getenv("JINA_API_KEY", "")

# 聊天模型配置（阿里云 DashScope）
LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen3.6-plus")
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# FAISS 持久化路径
FAISS_INDEX_DIR: str = os.path.join(os.path.dirname(__file__), "vectorstore", "faiss_index")

# 上传文件临时目录
UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "uploads")

# 对话记忆窗口大小
MEMORY_WINDOW_K: int = 3

# 对话历史持久化目录
CHAT_HISTORY_DIR: str = os.path.join(os.path.dirname(__file__), "chat_history")

# Embedding 并发数（控制同时发出的 API 请求数）
EMBEDDING_CONCURRENCY: int = int(os.getenv("EMBEDDING_CONCURRENCY", "3"))
