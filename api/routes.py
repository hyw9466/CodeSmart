import os
import json

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

import config
from api.schemas import (
    ChatRequest, ChatResponse, UploadResponse, SummaryRequest, SummaryResponse,
    CodeCompletionRequest, CodeCompletionResponse, CodeCompletionItem
)
from document.loader import load_file, split_documents, validate_and_load, SUPPORTED_EXTENSIONS
from vectorstore.store import add_documents, async_add_documents, has_index, delete_documents_by_source
from vectorstore.registry import compute_hash, is_duplicate, register_file, unregister_file, list_documents
from chains.rag_chain import build_rag_chain, stream_rag_chain
from chains.summary_chain import summarize_text, stream_summarize
from chains.code_completion_chain import generate_completions
from agent.agent import run_agent, stream_agent, get_session_history, list_sessions

router = APIRouter()


# ── SSE 工具函数 ──────────────────────────────────────────

def _sse_event(data: str, event: str = "message") -> str:
    """格式化一条 SSE 事件。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_done() -> str:
    """SSE 结束标记。"""
    return "event: done\ndata: [DONE]\n\n"


# ── 基础接口 ──────────────────────────────────────────────

@router.get("/ping")
async def ping():
    return {"message": "pong"}


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """上传文档，解析分块后存入向量库（知识库模式）。支持 .md / .txt / .pdf / .docx"""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400, f"不支持的文件类型，支持 {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    content = await file.read()

    # 检查重复：同名且同内容 hash 则跳过
    content_hash = compute_hash(content)
    if is_duplicate(file.filename, content_hash):
        raise HTTPException(409, f"文件 {file.filename} 已存在且内容未变化，无需重复上传")

    # 保存文件到上传目录
    save_path = os.path.join(config.UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        f.write(content)

    # 验证并加载文档内容
    text, is_valid, validate_msg = validate_and_load(save_path)
    if not is_valid:
        return UploadResponse(
            filename=file.filename,
            chunks=0,
            char_count=0,
            status="error",
            message=validate_msg,
        )

    # 切分文档
    docs = split_documents(text, file.filename)

    # 异步并发入库（存入 FAISS 向量库）
    count = await async_add_documents(docs)

    # 注册文件（去重用）
    register_file(file.filename, content_hash)

    return UploadResponse(
        filename=file.filename,
        chunks=count,
        char_count=len(text.strip()),
        status="success",
        message=f"成功处理 {count} 个片段，共 {len(text.strip())} 个字符",
    )


# ── 非流式接口（保持兼容）────────────────────────────────

@router.get("/documents")
async def get_documents():
    """查看已入库的文档列表。"""
    docs = list_documents()
    return {"count": len(docs), "documents": docs}


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """删除指定文档（从注册表和向量库中同时移除）。"""
    # 1. 先从向量库删除（可能失败）
    deleted_count = await delete_documents_by_source(filename)
    if deleted_count == 0 and not unregister_file(filename):
        # 文件不在注册表中，说明本来就不存在
        raise HTTPException(404, f"文档 '{filename}' 不在知识库中")

    # 2. 确认向量库删除成功后，再从注册表移除
    unregister_file(filename)

    return {
        "message": f"成功删除文档 '{filename}'",
        "deleted_chunks": deleted_count,
    }


@router.delete("/documents")
async def delete_all_documents():
    """清空整个知识库（删除所有文档）。"""
    docs = list_documents()
    if not docs:
        return {"message": "知识库已经是空的"}

    deleted_count = 0
    failed_files = []
    for doc in docs:
        filename = doc["filename"]
        try:
            count = await delete_documents_by_source(filename)
            # 只有向量库删除成功（或本来就不在向量库里）才从注册表移除
            unregister_file(filename)
            deleted_count += 1
        except Exception as e:
            failed_files.append(filename)

    if failed_files:
        return {
            "message": f"部分删除失败: {', '.join(failed_files)}",
            "deleted_count": deleted_count,
        }

    return {
        "message": f"已清空知识库，共删除 {deleted_count} 个文档",
        "deleted_count": deleted_count,
    }


@router.get("/sessions")
async def get_sessions():
    """获取所有会话列表。"""
    sessions = list_sessions()
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """获取指定会话的历史消息。"""
    messages = get_session_history(session_id)
    return {"session_id": session_id, "messages": messages}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """RAG 问答（非流式）。"""
    if not has_index():
        raise HTTPException(400, "向量库为空，请先上传文档")
    chain = build_rag_chain()
    answer = chain.invoke(req.query)
    return ChatResponse(answer=answer, session_id=req.session_id)


@router.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest):
    """Agent 智能对话（非流式）。"""
    answer = run_agent(req.query, req.session_id)
    return ChatResponse(answer=answer, session_id=req.session_id)


@router.post("/summary", response_model=SummaryResponse)
async def summary(req: SummaryRequest):
    """文档总结（非流式）。"""
    file_path = os.path.join(config.UPLOAD_DIR, req.filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, f"文件 {req.filename} 不存在，请先上传")
    text = load_file(file_path)
    result = summarize_text(text)
    return SummaryResponse(summary=result, filename=req.filename)


# ── 流式接口（SSE）────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """RAG 问答（流式 SSE）。"""
    if not has_index():
        raise HTTPException(400, "向量库为空，请先上传文档")

    async def generate():
        async for token in stream_rag_chain(req.query):
            yield _sse_event(token)
        yield _sse_done()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/agent/chat/stream")
async def agent_chat_stream(req: ChatRequest):
    """Agent 智能对话（流式 SSE）。"""
    async def generate():
        async for token in stream_agent(req.query, req.session_id):
            yield _sse_event(token)
        yield _sse_done()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/summary/stream")
async def summary_stream(req: SummaryRequest):
    """文档总结（流式 SSE）。"""
    file_path = os.path.join(config.UPLOAD_DIR, req.filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, f"文件 {req.filename} 不存在，请先上传")
    text = load_file(file_path)

    async def generate():
        async for token in stream_summarize(text):
            yield _sse_event(token)
        yield _sse_done()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/code/completion", response_model=CodeCompletionResponse)
async def code_completion(req: CodeCompletionRequest):
    """代码补全。"""
    try:
        # 生成代码补全建议
        completions_data = generate_completions(
            req.code,
            req.language,
            req.line,
            req.column
        )
        
        # 转换为响应模型
        completions = [
            CodeCompletionItem(
                label=item.get("label", ""),
                kind=item.get("kind", "Text"),
                documentation=item.get("documentation"),
                insertText=item.get("insertText", "")
            )
            for item in completions_data
        ]
        
        return CodeCompletionResponse(completions=completions)
    except Exception as e:
        raise HTTPException(500, f"代码补全失败: {str(e)}")
