"""长期记忆系统：使用向量数据库存储用户长期记忆。

支持：
- 添加记忆片段（用户偏好、关键知识点、对话摘要）
- 检索相关记忆（基于语义相似度）
- 记忆重要性排序
- 自动过期清理
"""

from __future__ import annotations

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import config
from models.embedding import instance as _embedding


class LongTermMemory:
    """长期记忆管理器"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory_dir = self._get_memory_dir()
        self._store = None
        self._meta_store = None
        self._load_or_create()
    
    def _get_memory_dir(self) -> str:
        """获取用户记忆目录"""
        return os.path.join(config.get_user_dir(self.user_id), "memory")
    
    def _load_or_create(self):
        """加载或创建记忆存储"""
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # 加载向量索引
        index_path = os.path.join(self.memory_dir, "index")
        if os.path.exists(os.path.join(index_path, "index.faiss")):
            self._store = FAISS.load_local(
                index_path,
                _embedding,
                allow_dangerous_deserialization=True
            )
        else:
            # 创建空索引（使用第一个嵌入来确定维度）
            self._store = None
        
        # 加载元数据存储
        meta_path = os.path.join(self.memory_dir, "memory_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                self._meta_store = json.load(f)
        else:
            self._meta_store = {"memories": [], "stats": {}}
    
    def _save(self):
        """持久化存储"""
        if self._store:
            index_path = os.path.join(self.memory_dir, "index")
            self._store.save_local(index_path)
        
        meta_path = os.path.join(self.memory_dir, "memory_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self._meta_store, f, ensure_ascii=False, indent=2)
    
    def add_memory(self, content: str, memory_type: str = "general",
                   importance: int = 5, metadata: Optional[Dict] = None) -> str:
        """添加记忆片段
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型 (general/preference/topic/fact/question)
            importance: 重要性 (1-10)
            metadata: 额外元数据
        
        Returns:
            记忆ID
        """
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(content)}"
        
        # 创建文档对象
        doc_metadata = {
            "user_id": self.user_id,
            "memory_id": memory_id,
            "memory_type": memory_type,
            "importance": importance,
            "created_at": datetime.now().isoformat(),
            "access_count": 0
        }
        if metadata:
            doc_metadata.update(metadata)
        
        doc = Document(page_content=content, metadata=doc_metadata)
        
        # 添加到向量存储
        if self._store is None:
            # 创建新索引
            self._store = FAISS.from_documents([doc], _embedding)
        else:
            self._store.add_documents([doc])
        
        # 更新元数据存储
        self._meta_store["memories"].append({
            "memory_id": memory_id,
            "type": memory_type,
            "importance": importance,
            "created_at": doc_metadata["created_at"]
        })
        
        self._save()
        return memory_id
    
    def retrieve(self, query: str, k: int = 3, 
                 memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """检索相关记忆
        
        Args:
            query: 查询内容
            k: 返回数量
            memory_type: 过滤记忆类型（可选）
        
        Returns:
            相关记忆列表
        """
        if self._store is None or self._store.index.ntotal == 0:
            return []
        
        # 执行检索
        results = self._store.similarity_search(query, k=k * 2)  # 多获取一些用于过滤
        
        # 过滤和排序
        filtered = []
        for doc in results:
            # 类型过滤
            if memory_type and doc.metadata.get("memory_type") != memory_type:
                continue
            
            filtered.append({
                "memory_id": doc.metadata.get("memory_id"),
                "content": doc.page_content,
                "type": doc.metadata.get("memory_type"),
                "importance": doc.metadata.get("importance", 5),
                "created_at": doc.metadata.get("created_at"),
                "access_count": doc.metadata.get("access_count", 0)
            })
        
        # 按重要性排序，取前 k 个
        filtered.sort(key=lambda x: x["importance"], reverse=True)
        return filtered[:k]
    
    def get_memories_by_type(self, memory_type: str, limit: int = 10) -> List[Dict]:
        """按类型获取记忆"""
        if self._store is None or self._store.index.ntotal == 0:
            return []
        
        # 获取所有记忆
        all_docs = self._store.similarity_search("*", k=100)
        filtered = []
        
        for doc in all_docs:
            if doc.metadata.get("memory_type") == memory_type:
                filtered.append({
                    "memory_id": doc.metadata.get("memory_id"),
                    "content": doc.page_content,
                    "type": doc.metadata.get("memory_type"),
                    "importance": doc.metadata.get("importance", 5),
                    "created_at": doc.metadata.get("created_at")
                })
        
        filtered.sort(key=lambda x: x["created_at"], reverse=True)
        return filtered[:limit]
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除指定记忆"""
        if self._store is None:
            return False
        
        # FAISS 不支持直接删除，需要重建索引
        index_path = os.path.join(self.memory_dir, "index")
        
        # 获取所有文档，排除要删除的
        all_docs = []
        for doc in self._store.similarity_search("*", k=1000):
            if doc.metadata.get("memory_id") != memory_id:
                all_docs.append(doc)
        
        # 重建索引
        if all_docs:
            self._store = FAISS.from_documents(all_docs, _embedding)
        else:
            self._store = None
        
        # 更新元数据
        self._meta_store["memories"] = [
            m for m in self._meta_store["memories"] 
            if m["memory_id"] != memory_id
        ]
        
        self._save()
        return True
    
    def cleanup_old_memories(self, days_to_keep: int = None) -> int:
        """清理过期记忆
        
        Args:
            days_to_keep: 保留天数，默认使用 config.MEMORY_EXPIRE_DAYS
        """
        if days_to_keep is None:
            days_to_keep = config.MEMORY_EXPIRE_DAYS
        
        if self._store is None:
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        # 获取所有文档
        all_docs = []
        for doc in self._store.similarity_search("*", k=1000):
            created_at = doc.metadata.get("created_at")
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    if created_dt < cutoff_date:
                        deleted_count += 1
                        continue  # 跳过，即删除
                except:
                    pass
            all_docs.append(doc)
        
        # 重建索引
        if all_docs:
            self._store = FAISS.from_documents(all_docs, _embedding)
        else:
            self._store = None
        
        self._save()
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        if self._store is None:
            return {
                "total_memories": 0,
                "memory_types": {},
                "oldest_memory": None,
                "newest_memory": None
            }
        
        # 统计各类型数量
        type_counts = {}
        oldest = None
        newest = None
        
        for doc in self._store.similarity_search("*", k=1000):
            mem_type = doc.metadata.get("memory_type", "general")
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
            
            created_at = doc.metadata.get("created_at")
            if created_at:
                if oldest is None or created_at < oldest:
                    oldest = created_at
                if newest is None or created_at > newest:
                    newest = created_at
        
        return {
            "total_memories": self._store.index.ntotal,
            "memory_types": type_counts,
            "oldest_memory": oldest,
            "newest_memory": newest
        }


# 单例缓存
_memory_instances: Dict[str, LongTermMemory] = {}

def get_memory_manager(user_id: str) -> LongTermMemory:
    """获取用户的长期记忆管理器（单例）"""
    if user_id not in _memory_instances:
        _memory_instances[user_id] = LongTermMemory(user_id)
    return _memory_instances[user_id]