"""文档注册表：追踪已入库文件，基于内容 hash 去重。

支持多租户隔离：
- 基础知识库注册表（所有用户共享）
- 用户知识库注册表（每个用户独立）
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, List, Optional

import config

# 基础知识库注册表路径
_BASE_REGISTRY_PATH = os.path.join(config.FAISS_INDEX_DIR, "doc_registry.json")


def _get_user_registry_path(user_id: str) -> str:
    """获取用户注册表路径。"""
    return os.path.join(config.get_user_faiss_dir(user_id), "doc_registry.json")


def _load_registry(user_id: Optional[str] = None) -> Dict[str, str]:
    """加载注册表 {filename: content_hash}。
    
    Args:
        user_id: 用户ID，如果为 None 则加载基础知识库注册表
    """
    if user_id is None:
        registry_path = _BASE_REGISTRY_PATH
    else:
        registry_path = _get_user_registry_path(user_id)
    
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_registry(registry: Dict[str, str], user_id: Optional[str] = None) -> None:
    """持久化注册表。
    
    Args:
        registry: 注册表数据
        user_id: 用户ID，如果为 None 则保存到基础知识库
    """
    if user_id is None:
        registry_path = _BASE_REGISTRY_PATH
    else:
        registry_path = _get_user_registry_path(user_id)
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def compute_hash(content: bytes) -> str:
    """计算文件内容的 SHA256 hash。"""
    return hashlib.sha256(content).hexdigest()


def is_duplicate(filename: str, content_hash: str, user_id: Optional[str] = None) -> bool:
    """检查文件是否已入库（同名且内容相同）。
    
    Args:
        filename: 文件名
        content_hash: 内容哈希
        user_id: 用户ID，如果为 None 则检查基础知识库
    """
    registry = _load_registry(user_id)
    return registry.get(filename) == content_hash


def register_file(filename: str, content_hash: str, user_id: Optional[str] = None) -> None:
    """将文件注册到已入库记录。
    
    Args:
        filename: 文件名
        content_hash: 内容哈希
        user_id: 用户ID，如果为 None 则注册到基础知识库
    """
    registry = _load_registry(user_id)
    registry[filename] = content_hash
    _save_registry(registry, user_id)


def list_documents(user_id: Optional[str] = None) -> List[Dict[str, str]]:
    """列出已入库的文档。
    
    Args:
        user_id: 用户ID，如果为 None 则列出基础知识库文档
    
    Returns:
        文档列表
    """
    registry = _load_registry(user_id)
    return [{"filename": k, "hash": v[:12]} for k, v in registry.items()]


def unregister_file(filename: str, user_id: Optional[str] = None) -> bool:
    """从注册表中删除指定文件的记录。
    
    Args:
        filename: 文件名
        user_id: 用户ID，如果为 None 则从基础知识库删除
    
    Returns:
        是否成功删除
    """
    registry = _load_registry(user_id)
    if filename in registry:
        del registry[filename]
        _save_registry(registry, user_id)
        return True
    return False


def get_document_count(user_id: Optional[str] = None) -> int:
    """获取已入库文档数量。
    
    Args:
        user_id: 用户ID，如果为 None 则统计基础知识库
    """
    return len(_load_registry(user_id))
