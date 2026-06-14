"""FAISS 向量索引管理：构建、检索、持久化。

支持多租户隔离：
- 基础知识库（所有用户共享，只读）
- 用户知识库（每个用户独立，可增删）
- 检索时合并两个知识库
"""

from __future__ import annotations

import os
from typing import List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import config
from models.embedding import instance as _embedding

# 基础知识库单例
_base_store: Optional[FAISS] = None

# 用户知识库缓存 {user_id: FAISS}
_user_stores: dict = {}


def _get_base_store() -> Optional[FAISS]:
    """获取基础知识库实例（所有用户共享，只读）。"""
    global _base_store
    if _base_store is not None:
        return _base_store
    index_path = os.path.join(config.FAISS_INDEX_DIR, "index.faiss")
    if os.path.exists(index_path):
        _base_store = FAISS.load_local(
            config.FAISS_INDEX_DIR,
            _embedding,
            allow_dangerous_deserialization=True,
        )
    return _base_store


def _get_user_store(user_id: str) -> Optional[FAISS]:
    """获取用户知识库实例。"""
    if user_id in _user_stores:
        return _user_stores[user_id]
    
    user_faiss_dir = config.get_user_faiss_dir(user_id)
    index_path = os.path.join(user_faiss_dir, "index.faiss")
    
    if os.path.exists(index_path):
        _user_stores[user_id] = FAISS.load_local(
            user_faiss_dir,
            _embedding,
            allow_dangerous_deserialization=True,
        )
        return _user_stores[user_id]
    
    return None


def _merge_retrievers(base_retriever, user_retriever, k: int = 4):
    """合并基础知识库和用户知识库的检索器。"""
    from langchain.retrievers import EnsembleRetriever
    
    if base_retriever and user_retriever:
        # 两个都有，合并检索
        return EnsembleRetriever(
            retrievers=[base_retriever, user_retriever],
            weights=[0.5, 0.5],  # 基础库和用户库权重各半
        )
    elif base_retriever:
        return base_retriever
    elif user_retriever:
        return user_retriever
    else:
        raise RuntimeError("向量库为空，请先上传文档")


def add_documents(docs: List[Document], user_id: Optional[str] = None) -> int:
    """将文档列表添加到向量库并持久化。
    
    Args:
        docs: 文档列表
        user_id: 用户ID，如果为 None 则添加到基础知识库
    
    Returns:
        新增文档数量
    """
    if not docs:
        return 0
    
    if user_id is None:
        # 添加到基础知识库
        global _base_store
        current = _get_base_store()
        if current is None:
            _base_store = FAISS.from_documents(docs, _embedding)
        else:
            _base_store = current
            _base_store.add_documents(docs)
        _base_store.save_local(config.FAISS_INDEX_DIR)
    else:
        # 添加到用户知识库
        config.ensure_user_dirs(user_id)
        user_faiss_dir = config.get_user_faiss_dir(user_id)
        
        current = _get_user_store(user_id)
        if current is None:
            _user_stores[user_id] = FAISS.from_documents(docs, _embedding)
        else:
            _user_stores[user_id] = current
            _user_stores[user_id].add_documents(docs)
        _user_stores[user_id].save_local(user_faiss_dir)
    
    return len(docs)


async def async_add_documents(docs: List[Document], user_id: Optional[str] = None) -> int:
    """异步并发入库：先并发生成 embedding，再批量写入 FAISS。
    
    Args:
        docs: 文档列表
        user_id: 用户ID，如果为 None 则添加到基础知识库
    
    Returns:
        新增文档数量
    """
    if not docs:
        return 0

    texts = [doc.page_content for doc in docs]
    embeddings = await _embedding.aembed_documents(texts)

    text_embedding_pairs = list(zip(texts, embeddings))
    metadatas = [doc.metadata for doc in docs]

    if user_id is None:
        # 添加到基础知识库
        global _base_store
        current = _get_base_store()
        if current is None:
            _base_store = FAISS.from_embeddings(
                text_embedding_pairs, _embedding, metadatas=metadatas
            )
        else:
            _base_store = current
            _base_store.add_embeddings(text_embedding_pairs, metadatas=metadatas)
        _base_store.save_local(config.FAISS_INDEX_DIR)
    else:
        # 添加到用户知识库
        config.ensure_user_dirs(user_id)
        user_faiss_dir = config.get_user_faiss_dir(user_id)
        
        current = _get_user_store(user_id)
        if current is None:
            _user_stores[user_id] = FAISS.from_embeddings(
                text_embedding_pairs, _embedding, metadatas=metadatas
            )
        else:
            _user_stores[user_id] = current
            _user_stores[user_id].add_embeddings(text_embedding_pairs, metadatas=metadatas)
        _user_stores[user_id].save_local(user_faiss_dir)
    
    return len(docs)


def get_retriever(k: int = 4, user_id: Optional[str] = None):
    """获取检索器，返回最相关的 k 个文档片段。
    
    Args:
        k: 返回的文档数量
        user_id: 用户ID，用于合并用户知识库
    
    Returns:
        合并后的检索器
    """
    base_store = _get_base_store()
    user_store = _get_user_store(user_id) if user_id else None
    
    base_retriever = base_store.as_retriever(search_kwargs={"k": k}) if base_store else None
    user_retriever = user_store.as_retriever(search_kwargs={"k": k}) if user_store else None
    
    return _merge_retrievers(base_retriever, user_retriever, k)


def has_index(user_id: Optional[str] = None) -> bool:
    """检查是否有可用的索引（基础知识库或用户知识库）。"""
    base_exists = _get_base_store() is not None
    user_exists = _get_user_store(user_id) is not None if user_id else False
    return base_exists or user_exists


async def delete_documents_by_source(source_filename: str, user_id: Optional[str] = None) -> int:
    """根据源文件名删除向量库中的相关文档片段。
    
    注意：FAISS 不支持单个向量删除，采用重建索引方式。
    
    Args:
        source_filename: 源文件名
        user_id: 用户ID，如果为 None 则从基础知识库删除（不允许）
    
    Returns:
        删除的片段数量
    """
    if user_id is None:
        # 不允许删除基础知识库
        raise RuntimeError("基础知识库是只读的，不允许删除")
    
    user_store = _get_user_store(user_id)
    if user_store is None:
        return 0

    # 获取所有文档及其 metadata
    all_docs = user_store.docstore._dict

    # 筛选出不删除的文档
    docs_to_keep = []
    deleted_count = 0
    for doc_id, doc in all_docs.items():
        if doc.metadata.get("source") == source_filename:
            deleted_count += 1
        else:
            docs_to_keep.append(doc)

    if deleted_count == 0:
        return 0

    # 重建索引
    user_faiss_dir = config.get_user_faiss_dir(user_id)
    if docs_to_keep:
        # 重新生成 embedding（异步）
        texts = [doc.page_content for doc in docs_to_keep]
        embeddings = await _embedding.aembed_documents(texts)
        text_embedding_pairs = list(zip(texts, embeddings))
        metadatas = [doc.metadata for doc in docs_to_keep]
        _user_stores[user_id] = FAISS.from_embeddings(
            text_embedding_pairs, _embedding, metadatas=metadatas
        )
    else:
        # 没有剩余文档，清空索引
        _user_stores[user_id] = None
        # 删除索引文件
        import shutil
        if os.path.exists(user_faiss_dir):
            shutil.rmtree(user_faiss_dir)
        os.makedirs(user_faiss_dir, exist_ok=True)
        return deleted_count

    _user_stores[user_id].save_local(user_faiss_dir)
    return deleted_count


def list_user_documents(user_id: str) -> List[dict]:
    """列出用户知识库中的文档。"""
    user_store = _get_user_store(user_id)
    if user_store is None:
        return []
    
    docs = []
    seen_sources = set()
    for doc_id, doc in user_store.docstore._dict.items():
        source = doc.metadata.get("source", "unknown")
        if source not in seen_sources:
            seen_sources.add(source)
            docs.append({
                "filename": source,
                "type": "user",  # 标记为用户文档
            })
    return docs


def list_base_documents() -> List[dict]:
    """列出基础知识库中的文档。"""
    base_store = _get_base_store()
    if base_store is None:
        return []
    
    docs = []
    seen_sources = set()
    for doc_id, doc in base_store.docstore._dict.items():
        source = doc.metadata.get("source", "unknown")
        if source not in seen_sources:
            seen_sources.add(source)
            docs.append({
                "filename": source,
                "type": "base",  # 标记为基础文档
            })
    return docs


def list_all_documents(user_id: str) -> List[dict]:
    """列出所有文档（基础知识库 + 用户知识库）。"""
    base_docs = list_base_documents()
    user_docs = list_user_documents(user_id)
    return base_docs + user_docs
