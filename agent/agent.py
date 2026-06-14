"""Agent 核心：组装 LLM + Tools + Memory，根据用户意图自动路由。

对话历史通过 FileChatMessageHistory 持久化到本地文件，
每个 session_id 对应一个 JSON 文件，重启服务后记忆不丢失。

支持长期记忆和智能上下文压缩：
- 长期记忆：存储用户偏好、关键知识点
- 上下文压缩：根据查询动态选择相关历史
- 会话总结：自动生成会话摘要
"""

from __future__ import annotations

import os
from typing import AsyncIterator, Optional

from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from models.llm import get_llm
from agent.tools import get_all_tools
from agent.long_term_memory import get_memory_manager
from agent.session_summarizer import get_summarizer
from agent.context_compressor import get_compressor
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


def _get_system_prompt(user_id: str = "default") -> str:
    """从专家配置加载 system prompt，并注入用户长期记忆。"""
    profile = load_profile()
    
    # 获取用户长期记忆
    try:
        memory_manager = get_memory_manager(user_id)
        relevant_memories = memory_manager.retrieve(
            "用户偏好和已知信息", 
            k=config.MEMORY_RETRIEVE_K
        )
        
        if relevant_memories:
            memory_text = "\n\n## 📚 用户记忆\n"
            for mem in relevant_memories:
                memory_text += f"- {mem['content']}\n"
        else:
            memory_text = ""
    except Exception:
        memory_text = ""
    
    return profile.persona + memory_text + _TOOL_INSTRUCTIONS


def _get_history(session_id: str, user_id: str = "default") -> FileChatMessageHistory:
    """获取指定会话的持久化历史记录。
    
    Args:
        session_id: 会话ID
        user_id: 用户ID，用于隔离不同用户的历史记录
    """
    config.ensure_user_dirs(user_id)
    user_chat_dir = config.get_user_chat_history_dir(user_id)
    file_path = os.path.join(user_chat_dir, f"{session_id}.json")
    return FileChatMessageHistory(file_path=file_path)


def _get_compressed_messages(history: FileChatMessageHistory, query: str, 
                            user_id: str) -> list:
    """获取压缩后的上下文消息，使用智能压缩算法。
    
    Args:
        history: 完整对话历史
        query: 当前查询
        user_id: 用户ID
    
    Returns:
        压缩后的消息列表（HumanMessage/AIMessage 对象）
    """
    # 获取所有消息
    all_messages = history.messages
    if not all_messages:
        return []
    
    # 转换为字典格式供压缩器使用
    dict_messages = []
    for msg in all_messages:
        if isinstance(msg, HumanMessage):
            dict_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            dict_messages.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, SystemMessage):
            dict_messages.append({"role": "system", "content": msg.content})
    
    # 使用智能压缩
    compressor = get_compressor()
    
    # 分析上下文并决定压缩策略
    analysis = compressor.analyze_context(dict_messages, query)
    
    if analysis["needs_compression"]:
        # 需要压缩，使用智能选择
        compressed = compressor.compress(dict_messages, query)
    else:
        # 使用动态窗口
        k = compressor.dynamic_window(dict_messages, query, base_k=config.MEMORY_WINDOW_K)
        compressed = dict_messages[-k * 2:] if len(dict_messages) > k * 2 else dict_messages
    
    # 转换回 Message 对象
    result = []
    for msg in compressed:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
        elif role == "system":
            result.append(SystemMessage(content=content))
    
    return result


def _build_agent(user_id: str = "default"):
    """构建 ReAct Agent 实例，包含用户记忆。"""
    llm = get_llm(temperature=0.3)
    tools = get_all_tools()
    return create_react_agent(llm, tools, prompt=_get_system_prompt(user_id))


# 简单对话模式：快速响应问候语和简单问题
# 简单问候语列表
_SIMPLE_GREETINGS = {
    # 基础问候
    '你好', '您好', 'hello', 'hi', 'hey', '嗨', '哈喽', 'hi there',
    '你好呀', '你好哦', '嗨喽', '嗨嗨',
    
    # 时间段问候
    '早上好', '上午好', '下午好', '晚上好', '晚安', '早安', '午安',
    'good morning', 'good afternoon', 'good evening', 'good night',
    
    # 告别
    '再见', '拜拜', 'bye', 'see you', 'see you later', '下次见',
    '拜拜了', '再见啦', '回头见', '明天见',
    
    # 感谢
    '谢谢', '感谢', 'thank you', 'thanks', '太感谢了', '谢谢你',
    '多谢', '非常感谢', '辛苦了', '麻烦你了',
}

_SIMPLE_QUESTIONS = {
    # 身份相关
    '你是谁', '你叫什么名字', '你是什么', '你是什么东西',
    '你的名字是什么', '你来自哪里', '你是哪个公司的',
    
    # 能力相关
    '你能做什么', '你有什么功能', '你会什么', '你擅长什么',
    '你能帮我做什么', '你有什么用', '你的作用是什么',
    
    # 状态相关
    '你好吗', '最近怎么样', '你还好吗', '你今天心情怎么样',
    '你累吗', '你忙吗', '你休息了吗',
    
    # 时间日期
    '现在几点了', '今天几号', '今天星期几', '现在是什么时间',
    
    # 确认性问题
    '在吗', '有人吗', '你在吗', '你在不在',
}


def _is_simple_message(query: str) -> bool:
    """判断是否是简单对话（问候语或简单问题）。"""
    query_lower = query.strip().lower()
    
    for greeting in _SIMPLE_GREETINGS:
        if greeting in query_lower:
            return True
    
    for question in _SIMPLE_QUESTIONS:
        if question in query_lower:
            return True
    
    if len(query.strip()) < 10:
        return True
    
    return False


def _get_simple_response(query: str) -> str:
    """为简单对话提供快速响应。"""
    query_lower = query.strip().lower()
    
    # 基础问候
    if any(g in query_lower for g in ['你好', 'hello', 'hi', 'hey', '嗨', '哈喽', 'hi there', '你好呀', '你好哦', '嗨喽']):
        return '你好！我是代码分析助手，很高兴为你服务。有什么可以帮你的吗？'
    
    # 时间段问候
    if any(g in query_lower for g in ['早上好', '上午好', 'good morning']):
        return '早上好！祝你今天工作顺利！'
    if any(g in query_lower for g in ['下午好', 'good afternoon']):
        return '下午好！需要我帮你分析代码吗？'
    if any(g in query_lower for g in ['晚上好', 'good evening']):
        return '晚上好！辛苦了一天，需要帮助吗？'
    if any(g in query_lower for g in ['晚安', 'good night']):
        return '晚安！好好休息，明天见！'
    if any(g in query_lower for g in ['早安']):
        return '早安！新的一天开始了，加油！'
    if any(g in query_lower for g in ['午安']):
        return '午安！记得休息一下哦！'
    
    # 告别
    if any(g in query_lower for g in ['再见', '拜拜', 'bye', 'see you', '下次见', '回头见', '明天见', '拜拜了', '再见啦']):
        return '再见！期待下次为你服务！'
    
    # 感谢
    if any(g in query_lower for g in ['谢谢', '感谢', 'thank you', 'thanks', '太感谢了', '谢谢你', '多谢', '非常感谢', '辛苦了', '麻烦你了']):
        return '不客气！能帮到你我很开心！'
    
    # 身份相关
    if any(g in query_lower for g in ['你是谁', '你叫什么名字', '你是什么', '你的名字是什么', '你来自哪里', '你是哪个公司的']):
        return '我是代码分析助手，一个基于大语言模型的智能助手。我可以帮你分析代码安全性、优化代码、分析错误日志等。'
    
    # 能力相关
    if any(g in query_lower for g in ['你能做什么', '你有什么功能', '你会什么', '你擅长什么', '你能帮我做什么', '你有什么用', '你的作用是什么']):
        return '我可以：\n\n1. 🔍 代码安全分析\n2. ⚡ 代码优化建议\n3. 📝 文档问答\n4. 📊 文档总结\n5. 🐛 错误日志分析\n\n请上传代码或文档开始使用！'
    
    # 状态相关
    if any(g in query_lower for g in ['你好吗', '最近怎么样', '你还好吗', '你今天心情怎么样', '你累吗', '你忙吗', '你休息了吗']):
        return '我很好，谢谢你的关心！我随时准备为你提供帮助！'
    
    # 时间日期
    if any(g in query_lower for g in ['现在几点了', '现在是什么时间']):
        from datetime import datetime
        now = datetime.now()
        return f'现在是 {now.strftime("%Y年%m月%d日 %H:%M:%S")}。'
    if any(g in query_lower for g in ['今天几号', '今天日期']):
        from datetime import datetime
        now = datetime.now()
        return f'今天是 {now.strftime("%Y年%m月%d日")}。'
    if any(g in query_lower for g in ['今天星期几']):
        from datetime import datetime
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        now = datetime.now()
        return f'今天是 {weekdays[now.weekday()]}。'
    
    # 确认性问题
    if any(g in query_lower for g in ['在吗', '有人吗', '你在吗', '你在不在']):
        return '我在的！有什么可以帮你的吗？'
    
    return ''


def _update_long_term_memory(query: str, answer: str, user_id: str):
    """将对话内容添加到长期记忆（关键信息提取）。"""
    try:
        memory_manager = get_memory_manager(user_id)
        
        # 提取关键词和关键信息
        if len(query) > 20 or len(answer) > 50:
            # 添加对话摘要到长期记忆
            summary = f"对话：用户问'{query[:50]}'，回答涉及'{answer[:100]}'"
            memory_manager.add_memory(
                content=summary,
                memory_type="conversation",
                importance=3
            )
        
        # 如果回答中包含重要信息，单独记录
        important_keywords = ['建议', '推荐', '应该', '需要', '必须', '最佳']
        for keyword in important_keywords:
            if keyword in answer:
                memory_manager.add_memory(
                    content=f"重要建议：{answer[:150]}",
                    memory_type="advice",
                    importance=7
                )
                break
    
    except Exception as e:
        # 记忆更新失败不影响主流程
        pass


def _should_summarize_session(session_id: str, user_id: str) -> bool:
    """判断是否需要总结会话。"""
    summarizer = get_summarizer()
    return summarizer.should_summarize(session_id, user_id, min_messages=5)


def _summarize_and_store(session_id: str, user_id: str):
    """总结会话并存储到长期记忆。"""
    try:
        summarizer = get_summarizer()
        memory_manager = get_memory_manager(user_id)
        
        summary = summarizer.summarize_session(session_id, user_id)
        
        # 将总结存储到长期记忆
        if summary.get("summary"):
            memory_manager.add_memory(
                content=f"会话总结：{summary['topic']} - {summary['summary']}",
                memory_type="summary",
                importance=6
            )
        
        # 存储关键知识点
        for point in summary.get("key_points", []):
            memory_manager.add_memory(
                content=f"知识点：{point}",
                memory_type="fact",
                importance=5
            )
        
        # 存储用户偏好
        for pref in summary.get("user_preferences", []):
            memory_manager.add_memory(
                content=f"用户偏好：{pref}",
                memory_type="preference",
                importance=8
            )
        
        return summary
    
    except Exception:
        return None


def run_agent(query: str, session_id: str = "default", user_id: str = "default") -> str:
    """同步执行 Agent，返回完整回答。
    
    Args:
        query: 用户查询
        session_id: 会话ID
        user_id: 用户ID，用于隔离不同用户的数据
    """
    # 快速路径：简单对话直接响应
    if _is_simple_message(query):
        simple_response = _get_simple_response(query)
        if simple_response:
            history = _get_history(session_id, user_id)
            history.add_user_message(query)
            history.add_ai_message(simple_response)
            
            # 更新长期记忆
            _update_long_term_memory(query, simple_response, user_id)
            
            return simple_response
    
    # 正常路径：使用 ReAct Agent
    agent = _build_agent(user_id)
    history = _get_history(session_id, user_id)
    
    # 使用智能压缩获取上下文
    recent = _get_compressed_messages(history, query, user_id)
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
    
    # 更新长期记忆
    _update_long_term_memory(query, answer, user_id)
    
    # 检查是否需要总结会话
    if _should_summarize_session(session_id, user_id):
        _summarize_and_store(session_id, user_id)
    
    return answer


async def stream_agent(
    query: str, session_id: str = "default", user_id: str = "default"
) -> AsyncIterator[dict]:
    """流式执行 Agent，逐 token 产出文本，并包含思考状态和工具调用信息。
    
    Args:
        query: 用户查询
        session_id: 会话ID
        user_id: 用户ID，用于隔离不同用户的数据
    """
    # 快速路径：简单对话直接响应（不经过 LLM）
    if _is_simple_message(query):
        simple_response = _get_simple_response(query)
        if simple_response:
            for char in simple_response:
                yield {"type": "token", "content": char}
            
            history = _get_history(session_id, user_id)
            history.add_user_message(query)
            history.add_ai_message(simple_response)
            
            _update_long_term_memory(query, simple_response, user_id)
            return
    
    # 正常路径：使用 ReAct Agent
    agent = _build_agent(user_id)
    history = _get_history(session_id, user_id)
    
    # 使用智能压缩获取上下文
    recent = _get_compressed_messages(history, query, user_id)
    messages = recent + [HumanMessage(content=query)]

    full_answer = ""

    async for event in agent.astream_events(
        {"messages": messages}, version="v2"
    ):
        kind = event.get("event", "")
        
        if kind == "on_agent_start":
            yield {"type": "thinking", "content": "正在分析您的问题..."}
        
        elif kind == "on_tool_start":
            tool_name = event.get("name", "")
            tool_input = event.get("data", {}).get("input", {})
            yield {
                "type": "tool_call",
                "name": tool_name,
                "input": tool_input,
                "content": f"🔧 正在调用工具：{tool_name}"
            }
        
        elif kind == "on_tool_end":
            tool_name = event.get("name", "")
            tool_result = event.get("data", {}).get("output", "")
            yield {
                "type": "tool_result",
                "name": tool_name,
                "content": f"✅ 工具调用完成：{tool_name}"
            }
        
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
    
    # 更新长期记忆
    _update_long_term_memory(query, full_answer, user_id)
    
    # 检查是否需要总结会话
    if _should_summarize_session(session_id, user_id):
        _summarize_and_store(session_id, user_id)


def get_session_history(session_id: str, user_id: str = "default") -> list:
    """获取指定会话的完整历史消息（供 API 返回给前端）。"""
    history = _get_history(session_id, user_id)
    messages = []
    for msg in history.messages:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, SystemMessage):
            messages.append({"role": "system", "content": msg.content})
    return messages


def list_sessions(user_id: str = "default") -> list:
    """列出用户的所有会话。"""
    import glob
    user_chat_dir = config.get_user_chat_history_dir(user_id)
    pattern = os.path.join(user_chat_dir, "*.json")
    sessions = []
    for path in glob.glob(pattern):
        session_id = os.path.splitext(os.path.basename(path))[0]
        history = _get_history(session_id, user_id)
        msgs = history.messages
        title = session_id
        for msg in msgs:
            if isinstance(msg, HumanMessage):
                title = msg.content[:30] + ("..." if len(msg.content) > 30 else "")
                break
        sessions.append({"id": session_id, "title": title})
    return sessions


def add_document_to_session(filename: str, content: str, session_id: str = "default", 
                           user_id: str = "default") -> None:
    """将文档内容添加到指定会话的历史记录中。"""
    history = _get_history(session_id, user_id)
    doc_message = SystemMessage(content=f"用户上传了文档: {filename}\n\n文档内容:\n{content}")
    history.add_message(doc_message)


# 导出新功能
def summarize_session(session_id: str, user_id: str = "default") -> dict:
    """总结指定会话并返回总结结果。"""
    summarizer = get_summarizer()
    return summarizer.summarize_session(session_id, user_id)


def get_memory_stats(user_id: str = "default") -> dict:
    """获取用户记忆统计信息。"""
    memory_manager = get_memory_manager(user_id)
    return memory_manager.get_stats()


def retrieve_memories(query: str, user_id: str = "default", k: int = 3) -> list:
    """检索用户相关记忆。"""
    memory_manager = get_memory_manager(user_id)
    return memory_manager.retrieve(query, k=k)