"""Embedding 封装：同步 + 异步并发，通过阿里云 DashScope API 调用嵌入模型。"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

import requests
from langchain_core.embeddings import Embeddings

import config

# 线程池供异步方法复用
_executor = ThreadPoolExecutor(max_workers=config.EMBEDDING_CONCURRENCY)


class DashScopeEmbedding(Embeddings):
    """通过阿里云 DashScope API 调用 Embedding 模型。

    支持模型：tongyi-embedding-vision-plus, text-embedding-v2, text-embedding-v3 等
    
    同步方法：embed_documents / embed_query（逐条串行）
    异步方法：aembed_documents / aembed_query（并发，受 EMBEDDING_CONCURRENCY 控制）
    """

    model: str = config.EMBEDDING_MODEL
    api_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    timeout: int = 30  # 请求超时时间（秒）

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not config.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY 未配置，请在 .env 文件中设置")

    def _embed_one(self, text: str) -> List[float]:
        """同步调用一次 DashScope Embedding API。"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.DASHSCOPE_API_KEY}"
        }
        
        payload = {
            "model": self.model,
            "input": [text]
        }
        
        try:
            resp = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Embedding API 连接超时（{self.timeout}秒）。"
                "请检查网络连接，或尝试使用代理。"
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "无法连接到 Embedding API。"
                "请检查网络连接，或确认 DASHSCOPE_API_KEY 是否已正确配置。"
            )
        except Exception as e:
            raise RuntimeError(f"Embedding 调用异常: {str(e)}")
        
        if resp.status_code != 200:
            error_msg = resp.text
            try:
                error_data = resp.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", error_msg)
            except:
                pass
            raise RuntimeError(
                f"Embedding 调用失败: {resp.status_code} - {error_msg}"
            )
        
        result = resp.json()
        return result["data"][0]["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """同步串行：对文档列表生成 embedding。"""
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        """同步：对单条查询生成 embedding。"""
        return self._embed_one(text)

    async def _aembed_one(
        self, text: str, semaphore: asyncio.Semaphore
    ) -> List[float]:
        """异步包装：在线程池中执行同步调用，受信号量控制并发。"""
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(_executor, self._embed_one, text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步并发：对文档列表并行生成 embedding。

        并发数受 config.EMBEDDING_CONCURRENCY 控制，避免打爆 API 限流。
        """
        sem = asyncio.Semaphore(config.EMBEDDING_CONCURRENCY)
        tasks = [self._aembed_one(t, sem) for t in texts]
        return await asyncio.gather(*tasks)

    async def aembed_query(self, text: str) -> List[float]:
        """异步：对单条查询生成 embedding。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._embed_one, text)
