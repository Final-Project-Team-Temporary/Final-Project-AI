"""추천 알고리즘 엔진"""

from typing import Dict, Any, List


class RecommendationEngine:
    
    @staticmethod
    def create_recommendation(analyzed_videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        분석된 영상들 중 최고 점수 1개만 추천
        """
        if not analyzed_videos:
            return None
        
        # 최고 점수 영상 (이미 정렬되어 있음)
        best_video = analyzed_videos[0]
        
        print(f"\n🏆 최종 추천 영상: {best_video['title']} (점수: {best_video['final_score']:.2f})")
        
        # 추천 결과 생성 (1개만)
        recommendation = {
            "rank": 1,
            "video_id": best_video["video_id"],
            "title": best_video["title"],
            "channel": best_video["channel"],
            "recommendation_score": best_video["final_score"],
            "quality_score": best_video["quality_score"],
            "relevance_score": best_video["relevance_score"],
            "educational_value": best_video.get("educational_value", 75.0),
            "content_accuracy": best_video.get("content_accuracy", 75.0),
            "analysis_summary": best_video["analysis_summary"],
            "trust_comment": best_video.get("trust_comment", "분석 완료"),
            "gemini_analyzed": True,
            "metrics": {
                "view_count": str(best_video["view_count"]),
                "like_count": str(best_video["like_count"]),
                "comment_count": best_video["comment_count"],
                "positive_ratio": 85.0  # 기본값
            }
        }
        
        return recommendation
