"""应用配置：所有配置项集中在此文件管理，避免硬编码。

通过环境变量或 .env 文件覆盖默认值。
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════
# Embedding 模型配置（阿里云 DashScope）
# ═══════════════════════════════════════════════════════════
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "tongyi-embedding-vision-flash-2026-03-06")
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
EMBEDDING_CONCURRENCY: int = int(os.getenv("EMBEDDING_CONCURRENCY", "3"))

# ═══════════════════════════════════════════════════════════
# LLM 模型配置（阿里云 DashScope）
# ═══════════════════════════════════════════════════════════
LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen3.6-plus")
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ═══════════════════════════════════════════════════════════
# 持久化路径
# ═══════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(__file__)

# FAISS 向量索引持久化目录
FAISS_INDEX_DIR: str = os.path.join(BASE_DIR, "vectorstore", "faiss_index")

# 上传文件临时目录
UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")

# 对话历史持久化目录
CHAT_HISTORY_DIR: str = os.path.join(BASE_DIR, "chat_history")

# ═══════════════════════════════════════════════════════════
# Agent 配置
# ═══════════════════════════════════════════════════════════
# 对话记忆窗口大小（取最近 K 轮对话作为上下文）
MEMORY_WINDOW_K: int = int(os.getenv("MEMORY_WINDOW_K", "3"))
