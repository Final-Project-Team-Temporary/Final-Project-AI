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
    """Redis Stream 메시지 스키마"""
    articleId: str
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
    video_url: str
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

# 공통 응답 스키마
class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    error: str
    detail: Optional[str] = None

# Quiz 관련 스키마

class QuizSourceType(str, Enum):
    """퀴즈 출처 타입"""
    KEYWORD = "KEYWORD"
    ARTICLE = "ARTICLE"

class QuizItem(BaseModel):
    """단일 객관식 퀴즈 항목"""
    question: str
    options: List[str]
    answer_index: int = Field(..., ge=0)
    explanation: Optional[str] = None

class QuizResponse(BaseModel):
    """퀴즈 응답 스키마"""
    quizzes: List[QuizItem]

class QuizByKeywordRequest(BaseModel):
    """키워드 기반 퀴즈 생성/조회 요청"""
    keyword: str
    count: int = 3

class QuizByArticleRequest(BaseModel):
    """기사 ID 기반 퀴즈 생성/조회 요청"""
    article_id: str
    count: int = 3

class QuizDocument(BaseModel):
    """MongoDB quizzes 컬렉션 문서 스키마 (여러 문항을 한 문서로 저장)"""
    id: Optional[str] = Field(None, alias="_id")
    sourceType: QuizSourceType
    keyword: Optional[str] = None
    articleId: Optional[str] = None
    articleTitle: Optional[str] = None
    quizzes: List[QuizItem]
    createdAt: datetime

    class Config:
        populate_by_name = True
        use_enum_values = True

# Keyword 관련 스키마

class TermSummary(BaseModel):
    term: str
    term_summary: str

class KeywordTermsResponse(BaseModel):
    results: List[TermSummary]

class StockMatch(BaseModel):
    stock_name: str
    stock_code: str
    market: Optional[str] = None
    sector: Optional[str] = None

class KeywordStockResponse(BaseModel):
    matched_stocks: List[StockMatch]
