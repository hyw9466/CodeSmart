"""阿里云 DashScope Embedding 封装：同步 + 异步并发调用。

依赖环境变量：
- DASHSCOPE_API_KEY: 阿里云 DashScope 的 API Key
- EMBEDDING_MODEL: 模型名称（默认 text-embedding-v4）
- EMBEDDING_CONCURRENCY: 并发数（默认 3）
"""

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

    支持同步（embed_documents / embed_query）和异步（aembed_documents / aembed_query）两种调用方式。
    异步方式受 EMBEDDING_CONCURRENCY 控制并发数。
    
    支持的模型包括：
    - text-embedding-v4（文本专用，推荐）
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int = 60,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._model = model or config.EMBEDDING_MODEL
        self._api_key = api_key or config.DASHSCOPE_API_KEY
        self._timeout = timeout
        self._base_url = base_url

        if not self._api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY 未配置，请设置环境变量或在 .env 文件中配置"
            )

    @property
    def model(self) -> str:
        return self._model

    def _embed_one(self, text: str) -> List[float]:
        """调用 DashScope Embedding API 生成单条文本的向量。"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        payload = {"model": self._model, "input": text}

        try:
            resp = requests.post(
                f"{self._base_url}/embeddings",
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Embedding API 连接超时（{self._timeout}秒），"
                "请检查网络连接"
            )
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"无法连接到 DashScope Embedding API：{str(e)}\n"
                "请确保网络可以访问阿里云 DashScope 服务"
            )
        except Exception as e:
            raise RuntimeError(f"Embedding 调用异常: {str(e)}")

        if resp.status_code != 200:
            error_msg = resp.text
            try:
                error_data = resp.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", error_msg)
            except Exception:
                pass
            raise RuntimeError(f"Embedding 调用失败: {resp.status_code} - {error_msg}")

        return resp.json()["data"][0]["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """同步批量生成文档 embedding（串行）。"""
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        """同步生成单条查询的 embedding。"""
        return self._embed_one(text)

    async def _aembed_one(self, text: str, semaphore: asyncio.Semaphore) -> List[float]:
        """异步包装：在线程池中执行同步调用，受信号量控制并发。"""
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(_executor, self._embed_one, text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步并发生成文档 embedding，并发数受 EMBEDDING_CONCURRENCY 控制。"""
        sem = asyncio.Semaphore(config.EMBEDDING_CONCURRENCY)
        tasks = [self._aembed_one(t, sem) for t in texts]
        return await asyncio.gather(*tasks)

    async def aembed_query(self, text: str) -> List[float]:
        """异步生成单条查询的 embedding。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._embed_one, text)


# 模块级单例，供 vectorstore 等模块直接引用
instance = DashScopeEmbedding()
