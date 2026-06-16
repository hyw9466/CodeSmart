import os
import json
import uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from fastapi.responses import StreamingResponse

import config
from api.schemas import (
    ChatRequest, ChatResponse, UploadResponse, SummaryRequest, SummaryResponse,
    CodeCompletionRequest, CodeCompletionResponse, CodeCompletionItem
)
from document.loader import load_file, split_documents, validate_and_load, SUPPORTED_EXTENSIONS
from vectorstore.store import (
    async_add_documents, has_index, delete_documents_by_source,
    list_all_documents, list_base_documents, list_user_documents
)
from vectorstore.registry import compute_hash, is_duplicate, register_file, unregister_file, list_documents
from chains.rag_chain import build_rag_chain, stream_rag_chain
from chains.summary_chain import summarize_text, stream_summarize
from chains.code_completion_chain import generate_completions
from agent.agent import run_agent, stream_agent, get_session_history, list_sessions, summarize_session, get_memory_stats, retrieve_memories

router = APIRouter()


# ── 用户ID管理 ──────────────────────────────────────────

def _get_or_create_user_id(x_user_id: Optional[str] = None) -> str:
    """获取或创建用户ID。"""
    if x_user_id:
        return x_user_id
    # 如果没有提供 user_id，生成一个临时的（基于 IP 或随机）
    return f"guest_{uuid.uuid4().hex[:8]}"


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
async def upload_document(
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """上传文档到用户知识库。支持 .md / .txt / .pdf / .docx"""
    user_id = _get_or_create_user_id(x_user_id)
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400, f"不支持的文件类型，支持 {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    content = await file.read()

    # 检查重复：同名且同内容 hash 则跳过
    content_hash = compute_hash(content)
    if is_duplicate(file.filename, content_hash, user_id):
        raise HTTPException(409, f"文件 {file.filename} 已存在且内容未变化，无需重复上传")

    # 确保用户目录存在
    config.ensure_user_dirs(user_id)
    
    # 保存文件到用户上传目录
    user_upload_dir = config.get_user_upload_dir(user_id)
    save_path = os.path.join(user_upload_dir, file.filename)
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

    # 异步并发入库（存入用户 FAISS 向量库）
    count = await async_add_documents(docs, user_id=user_id)

    # 注册文件（去重用）
    register_file(file.filename, content_hash, user_id=user_id)

    return UploadResponse(
        filename=file.filename,
        chunks=count,
        char_count=len(text.strip()),
        status="success",
        message=f"成功处理 {count} 个片段，共 {len(text.strip())} 个字符",
    )


# ── 文档管理接口 ─────────────────────────────────────────

@router.get("/documents")
async def get_documents(x_user_id: Optional[str] = Header(None, alias="X-User-ID")):
    """查看文档列表（基础知识库 + 用户知识库）。"""
    user_id = _get_or_create_user_id(x_user_id)
    docs = list_all_documents(user_id)
    return {"count": len(docs), "documents": docs, "user_id": user_id}


@router.get("/documents/base")
async def get_base_documents():
    """查看基础知识库文档列表（只读）。"""
    docs = list_base_documents()
    return {"count": len(docs), "documents": docs, "type": "base"}


@router.get("/documents/user")
async def get_user_documents(x_user_id: Optional[str] = Header(None, alias="X-User-ID")):
    """查看用户知识库文档列表。"""
    user_id = _get_or_create_user_id(x_user_id)
    docs = list_user_documents(user_id)
    return {"count": len(docs), "documents": docs, "user_id": user_id, "type": "user"}


@router.delete("/documents/{filename}")
async def delete_document(
    filename: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """删除用户知识库中的指定文档。"""
    user_id = _get_or_create_user_id(x_user_id)
    
    # 检查是否是基础文档
    base_docs = list_base_documents()
    for doc in base_docs:
        if doc["filename"] == filename:
            raise HTTPException(403, f"文档 '{filename}' 是基础知识库的一部分，不允许删除")
    
    # 从用户向量库删除
    deleted_count = await delete_documents_by_source(filename, user_id=user_id)
    if deleted_count == 0 and not unregister_file(filename, user_id=user_id):
        raise HTTPException(404, f"文档 '{filename}' 不在您的知识库中")

    # 确认删除成功后，从注册表移除
    unregister_file(filename, user_id=user_id)
    
    # 删除用户上传的文件
    user_upload_dir = config.get_user_upload_dir(user_id)
    file_path = os.path.join(user_upload_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    return {
        "message": f"成功删除文档 '{filename}'",
        "deleted_chunks": deleted_count,
    }


@router.delete("/documents")
async def delete_all_documents(x_user_id: Optional[str] = Header(None, alias="X-User-ID")):
    """清空用户知识库（不影响基础知识库）。"""
    user_id = _get_or_create_user_id(x_user_id)
    
    docs = list_user_documents(user_id)
    if not docs:
        return {"message": "您的知识库已经是空的"}

    deleted_count = 0
    failed_files = []
    for doc in docs:
        filename = doc["filename"]
        try:
            count = await delete_documents_by_source(filename, user_id=user_id)
            unregister_file(filename, user_id=user_id)
            
            # 删除用户上传的文件
            user_upload_dir = config.get_user_upload_dir(user_id)
            file_path = os.path.join(user_upload_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            deleted_count += 1
        except Exception as e:
            failed_files.append(filename)

    if failed_files:
        return {
            "message": f"部分删除失败: {', '.join(failed_files)}",
            "deleted_count": deleted_count,
        }

    return {
        "message": f"已清空您的知识库，共删除 {deleted_count} 个文档",
        "deleted_count": deleted_count,
    }


# ── 会话管理接口 ─────────────────────────────────────────

@router.get("/sessions")
async def get_sessions(x_user_id: Optional[str] = Header(None, alias="X-User-ID")):
    """获取用户的会话列表。"""
    user_id = _get_or_create_user_id(x_user_id)
    sessions = list_sessions(user_id)
    return {"sessions": sessions, "user_id": user_id}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """获取指定会话的历史消息。"""
    user_id = _get_or_create_user_id(x_user_id)
    messages = get_session_history(session_id, user_id)
    return {"session_id": session_id, "messages": messages, "user_id": user_id}


# ── 聊天接口 ──────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """RAG 问答（非流式）。"""
    user_id = req.user_id or _get_or_create_user_id()
    if not has_index(user_id):
        raise HTTPException(400, "向量库为空，请先上传文档")
    chain = build_rag_chain(user_id=user_id)
    answer = chain.invoke(req.query)
    return ChatResponse(answer=answer, session_id=req.session_id)


@router.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest):
    """Agent 智能对话（非流式）。"""
    user_id = req.user_id or _get_or_create_user_id()
    answer = run_agent(req.query, req.session_id, user_id=user_id)
    return ChatResponse(answer=answer, session_id=req.session_id)


@router.post("/summary", response_model=SummaryResponse)
async def summary(req: SummaryRequest):
    """文档总结（非流式）。"""
    user_id = req.user_id or _get_or_create_user_id()
    
    # 先在用户目录查找
    user_upload_dir = config.get_user_upload_dir(user_id)
    file_path = os.path.join(user_upload_dir, req.filename)
    
    # 如果用户目录没有，再在公共目录查找
    if not os.path.exists(file_path):
        file_path = os.path.join(config.UPLOAD_DIR, req.filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(404, f"文件 {req.filename} 不存在")
    
    text = load_file(file_path)
    result = summarize_text(text)
    return SummaryResponse(summary=result, filename=req.filename)


# ── 流式接口（SSE）────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """RAG 问答（流式 SSE）。"""
    user_id = req.user_id or _get_or_create_user_id()
    if not has_index(user_id):
        raise HTTPException(400, "向量库为空，请先上传文档")

    async def generate():
        async for token in stream_rag_chain(req.query, user_id=user_id):
            yield _sse_event(token)
        yield _sse_done()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/agent/chat/stream")
async def agent_chat_stream(req: ChatRequest):
    """Agent 智能对话（流式 SSE）。"""
    user_id = req.user_id or _get_or_create_user_id()
    
    async def generate():
        try:
            async for token in stream_agent(req.query, req.session_id, user_id=user_id):
                yield _sse_event(token)
            yield _sse_done()
        except Exception as e:
            yield _sse_event(
                {"type": "error", "content": f"处理请求时出错：{str(e)}"},
                event="error"
            )
            yield _sse_done()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/summary/stream")
async def summary_stream(req: SummaryRequest):
    """文档总结（流式 SSE）。"""
    user_id = req.user_id or _get_or_create_user_id()
    
    # 先在用户目录查找
    user_upload_dir = config.get_user_upload_dir(user_id)
    file_path = os.path.join(user_upload_dir, req.filename)
    
    # 如果用户目录没有，再在公共目录查找
    if not os.path.exists(file_path):
        file_path = os.path.join(config.UPLOAD_DIR, req.filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(404, f"文件 {req.filename} 不存在")
    
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
        completions_data = generate_completions(
            req.code,
            req.language,
            req.line,
            req.column
        )
        
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


# ── 记忆管理接口 ─────────────────────────────────────────

@router.get("/memory/stats")
async def memory_stats(x_user_id: Optional[str] = Header(None, alias="X-User-ID")):
    """获取用户记忆统计信息。"""
    user_id = _get_or_create_user_id(x_user_id)
    stats = get_memory_stats(user_id)
    return {"stats": stats, "user_id": user_id}


@router.get("/memory/retrieve")
async def memory_retrieve(
    query: str,
    k: int = 3,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """检索用户相关记忆。"""
    user_id = _get_or_create_user_id(x_user_id)
    memories = retrieve_memories(query, user_id, k=k)
    return {"memories": memories, "user_id": user_id, "query": query}


@router.post("/memory/add")
async def memory_add(
    content: str,
    memory_type: str = "general",
    importance: int = 5,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """手动添加记忆片段。"""
    user_id = _get_or_create_user_id(x_user_id)
    
    from agent.long_term_memory import get_memory_manager
    memory_manager = get_memory_manager(user_id)
    
    memory_id = memory_manager.add_memory(
        content=content,
        memory_type=memory_type,
        importance=importance
    )
    
    return {"message": "记忆添加成功", "memory_id": memory_id, "user_id": user_id}


@router.delete("/memory/{memory_id}")
async def memory_delete(
    memory_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """删除指定记忆片段。"""
    user_id = _get_or_create_user_id(x_user_id)
    
    from agent.long_term_memory import get_memory_manager
    memory_manager = get_memory_manager(user_id)
    
    success = memory_manager.delete_memory(memory_id)
    
    if success:
        return {"message": f"记忆 {memory_id} 删除成功", "user_id": user_id}
    else:
        raise HTTPException(404, f"记忆 {memory_id} 不存在")


# ── 会话总结接口 ─────────────────────────────────────────

@router.get("/sessions/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """获取指定会话的总结。"""
    user_id = _get_or_create_user_id(x_user_id)
    summary = summarize_session(session_id, user_id)
    return {"session_id": session_id, "user_id": user_id, "summary": summary}
