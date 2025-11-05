from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Enum 타입 정의
class SummaryLevel(str, Enum):
    """요약 난이도 레벨"""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    ADVANCED = "ADVANCED"

class Category(str, Enum):
    """기사 카테고리"""
    ECONOMY = "ECONOMY"
    FINANCE = "FINANCE"
    BUSINESS = "BUSINESS"
    TECHNOLOGY = "TECHNOLOGY"
    GENERAL = "GENERAL"

# MongoDB 관련 스키마
class ArticleDocument(BaseModel):
    """MongoDB에 저장된 기사 문서 스키마"""
    id: Optional[str] = Field(None, alias="_id")
    title: str
    content: str
    publishedAt: str
    url: str
    summary_status: str = "BEFORE_ENQUEUED"

    class Config:
        populate_by_name = True

class RedisStreamMessage(BaseModel):
    """Redis Stream 메시지 스키마 (Article Summarize용)"""
    articleId: str
    timestamp: str

class KeywordRecommendStreamMessage(BaseModel):
    """Redis Stream 메시지 스키마 (YouTube Recommend 요청)"""
    keywordId: str
    keywordName: str
    timestamp: str

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

class SummarizedArticle(BaseModel):
    """MongoDB summarized_articles 컬렉션 스키마"""
    id: Optional[str] = Field(None, alias="_id")
    originalArticleId: str
    title: str
    category: Category = Category.GENERAL
    summarizedContent: str
    summaryLevel: SummaryLevel
    summarizedAt: datetime
    publishedAt: Optional[str] = None

    class Config:
        populate_by_name = True
        use_enum_values = True

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
    relevance_score: float
    educational_value: float
    content_accuracy: float
    analysis_summary: str
    trust_comment: str
    metrics: VideoMetrics

class RecommendationResponse(BaseModel):
    """YouTube 추천 응답 스키마"""
    status: str
    total_analyzed: int
    recommendations: List[VideoRecommendation]

# YouTube 추천 결과 스트림 스키마 (Java로 전송)
class YoutubeVideo(BaseModel):
    """YouTube 영상 정보 (Java 전송용)"""
    videoId: str
    title: str
    channel: str
    recommendationScore: float
    qualityScore: float
    relevanceScore: float
    educationalValue: float
    contentAccuracy: float
    analysisSummary: str
    trustComment: str
    viewCount: str
    likeCount: str
    commentCount: int

    @classmethod
    def from_recommendation(cls, rec: VideoRecommendation):
        """VideoRecommendation을 YoutubeVideo로 변환"""
        return cls(
            videoId=rec.video_id,
            title=rec.title,
            channel=rec.channel,
            recommendationScore=rec.recommendation_score,
            qualityScore=rec.quality_score,
            relevanceScore=rec.relevance_score,
            educationalValue=rec.educational_value,
            contentAccuracy=rec.content_accuracy,
            analysisSummary=rec.analysis_summary,
            trustComment=rec.trust_comment,
            viewCount=rec.metrics.view_count,
            likeCount=rec.metrics.like_count,
            commentCount=rec.metrics.comment_count
        )

class YoutubeRecommendResultStreamMessage(BaseModel):
    """Redis Stream 메시지 스키마 (YouTube Recommend 결과)"""
    keywordId: str
    videos: List[YoutubeVideo]

# 공통 응답 스키마
class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    error: str
    detail: Optional[str] = None
