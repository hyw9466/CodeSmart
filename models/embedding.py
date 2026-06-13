"""Embedding 封装：支持多后端（Jina / DashScope / OpenAI 兼容）。

通过环境变量切换提供商，无需修改代码即可适配不同网络环境：
- jina      : Jina AI（海外，国内需代理）
- dashscope : 阿里云 DashScope（国内直连）
- openai    : OpenAI 或任意兼容端点
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


class JinaEmbedding(Embeddings):
    """通过 Jina AI API 调用 Embedding 模型。"""

    model: str = config.EMBEDDING_MODEL
    api_url: str = "https://api.jina.ai/v1/embeddings"
    timeout: int = 60

    def __init__(self, api_key: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key or config.JINA_API_KEY or config.EMBEDDING_API_KEY
        if not self._api_key:
            raise ValueError(
                "Jina Embedding 需要 API Key，请设置 JINA_API_KEY 或 EMBEDDING_API_KEY"
            )

    def _embed_one(self, text: str) -> List[float]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        payload = {"model": self.model, "input": text}
        try:
            resp = requests.post(
                self.api_url, json=payload, headers=headers, timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Embedding API 连接超时（{self.timeout}秒）。"
                "请检查网络连接，或尝试切换 EMBEDDING_PROVIDER。"
            )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "无法连接到 Jina Embedding API（api.jina.ai）。"
                "国内网络建议切换 EMBEDDING_PROVIDER=dashscope"
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

        result = resp.json()
        return result["data"][0]["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_one(text)

    async def _aembed_one(
        self, text: str, semaphore: asyncio.Semaphore
    ) -> List[float]:
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(_executor, self._embed_one, text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        sem = asyncio.Semaphore(config.EMBEDDING_CONCURRENCY)
        tasks = [self._aembed_one(t, sem) for t in texts]
        return await asyncio.gather(*tasks)

    async def aembed_query(self, text: str) -> List[float]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._embed_one, text)


class OpenAICompatibleEmbedding(Embeddings):
    """OpenAI 兼容格式的 Embedding（适用于 DashScope / 硅基流动 / OpenRouter 等）。

    底层复用 langchain_openai.OpenAIEmbeddings，天然支持异步并发与重试。
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ):
        # 延迟导入，避免在未安装 langchain_openai 时直接报错
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as e:
            raise ImportError(
                "使用 OpenAI 兼容嵌入需要安装 langchain-openai，"
                f"请执行: pip install langchain-openai\n原始错误: {e}"
            )

        self._model = model or config.EMBEDDING_MODEL
        self._api_key = api_key or config.EMBEDDING_API_KEY
        self._base_url = base_url or config.EMBEDDING_BASE_URL

        if not self._api_key:
            raise ValueError(
                "OpenAI 兼容 Embedding 需要 API Key，"
                "请设置 EMBEDDING_API_KEY"
            )

        self._client = OpenAIEmbeddings(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            chunk_size=16,
            **kwargs,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._client.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._client.embed_query(text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return await self._client.aembed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        return await self._client.aembed_query(text)


def create_embedding() -> Embeddings:
    """工厂函数：根据配置创建对应的 Embedding 实例。"""
    provider = config.EMBEDDING_PROVIDER.lower()

    if provider == "jina":
        return JinaEmbedding()

    if provider in ("dashscope", "openai"):
        return OpenAICompatibleEmbedding()

    raise ValueError(
        f"不支持的 EMBEDDING_PROVIDER: {provider}，"
        f"可选值: jina, dashscope, openai"
    )
