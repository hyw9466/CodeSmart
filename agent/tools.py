"""Agent 工具定义：文档问答 Tool、文档总结 Tool、代码安全分析 Tool。"""

from __future__ import annotations

from langchain_core.tools import tool

from chains.rag_chain import build_rag_chain
from chains.summary_chain import summarize_text
from vectorstore.store import has_index


@tool
def document_qa(query: str) -> str:
    """基于已上传的文档进行知识问答。当用户提出与文档内容相关的问题时使用此工具。
    输入应该是用户的具体问题。"""
    if not has_index():
        return "向量库为空，请先上传文档后再提问。"
    chain = build_rag_chain()
    return chain.invoke(query)


@tool
def document_summary(text: str) -> str:
    """对给定的文本内容进行总结摘要。当用户要求总结、概括文档内容时使用此工具。
    输入应该是需要总结的文本内容。"""
    return summarize_text(text)


@tool
def code_security_analysis(code: str, language: str = "python") -> str:
    """分析代码中的安全漏洞。当用户需要检查代码安全性、发现潜在安全问题时使用此工具。
    
    参数：
    - code: 需要分析的代码文本
    - language: 代码语言（默认 python）
    
    检测范围：
    - SQL 注入、XSS 攻击、敏感信息泄露
    - 硬编码密钥/密码、命令注入
    - 路径遍历、认证绕过、CSRF
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from models.llm import get_llm
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一位资深的代码安全分析师。请分析以下代码中的安全漏洞。\n"
                   "检测范围：SQL注入、XSS攻击、敏感信息泄露、硬编码密钥、命令注入、路径遍历、认证绕过。\n"
                   "对于每个发现的问题，请给出：问题描述、风险等级（高/中/低）、修复建议。\n"
                   "语言: {language}"),
        ("user", "请分析以下代码的安全性：\n```\n{code}\n```")
    ])
    
    llm = get_llm(temperature=0)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"code": code, "language": language})


@tool
def code_optimization(code: str, language: str = "python") -> str:
    """分析代码并给出优化建议。当用户需要改进代码质量、性能或可读性时使用此工具。
    
    参数：
    - code: 需要优化的代码文本
    - language: 代码语言（默认 python）
    
    优化方向：
    - 代码可读性（命名、注释）
    - 性能优化（算法复杂度、内存使用）
    - 代码规范（PEP8、设计模式）
    - 架构改进（模块化、解耦）
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from models.llm import get_llm
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一位资深的软件架构师。请分析以下代码并给出优化建议。\n"
                   "从以下维度分析：\n"
                   "1. 代码可读性（命名规范、注释完善度）\n"
                   "2. 性能优化（算法复杂度、内存使用、重复计算）\n"
                   "3. 代码规范（PEP8 标准、设计模式应用）\n"
                   "4. 架构改进（模块化、解耦、可维护性）\n"
                   "给出具体的优化建议和改进后的代码示例。\n"
                   "语言: {language}"),
        ("user", "请优化以下代码：\n```\n{code}\n```")
    ])
    
    llm = get_llm(temperature=0.3)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"code": code, "language": language})


@tool
def error_log_analysis(log_text: str) -> str:
    """分析错误日志，定位问题原因并给出修复建议。当用户遇到程序错误、崩溃时使用此工具。
    
    参数：
    - log_text: 错误日志文本
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from models.llm import get_llm
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一位资深的运维工程师和调试专家。请分析以下错误日志，找出问题根源。\n"
                   "请输出：\n"
                   "1. 错误类型识别\n"
                   "2. 问题根因分析\n"
                   "3. 修复建议\n"
                   "4. 预防措施\n"
                   "请提供具体的代码修复示例。"),
        ("user", "请分析以下错误日志：\n```\n{log_text}\n```")
    ])
    
    llm = get_llm(temperature=0)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"log_text": log_text})


def get_all_tools() -> list:
    """返回所有可用的 Agent 工具列表。"""
    return [document_qa, document_summary, code_security_analysis, code_optimization, error_log_analysis]
