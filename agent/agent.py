"""Agent 核心：组装 LLM + Tools + Memory，根据用户意图自动路由。

对话历史通过 FileChatMessageHistory 持久化到本地文件，
每个 session_id 对应一个 JSON 文件，重启服务后记忆不丢失。
传入 Agent 时只取最近 K 轮作为上下文窗口。
"""

from __future__ import annotations

import os
from typing import AsyncIterator

from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from models.llm import get_llm
from agent.tools import get_all_tools
from expert.profile import load_profile
import config

_TOOL_INSTRUCTIONS = """

## 🛠️ 可用工具

| 工具名称 | 使用场景 |
|---------|---------|
| document_qa | 当需要查阅知识库或用户上传的文档内容时 |
| document_summary | 当用户明确要求总结、概括文本内容时 |
| code_security_analysis | 当用户需要分析代码安全性、检测漏洞时 |
| code_optimization | 当用户需要优化代码质量、性能或可读性时 |
| error_log_analysis | 当用户需要分析错误日志、定位问题原因时 |

## 🤔 工具调用决策指南

**✅ 直接回答（不需要工具）**：
- 简单问候或闲聊（如"你好"、"今天天气"）
- 一般性知识问答（如"什么是 Python"、"解释什么是 REST API"）
- 概念解释（如"什么是 SQL 注入"、"什么是异步编程"）
- 不需要外部知识的问题
- 简短的技术问题（如"Python 中如何读取文件"）

**🔧 调用工具**：
- **code_security_analysis**：用户说"分析这段代码的安全性"、"检查漏洞"、"安全审计"
- **code_optimization**：用户说"优化这段代码"、"改进性能"、"代码重构建议"
- **document_qa**：用户上传文档后提问"文档中提到了什么"、"根据文档回答..."
- **document_summary**：用户说"总结这段文本"、"概括内容"
- **error_log_analysis**：用户粘贴错误日志，说"帮我看看这个错误"、"分析日志"

**💡 思考过程**：
1. 先理解用户的核心需求
2. 判断是否需要外部工具获取信息
3. 如果需要，选择最合适的工具
4. 如果不确定，尝试直接回答（保守策略）"""


def _get_system_prompt() -> str:
    """从专家配置加载 system prompt。"""
    profile = load_profile()
    return profile.persona + _TOOL_INSTRUCTIONS


def _get_history(session_id: str) -> FileChatMessageHistory:
    """获取指定会话的持久化历史记录。"""
    file_path = os.path.join(config.CHAT_HISTORY_DIR, f"{session_id}.json")
    return FileChatMessageHistory(file_path=file_path)


def _get_recent_messages(history: FileChatMessageHistory, k: int) -> list:
    """从完整历史中取最近 k 轮对话作为上下文窗口。"""
    all_msgs = history.messages
    # 每轮 = 1 human + 1 ai = 2 条消息
    window = k * 2
    if len(all_msgs) <= window:
        return list(all_msgs)
    return list(all_msgs[-window:])


def _build_agent():
    """构建 ReAct Agent 实例。"""
    llm = get_llm(temperature=0.3)
    tools = get_all_tools()
    return create_react_agent(llm, tools, prompt=_get_system_prompt())


# 简单对话模式：快速响应问候语和简单问题
_SIMPLE_GREETINGS = {
    '你好', '您好', 'hello', 'hi', 'hey', '嗨', '哈喽',
    '早上好', '下午好', '晚上好', '晚安',
    '再见', '拜拜', 'bye', 'see you',
    '谢谢', '感谢', 'thank you', 'thanks',
}

_SIMPLE_QUESTIONS = {
    '你是谁', '你叫什么名字', '你是什么', '你能做什么',
    '你好吗', '最近怎么样', '你还好吗',
}


def _is_simple_message(query: str) -> bool:
    """判断是否是简单对话（问候语或简单问题）。"""
    query_lower = query.strip().lower()
    
    # 检查问候语
    for greeting in _SIMPLE_GREETINGS:
        if greeting in query_lower:
            return True
    
    # 检查简单问题
    for question in _SIMPLE_QUESTIONS:
        if question in query_lower:
            return True
    
    # 非常短的消息（少于10个字符）通常是简单对话
    if len(query.strip()) < 10:
        return True
    
    return False


def _get_simple_response(query: str) -> str:
    """为简单对话提供快速响应。"""
    query_lower = query.strip().lower()
    
    if any(g in query_lower for g in ['你好', 'hello', 'hi', '嗨', '哈喽']):
        return '你好！我是代码分析助手，很高兴为你服务。有什么可以帮你的吗？'
    
    if any(g in query_lower for g in ['早上好', '下午好', '晚上好']):
        return '你好！祝你今天愉快！'
    
    if any(g in query_lower for g in ['晚安', 'good night']):
        return '晚安！好好休息，明天见！'
    
    if any(g in query_lower for g in ['再见', '拜拜', 'bye']):
        return '再见！期待下次为你服务！'
    
    if any(g in query_lower for g in ['谢谢', '感谢', 'thank you']):
        return '不客气！能帮到你我很开心！'
    
    if any(g in query_lower for g in ['你是谁', '你叫什么名字']):
        return '我是代码分析助手，一个基于大语言模型的智能助手。我可以帮你分析代码安全性、优化代码、分析错误日志等。'
    
    if any(g in query_lower for g in ['你能做什么', '你有什么功能']):
        return '我可以：\n\n1. 🔍 代码安全分析\n2. ⚡ 代码优化建议\n3. 📝 文档问答\n4. 📊 文档总结\n5. 🐛 错误日志分析\n\n请上传代码或文档开始使用！'
    
    return ''


def run_agent(query: str, session_id: str = "default") -> str:
    """同步执行 Agent，返回完整回答。"""
    # 快速路径：简单对话直接响应
    if _is_simple_message(query):
        simple_response = _get_simple_response(query)
        if simple_response:
            history = _get_history(session_id)
            history.add_user_message(query)
            history.add_ai_message(simple_response)
            return simple_response
    
    # 正常路径：使用 ReAct Agent
    agent = _build_agent()
    history = _get_history(session_id)
    recent = _get_recent_messages(history, config.MEMORY_WINDOW_K)
    messages = recent + [HumanMessage(content=query)]

    result = agent.invoke({"messages": messages})

    # 提取最终回复
    answer = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            answer = msg.content
            break

    # 持久化到文件
    history.add_user_message(query)
    history.add_ai_message(answer)
    return answer


async def stream_agent(
    query: str, session_id: str = "default"
) -> AsyncIterator[dict]:
    """流式执行 Agent，逐 token 产出文本，并包含思考状态和工具调用信息。"""
    # 快速路径：简单对话直接响应（不经过 LLM）
    if _is_simple_message(query):
        simple_response = _get_simple_response(query)
        if simple_response:
            for char in simple_response:
                yield {"type": "token", "content": char}
            
            history = _get_history(session_id)
            history.add_user_message(query)
            history.add_ai_message(simple_response)
            return
    
    # 正常路径：使用 ReAct Agent
    agent = _build_agent()
    history = _get_history(session_id)
    recent = _get_recent_messages(history, config.MEMORY_WINDOW_K)
    messages = recent + [HumanMessage(content=query)]

    full_answer = ""

    async for event in agent.astream_events(
        {"messages": messages}, version="v2"
    ):
        kind = event.get("event", "")
        
        # 思考状态：agent 正在思考
        if kind == "on_agent_start":
            yield {"type": "thinking", "content": "正在分析您的问题..."}
        
        # 工具调用开始
        elif kind == "on_tool_start":
            tool_name = event.get("name", "")
            tool_input = event.get("data", {}).get("input", {})
            yield {
                "type": "tool_call",
                "name": tool_name,
                "input": tool_input,
                "content": f"🔧 正在调用工具：{tool_name}"
            }
        
        # 工具调用结束
        elif kind == "on_tool_end":
            tool_name = event.get("name", "")
            tool_result = event.get("data", {}).get("output", "")
            yield {
                "type": "tool_result",
                "name": tool_name,
                "content": f"✅ 工具调用完成：{tool_name}"
            }
        
        # LLM 流式输出
        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                if not getattr(chunk, "tool_calls", None) and not getattr(
                    chunk, "tool_call_chunks", None
                ):
                    full_answer += chunk.content
                    yield {"type": "token", "content": chunk.content}

    # 流结束后持久化
    history.add_user_message(query)
    history.add_ai_message(full_answer)


def get_session_history(session_id: str) -> list:
    """获取指定会话的完整历史消息（供 API 返回给前端）。"""
    history = _get_history(session_id)
    messages = []
    for msg in history.messages:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
    return messages


def list_sessions() -> list:
    """列出所有有历史记录的会话。"""
    import glob
    pattern = os.path.join(config.CHAT_HISTORY_DIR, "*.json")
    sessions = []
    for path in glob.glob(pattern):
        session_id = os.path.splitext(os.path.basename(path))[0]
        history = _get_history(session_id)
        msgs = history.messages
        # 用第一条用户消息作为标题
        title = session_id
        for msg in msgs:
            if isinstance(msg, HumanMessage):
                title = msg.content[:30] + ("..." if len(msg.content) > 30 else "")
                break
        sessions.append({"id": session_id, "title": title})
    return sessions


def add_document_to_session(filename: str, content: str, session_id: str = "default") -> None:
    """将文档内容添加到指定会话的历史记录中。"""
    history = _get_history(session_id)
    doc_message = SystemMessage(content=f"用户上传了文档: {filename}\n\n文档内容:\n{content}")
    history.add_message(doc_message)


def get_session_history(session_id: str) -> list:
    """获取指定会话的完整历史消息（供 API 返回给前端）。"""
    history = _get_history(session_id)
    messages = []
    for msg in history.messages:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, SystemMessage):
            messages.append({"role": "system", "content": msg.content})
    return messages
