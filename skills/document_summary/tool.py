"""document_summary Skill 自定义实现：使用专用摘要链。"""

from langchain_core.tools import tool

from chains.summary_chain import summarize_text


def create_tool(skill_config):
    """创建 document_summary 工具（摘要链）。"""

    @tool
    def document_summary(text: str) -> str:
        """对给定的文本内容进行总结摘要。当用户要求总结、概括文档内容时使用此工具。
        输入应该是需要总结的文本内容。"""
        return summarize_text(text)

    return document_summary