from typing import List, Optional
from pydantic import BaseModel, Field

class EvaluateRequest(BaseModel):
    target: str = Field(..., description="Expected text/transliteration")
    spoken: str = Field(..., description="User recognized speech text")

class DiffItem(BaseModel):
    op: str
    a: str
    b: str

class EvaluateResponse(BaseModel):
    score: float
    diffs: List[DiffItem]

class Bookmark(BaseModel):
    user_id: str
    chapter_id: int
    verse_id: int

class Progress(BaseModel):
    user_id: str
    chapter_id: int
    verse_id: int
    score: float

class PracticeItem(BaseModel):
    chapter_id: int
    verse_id: int

class ExportRequest(BaseModel):
    items: List[PracticeItem]

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
