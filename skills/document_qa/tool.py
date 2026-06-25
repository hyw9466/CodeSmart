"""document_qa Skill 自定义实现：使用 RAG 检索增强生成链。"""

from langchain_core.tools import tool

from chains.rag_chain import build_rag_chain
from vectorstore.store import has_index


def create_tool(skill_config):
    """创建 document_qa 工具（RAG 链）。"""

    @tool
    def document_qa(query: str) -> str:
        """基于已上传的文档进行知识问答。当用户提出与文档内容相关的问题时使用此工具。
        输入应该是用户的具体问题。"""
        if not has_index():
            return "向量库为空，请先上传文档后再提问。"
        chain = build_rag_chain()
        return chain.invoke(query)

    return document_qa