from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    session_id: str


class UploadResponse(BaseModel):
    filename: str
    chunks: int
    char_count: int
    status: str  # "success" | "warning" | "error"
    message: str
    session_id: str = "default"


class SummaryRequest(BaseModel):
    filename: str


class SummaryResponse(BaseModel):
    summary: str
    filename: str


class CodeCompletionRequest(BaseModel):
    code: str
    language: str
    line: int
    column: int


class CodeCompletionItem(BaseModel):
    label: str
    kind: str
    documentation: Optional[str] = None
    insertText: str


class CodeCompletionResponse(BaseModel):
    completions: list[CodeCompletionItem]
