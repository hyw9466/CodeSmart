"""FAISS 向量索引管理：构建、检索、持久化。"""

from __future__ import annotations

import os
from typing import List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import config
from models.embedding import instance as _embedding

# 模块级单例
_store: Optional[FAISS] = None


def _get_store() -> Optional[FAISS]:
    """获取当前 FAISS 实例，如果磁盘上有索引则加载。"""
    global _store
    if _store is not None:
        return _store
    index_path = os.path.join(config.FAISS_INDEX_DIR, "index.faiss")
    if os.path.exists(index_path):
        _store = FAISS.load_local(
            config.FAISS_INDEX_DIR,
            _embedding,
            allow_dangerous_deserialization=True,
        )
    return _store


def add_documents(docs: List[Document]) -> int:
    """将文档列表添加到 FAISS 索引并持久化，返回新增数量。"""
    global _store
    if not docs:
        return 0
    current = _get_store()
    if current is None:
        _store = FAISS.from_documents(docs, _embedding)
    else:
        _store = current
        _store.add_documents(docs)
    _store.save_local(config.FAISS_INDEX_DIR)
    return len(docs)


async def async_add_documents(docs: List[Document]) -> int:
    """异步并发入库：先并发生成 embedding，再批量写入 FAISS。"""
    global _store
    if not docs:
        return 0

    texts = [doc.page_content for doc in docs]
    embeddings = await _embedding.aembed_documents(texts)

    text_embedding_pairs = list(zip(texts, embeddings))
    metadatas = [doc.metadata for doc in docs]

    current = _get_store()
    if current is None:
        _store = FAISS.from_embeddings(
            text_embedding_pairs, _embedding, metadatas=metadatas
        )
    else:
        _store = current
        _store.add_embeddings(text_embedding_pairs, metadatas=metadatas)
    _store.save_local(config.FAISS_INDEX_DIR)
    return len(docs)


def get_retriever(k: int = 4):
    """获取 FAISS 检索器，返回最相关的 k 个文档片段。"""
    store = _get_store()
    if store is None:
        raise RuntimeError("向量库为空，请先上传文档")
    return store.as_retriever(search_kwargs={"k": k})


def has_index() -> bool:
    """检查是否已有可用索引。"""
    return _get_store() is not None


async def delete_documents_by_source(source_filename: str) -> int:
    """根据源文件名删除向量库中的相关文档片段。

    注意：FAISS 不支持单个向量删除，采用重建索引方式。
    返回删除的片段数量。
    """
    global _store
    store = _get_store()
    if store is None:
        return 0

    # 获取所有文档及其 metadata
    all_docs = store.docstore._dict

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
    if docs_to_keep:
        # 重新生成 embedding（异步）
        texts = [doc.page_content for doc in docs_to_keep]
        embeddings = await _embedding.aembed_documents(texts)
        text_embedding_pairs = list(zip(texts, embeddings))
        metadatas = [doc.metadata for doc in docs_to_keep]
        _store = FAISS.from_embeddings(
            text_embedding_pairs, _embedding, metadatas=metadatas
        )
    else:
        # 没有剩余文档，清空索引
        _store = None
        # 删除索引文件
        import shutil
        index_dir = config.FAISS_INDEX_DIR
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir)
        os.makedirs(index_dir, exist_ok=True)
        return deleted_count

    _store.save_local(config.FAISS_INDEX_DIR)
    return deleted_count
