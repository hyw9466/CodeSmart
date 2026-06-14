"""智能上下文压缩器：根据当前查询动态选择最相关的对话历史。

支持：
- 基于语义相似度的上下文选择
- 动态窗口调整
- 关键信息保留
- Token 数量控制
"""

from __future__ import annotations

import math
from typing import List, Dict, Any, Optional, Tuple

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

import config
from models.embedding import instance as _embedding


class ContextCompressor:
    """智能上下文压缩器"""
    
    def __init__(self):
        self.embedding = _embedding
    
    def _calculate_relevance(self, message_content: str, query: str) -> float:
        """计算消息与查询的相关性分数"""
        if not message_content or not query:
            return 0.0
        
        try:
            # 生成嵌入向量
            msg_embedding = self.embedding.embed_query(message_content)
            query_embedding = self.embedding.embed_query(query)
            
            # 计算余弦相似度
            dot_product = sum(a * b for a, b in zip(msg_embedding, query_embedding))
            msg_norm = math.sqrt(sum(a * a for a in msg_embedding))
            query_norm = math.sqrt(sum(a * a for a in query_embedding))
            
            if msg_norm == 0 or query_norm == 0:
                return 0.0
            
            return dot_product / (msg_norm * query_norm)
        except Exception:
            return 0.0
    
    def _score_message(self, message: Dict, query: str, index: int, total_messages: int) -> float:
        """为消息打分，综合考虑相关性、位置和类型
        
        分数组成：
        - 相关性分数（0.6权重）
        - 位置分数（0.3权重）：越近的消息权重越高
        - 类型分数（0.1权重）：用户消息和工具结果权重更高
        """
        content = message.get("content", "")
        role = message.get("role", "unknown")
        
        # 相关性分数（0-1）
        relevance = self._calculate_relevance(content, query)
        
        # 位置分数（0-1）：越近越重要
        position_score = (index + 1) / total_messages
        
        # 类型分数（0-1）
        type_score = 0.5  # 默认
        if role == "user":
            type_score = 1.0  # 用户消息最重要
        elif role == "assistant" and len(content) > 100:
            type_score = 0.8  # 长回复可能包含重要信息
        elif role == "tool_result":
            type_score = 0.9  # 工具调用结果很重要
        
        # 综合分数
        score = (relevance * 0.6) + (position_score * 0.3) + (type_score * 0.1)
        return score
    
    def _estimate_tokens(self, text: str) -> int:
        """估算文本的 Token 数量"""
        # 粗略估算：1 Token ≈ 4 字符
        return len(text) // 4
    
    def compress(self, messages: List[Dict], query: str,
                max_tokens: int = 2048, k: Optional[int] = None) -> List[Dict]:
        """智能压缩对话上下文
        
        Args:
            messages: 原始消息列表
            query: 当前查询
            max_tokens: 最大 Token 数限制
            k: 可选的固定窗口大小（优先使用）
        
        Returns:
            压缩后的消息列表
        """
        if not messages:
            return []
        
        # 如果指定了固定窗口大小，使用简单截取
        if k is not None:
            window_size = k * 2  # 每轮 = human + ai
            return messages[-window_size:] if len(messages) > window_size else messages
        
        total_messages = len(messages)
        
        # 为每条消息打分
        scored_messages = []
        for i, msg in enumerate(messages):
            score = self._score_message(msg, query, i, total_messages)
            scored_messages.append((score, i, msg))
        
        # 按分数降序排序
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        # 选择最佳消息组合
        selected = []
        selected_indices = set()
        current_tokens = 0
        
        for score, index, msg in scored_messages:
            # 跳过已选择的
            if index in selected_indices:
                continue
            
            # 估算这条消息的 Token 数
            msg_tokens = self._estimate_tokens(msg.get("content", ""))
            
            # 如果添加后超过限制，跳过
            if current_tokens + msg_tokens > max_tokens:
                continue
            
            selected.append((index, msg))
            selected_indices.add(index)
            current_tokens += msg_tokens
            
            # 达到限制或选够数量
            if current_tokens >= max_tokens or len(selected) >= total_messages:
                break
        
        # 按原始顺序排序
        selected.sort(key=lambda x: x[0])
        
        # 如果选的太少，补充最近的消息
        if len(selected) < 2 and total_messages > 2:
            # 至少保留最近的一轮对话
            recent = messages[-2:]
            recent_indices = set([total_messages - 2, total_messages - 1])
            
            for idx, msg in enumerate(recent):
                orig_idx = total_messages - 2 + idx
                if orig_idx not in selected_indices:
                    selected.append((orig_idx, msg))
            
            # 重新排序
            selected.sort(key=lambda x: x[0])
        
        return [msg for _, msg in selected]
    
    def dynamic_window(self, messages: List[Dict], query: str,
                      base_k: int = 3) -> int:
        """动态计算最佳窗口大小
        
        根据查询复杂度和历史消息相关性调整窗口大小。
        
        Args:
            messages: 消息列表
            query: 当前查询
            base_k: 基础窗口大小
        
        Returns:
            最佳窗口大小（轮数）
        """
        if not messages or not query:
            return base_k
        
        total_messages = len(messages)
        if total_messages <= base_k * 2:
            return base_k
        
        # 计算最近消息的平均相关性
        recent_messages = messages[-base_k * 2:]
        avg_relevance = sum(
            self._calculate_relevance(msg.get("content", ""), query)
            for msg in recent_messages
        ) / len(recent_messages)
        
        # 根据相关性调整窗口
        if avg_relevance > 0.7:
            # 高相关性，需要更多上下文
            return min(base_k + 2, total_messages // 2)
        elif avg_relevance > 0.4:
            # 中等相关性，保持基础窗口
            return base_k
        else:
            # 低相关性，缩小窗口
            return max(1, base_k - 1)
    
    def analyze_context(self, messages: List[Dict], query: str) -> Dict[str, Any]:
        """分析上下文质量
        
        Args:
            messages: 消息列表
            query: 当前查询
        
        Returns:
            分析报告
        """
        if not messages:
            return {
                "total_messages": 0,
                "estimated_tokens": 0,
                "avg_relevance": 0.0,
                "suggested_window": 3,
                "needs_compression": False
            }
        
        total_messages = len(messages)
        
        # 估算 Token 数
        total_content = "\n".join(msg.get("content", "") for msg in messages)
        estimated_tokens = self._estimate_tokens(total_content)
        
        # 计算平均相关性
        if query:
            avg_relevance = sum(
                self._calculate_relevance(msg.get("content", ""), query)
                for msg in messages
            ) / total_messages
        else:
            avg_relevance = 0.0
        
        # 建议窗口大小
        suggested_window = self.dynamic_window(messages, query)
        
        # 是否需要压缩
        needs_compression = estimated_tokens > config.MEMORY_WINDOW_K * 500  # 粗略判断
        
        return {
            "total_messages": total_messages,
            "estimated_tokens": estimated_tokens,
            "avg_relevance": avg_relevance,
            "suggested_window": suggested_window,
            "needs_compression": needs_compression
        }


# 单例实例
_compressor_instance: Optional[ContextCompressor] = None

def get_compressor() -> ContextCompressor:
    """获取上下文压缩器（单例）"""
    global _compressor_instance
    if _compressor_instance is None:
        _compressor_instance = ContextCompressor()
    return _compressor_instance