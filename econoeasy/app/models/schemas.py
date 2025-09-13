from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# 요약 관련 스키마
class ArticleInput(BaseModel):
    """기사 입력 스키마"""
    title: str
    content: str

class SummaryOutput(BaseModel):
    """요약 출력 스키마"""
    easy: str
    medium: str
    advanced: str

# YouTube 추천 관련 스키마
class RecommendationRequest(BaseModel):
    """YouTube 추천 요청 스키마"""
    keyword: str
    top_n: int = 3

class VideoMetrics(BaseModel):
    """영상 메트릭스 스키마"""
    view_count: str
    like_count: str
    comment_count: int
    positive_ratio: float

class VideoRecommendation(BaseModel):
    """영상 추천 결과 스키마"""
    rank: int
    title: str
    video_id: str
    channel: str
    recommendation_score: float
    quality_score: float
    sentiment_score: float
    relevance_score: float
    metrics: VideoMetrics

class RecommendationResponse(BaseModel):
    """YouTube 추천 응답 스키마"""
    status: str
    total_analyzed: int
    recommendations: List[VideoRecommendation]

# 공통 응답 스키마
class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    error: str
    detail: Optional[str] = None
