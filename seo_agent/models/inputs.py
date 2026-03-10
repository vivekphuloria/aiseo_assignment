from typing import Optional
from pydantic import BaseModel, Field


class JobRequest(BaseModel):
    topic: str = Field(..., description="Topic or keyword to generate an article for")
    target_word_count: int = Field(1500, ge=500, le=5000)
    language: str = Field("en", description="ISO 639-1 language code")
    use_mock: bool = Field(False, description="Use mock SERP data instead of real SerpAPI call")


class JobResponse(BaseModel):
    thread_id: str
    status: str


class JobStatusResponse(BaseModel):
    thread_id: str
    status: str
    execution_stage: Optional[str] = None
    topic: Optional[str] = None
    created_at: str
    updated_at: str
    error_message: Optional[str] = None
    result_preview: Optional[str] = None
