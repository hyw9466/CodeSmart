"""代码补全链：基于 LLM 生成代码补全建议。"""

import json
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from models.llm import get_llm

# 代码补全提示词模板
_COMPLETION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "你是一个专业的代码补全助手，擅长各种编程语言。"\
        "根据用户提供的代码上下文和光标位置，生成合理、正确的代码补全建议。"\
        "补全建议应该符合编程语言的语法规范和最佳实践。"\
        "返回的补全内容应该是完整的代码片段，而不是解释或注释。"\
        "如果有多种可能的补全，提供最常见和最有用的几种。"\
        "语言: {language}"
    ),
    (
        "user",
        "代码：\n```\n{code}\n```\n"\
        "光标位置：第 {line} 行，第 {column} 列\n"\
        "请生成代码补全建议，格式为 JSON 数组：\n"\
        "[\n"\
        "  {\n"\
        "    \"label\": \"补全项显示文本\",\n"\
        "    \"kind\": \"补全类型（如 Function、Variable、Class 等）\",\n"\
        "    \"documentation\": \"补全项的说明文档\",\n"\
        "    \"insertText\": \"要插入的代码文本\"\n"\
        "  },\n"\
        "  ...\n"\
        "]\n"\
        "只返回 JSON 内容，不要包含其他文本。"
    ),
])

def build_code_completion_chain():
    """构建代码补全链。"""
    llm = get_llm(temperature=0.3)
    return _COMPLETION_PROMPT | llm | StrOutputParser()


def generate_completions(code: str, language: str, line: int, column: int) -> List[Dict[str, Any]]:
    """生成代码补全建议。"""
    chain = build_code_completion_chain()
    result = chain.invoke({
        "code": code,
        "language": language,
        "line": line,
        "column": column
    })
    
    # 解析 JSON 结果
    try:
        completions = json.loads(result)
        # 确保返回的是列表
        if isinstance(completions, list):
            return completions
        return []
    except json.JSONDecodeError:
        # 如果解析失败，返回空列表
        return []