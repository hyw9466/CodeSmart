"""应用配置：所有配置项集中在此文件管理，避免硬编码。

通过环境变量或 .env 文件覆盖默认值。
"""

import os
from dotenv import load_dotenv

# 获取 config.py 所在目录（即项目根目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 加载 .env 文件
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ═══════════════════════════════════════════════════════════
# Embedding 模型配置（阿里云 DashScope）
# ═══════════════════════════════════════════════════════════
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
EMBEDDING_CONCURRENCY: int = int(os.getenv("EMBEDDING_CONCURRENCY", "3"))

# ═══════════════════════════════════════════════════════════
# LLM 模型配置（阿里云 DashScope）
# ═══════════════════════════════════════════════════════════
LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen3.6-plus")
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ═══════════════════════════════════════════════════════════
# 多租户隔离配置
# ═══════════════════════════════════════════════════════════
# 数据根目录
DATA_DIR: str = os.path.join(BASE_DIR, "data")

# 基础知识库目录（只读，所有用户共享）
BASE_KNOWLEDGE_DIR: str = os.path.join(DATA_DIR, "base_knowledge")

# 用户数据根目录
USERS_DIR: str = os.path.join(DATA_DIR, "users")

# ═══════════════════════════════════════════════════════════
# 持久化路径（兼容旧版本，现在由用户管理模块动态设置）
# ═══════════════════════════════════════════════════════════
# FAISS 向量索引持久化目录（基础知识库）
FAISS_INDEX_DIR: str = os.path.join(BASE_KNOWLEDGE_DIR, "faiss_index")

# 上传文件临时目录（兼容旧版本）
UPLOAD_DIR: str = os.path.join(DATA_DIR, "uploads")

# 对话历史持久化目录（兼容旧版本）
CHAT_HISTORY_DIR: str = os.path.join(DATA_DIR, "chat_history")

# ═══════════════════════════════════════════════════════════
# Agent 配置
# ═══════════════════════════════════════════════════════════
# 对话记忆窗口大小（取最近 K 轮对话作为上下文）
MEMORY_WINDOW_K: int = int(os.getenv("MEMORY_WINDOW_K", "3"))

# ═══════════════════════════════════════════════════════════
# 长期记忆配置
# ═══════════════════════════════════════════════════════════
# 记忆过期天数（超过此天数的记忆会被自动清理）
MEMORY_EXPIRE_DAYS: int = int(os.getenv("MEMORY_EXPIRE_DAYS", "30"))
# 每次检索返回的记忆数量
MEMORY_RETRIEVE_K: int = int(os.getenv("MEMORY_RETRIEVE_K", "3"))
# 会话总结触发阈值（消息数）
MEMORY_SUMMARY_THRESHOLD: int = int(os.getenv("MEMORY_SUMMARY_THRESHOLD", "5"))


# ═══════════════════════════════════════════════════════════
# 用户数据管理工具函数
# ═══════════════════════════════════════════════════════════
def get_user_dir(user_id: str) -> str:
    """获取用户数据目录。"""
    return os.path.join(USERS_DIR, user_id)


def get_user_faiss_dir(user_id: str) -> str:
    """获取用户 FAISS 向量索引目录。"""
    return os.path.join(USERS_DIR, user_id, "faiss_index")


def get_user_upload_dir(user_id: str) -> str:
    """获取用户上传文件目录。"""
    return os.path.join(USERS_DIR, user_id, "uploads")


def get_user_chat_history_dir(user_id: str) -> str:
    """获取用户聊天历史目录。"""
    return os.path.join(USERS_DIR, user_id, "chat_history")


def ensure_user_dirs(user_id: str) -> None:
    """确保用户目录存在。"""
    os.makedirs(get_user_faiss_dir(user_id), exist_ok=True)
    os.makedirs(get_user_upload_dir(user_id), exist_ok=True)
    os.makedirs(get_user_chat_history_dir(user_id), exist_ok=True)
