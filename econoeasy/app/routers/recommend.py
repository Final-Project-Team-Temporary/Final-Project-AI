from fastapi import APIRouter, HTTPException
from ..models.schemas import RecommendationRequest, RecommendationResponse, ErrorResponse
from ..services.recommender import recommender_service

router = APIRouter(
    prefix="/recommend",
    tags=["recommend"],
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "서버 오류"}
    }
)

@router.post("/videos", response_model=RecommendationResponse)
async def recommend_videos(request: RecommendationRequest):
    """
    키워드 기반 YouTube 영상 추천
    
    - **keyword**: 검색할 키워드
    - **top_n**: 추천할 영상 개수 (기본값: 3)
    
    **요청 예시:**
    ```json
    {
        "keyword": "파이썬 기초",
        "top_n": 3
    }
    ```
    
    **응답 예시:**
    ```json
    {
        "status": "success",
        "total_analyzed": 10,
        "recommendations": [
            {
                "rank": 1,
                "title": "파이썬 기초 강의",
                "video_id": "abc123",
                "channel": "코딩채널",
                "recommendation_score": 85.5,
                "quality_score": 78.2,
                "relevance_score": 95.0,
                "educational_value": 88.5,
                "content_accuracy": 92.3,
                "analysis_summary": "파이썬 기초 문법을 체계적으로 설명하는 교육 영상",
                "trust_comment": "구체적인 예제와 실습을 통해 학습 효과가 높음",
                "metrics": {
                    "view_count": "150000",
                    "like_count": "5000",
                    "comment_count": 120,
                    "positive_ratio": 85.2
                }
            }
        ]
    }
    ```
    """
    try:
        result = await recommender_service.recommend_videos(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"영상 추천 처리 중 오류가 발생했습니다: {str(e)}"
        )
