from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

# Application Schemas

class Progress(BaseModel):
    """Tracks user's learning progress per verse"""
    user_id: str = Field(default="public", description="User identifier")
    chapter: int = Field(..., ge=1, le=18, description="Chapter number")
    verse_id: str = Field(..., description="Verse identifier unique within chapter")
    status: str = Field(default="learning", description="learning|mastered|review")
    score: float = Field(default=0.0, ge=0, le=100, description="Pronunciation score")

class Bookmark(BaseModel):
    """Stores user's favorite verses"""
    user_id: str = Field(default="public")
    chapter: int = Field(..., ge=1, le=18)
    verse_id: str = Field(...)
    note: Optional[str] = Field(default=None)

class PracticeItem(BaseModel):
    """Items the user added for extra pronunciation practice"""
    user_id: str = Field(default="public")
    chapter: int = Field(..., ge=1, le=18)
    verse_id: str = Field(...)
    phrase: Optional[str] = None

class ChatMessage(BaseModel):
    user_id: str = Field(default="public")
    message: str

class EvaluateRequest(BaseModel):
    target_text: str
    recognized_text: str

class EvaluateResponse(BaseModel):
    score: float
    differences: List[Dict[str, int]] = Field(
        default_factory=list,
        description="List of diff spans as {start, end} positions in target_text that mismatched"
    )

class ExportRequest(BaseModel):
    user_id: str = Field(default="public")

# Note: collection names will be the lowercase of class names above:
# progress -> "progress", bookmark -> "bookmark", practiceitem -> "practiceitem"
