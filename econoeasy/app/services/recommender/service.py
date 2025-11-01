"""유튜브 영상 추천 서비스"""

from typing import Dict, Any
from ...core.config import settings
from .client import YouTubeClient
from .analyzer import VideoAnalyzer
from .engine import RecommendationEngine


class RecommenderService:
    
    def __init__(self):
        self.youtube_client = YouTubeClient()
        self.video_analyzer = VideoAnalyzer()
        self.recommendation_engine = RecommendationEngine()
        self.default_top_n = settings.YOUTUBE_DEFAULT_TOP_N
    
    async def recommend_videos(self, request) -> Dict[str, Any]:
        """
        키워드 기반 YouTube 영상 추천
        
        프로세스:
        1. 조회수/좋아요 기준 상위 top_n개 영상 선택
        2. 각 영상의 댓글 15개를 Gemini로 분석 (품질/관련성 점수)
        3. 최고 점수 1개만 추천
        """
        try:
            # 요청에서 키워드와 top_n 추출
            keyword = request.keyword
            top_n = request.top_n
            
            # Step 1: 조회수/좋아요 기준 상위 top_n개 영상 검색
            videos = await self.youtube_client.search_videos(keyword, top_n)
            
            # Step 2: 각 영상의 댓글 15개를 Gemini API로 분석
            analyzed_videos = await self.video_analyzer.analyze_videos(videos, keyword)
            
            # Step 3: 최고 점수 1개만 추천
            recommendation = self.recommendation_engine.create_recommendation(analyzed_videos)
            
            print(f"✅ 추천 완료: 총 {len(analyzed_videos)}개 영상 분석, 1개 추천")
            
            return {
                "status": "success",
                "total_analyzed": len(analyzed_videos),
                "recommendations": [recommendation] if recommendation else []
            }
            
        except Exception as e:
            print(f"❌ 추천 처리 중 오류: {e}")
            return {
                "status": "error",
                "message": f"추천 처리 중 오류: {str(e)}",
                "total_analyzed": 0,
                "recommendations": []
            }


# 전역 서비스 인스턴스
recommender_service = RecommenderService()
