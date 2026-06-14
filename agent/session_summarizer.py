"""会话总结器：自动对对话历史进行摘要，生成关键知识点。

支持：
- 实时会话总结
- 多轮对话压缩
- 关键信息提取
- 话题追踪
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import HumanMessage, AIMessage

from models.llm import get_llm


class SessionSummarizer:
    """会话总结器"""
    
    def __init__(self):
        self.llm = get_llm(temperature=0.1)
    
    def _build_summary_prompt(self) -> ChatPromptTemplate:
        """构建总结提示词"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的对话总结助手。请分析以下对话历史，
生成一份简明扼要的总结报告。

总结要求：
1. 识别对话主题和关键问题
2. 提取重要的结论和决策
3. 记录用户提到的偏好或需求
4. 识别未解决的问题或待办事项
5. 保持简洁，不超过300字

输出格式：
```json
{
  "topic": "对话主题",
  "summary": "简要总结",
  "key_points": ["关键点1", "关键点2", "..."],
  "user_preferences": ["偏好1", "偏好2", "..."],
  "action_items": ["待办1", "待办2", "..."]
}
```"""),
            ("user", "请总结以下对话：\n{conversation}")
        ])
    
    def _build_compression_prompt(self) -> ChatPromptTemplate:
        """构建上下文压缩提示词"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是一位智能上下文压缩专家。请分析以下对话历史，
生成一个紧凑但信息完整的版本，用于作为后续对话的上下文。

压缩规则：
1. 保留关键问题和答案
2. 删除重复内容和闲聊
3. 合并相关的对话片段
4. 保持逻辑连贯性
5. 控制在约2000字符以内

输出格式：直接输出压缩后的对话文本，不需要任何格式标记。"""),
            ("user", "请压缩以下对话上下文：\n{conversation}")
        ])
    
    def _build_topic_prompt(self) -> ChatPromptTemplate:
        """构建话题提取提示词"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是一位话题分析专家。请分析对话历史，识别主要讨论的话题。

输出格式：
```json
{
  "main_topic": "主要话题",
  "sub_topics": ["子话题1", "子话题2", "..."],
  "keywords": ["关键词1", "关键词2", "..."]
}
```"""),
            ("user", "请分析以下对话的话题：\n{conversation}")
        ])
    
    def _format_conversation(self, messages: List[Dict]) -> str:
        """格式化对话历史为文本"""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if role == "user":
                lines.append(f"用户：{content}")
            elif role == "assistant":
                lines.append(f"助手：{content}")
            elif role == "system":
                lines.append(f"系统：{content}")
            else:
                lines.append(f"{role}：{content}")
        
        return "\n".join(lines)
    
    def summarize_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """总结指定会话
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
        
        Returns:
            总结结果（包含主题、摘要、关键点等）
        """
        # 获取对话历史
        from agent.agent import get_session_history
        messages = get_session_history(session_id, user_id)
        
        if not messages:
            return {
                "topic": "空对话",
                "summary": "暂无对话内容",
                "key_points": [],
                "user_preferences": [],
                "action_items": []
            }
        
        # 格式化对话
        conversation = self._format_conversation(messages)
        
        # 构建并执行总结链
        prompt = self._build_summary_prompt()
        parser = JsonOutputParser()
        
        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({"conversation": conversation})
            return result
        except Exception as e:
            # 如果JSON解析失败，返回简单总结
            fallback_prompt = ChatPromptTemplate.from_messages([
                ("system", "请用一句话总结以下对话内容。"),
                ("user", conversation)
            ])
            simple_summary = (fallback_prompt | self.llm | StrOutputParser()).invoke({})
            
            return {
                "topic": "未知",
                "summary": simple_summary,
                "key_points": [],
                "user_preferences": [],
                "action_items": []
            }
    
    def compress_context(self, session_id: str, user_id: str, 
                        max_length: int = 2000) -> str:
        """压缩对话上下文，保持关键信息
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            max_length: 最大长度
        
        Returns:
            压缩后的上下文文本
        """
        from agent.agent import get_session_history
        messages = get_session_history(session_id, user_id)
        
        if not messages:
            return ""
        
        conversation = self._format_conversation(messages)
        
        # 如果已经很短，直接返回
        if len(conversation) <= max_length:
            return conversation
        
        # 执行压缩
        prompt = self._build_compression_prompt()
        chain = prompt | self.llm | StrOutputParser()
        
        compressed = chain.invoke({"conversation": conversation})
        
        # 如果压缩后仍然过长，截断
        if len(compressed) > max_length:
            compressed = compressed[:max_length - 3] + "..."
        
        return compressed
    
    def extract_topics(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """提取对话话题和关键词
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
        
        Returns:
            话题分析结果
        """
        from agent.agent import get_session_history
        messages = get_session_history(session_id, user_id)
        
        if not messages:
            return {
                "main_topic": "未知",
                "sub_topics": [],
                "keywords": []
            }
        
        conversation = self._format_conversation(messages)
        
        prompt = self._build_topic_prompt()
        parser = JsonOutputParser()
        
        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({"conversation": conversation})
            return result
        except Exception:
            # 返回简单结果
            return {
                "main_topic": "对话内容分析",
                "sub_topics": [],
                "keywords": []
            }
    
    def should_summarize(self, session_id: str, user_id: str, 
                        min_messages: int = None) -> bool:
        """判断是否需要总结（基于消息数量）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            min_messages: 最少消息数，默认使用 config.MEMORY_SUMMARY_THRESHOLD
        """
        if min_messages is None:
            min_messages = config.MEMORY_SUMMARY_THRESHOLD
            
        from agent.agent import get_session_history
        messages = get_session_history(session_id, user_id)
        return len(messages) >= min_messages


# 单例实例
_summarizer_instance: Optional[SessionSummarizer] = None

def get_summarizer() -> SessionSummarizer:
    """获取会话总结器（单例）"""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = SessionSummarizer()
    return _summarizer_instance