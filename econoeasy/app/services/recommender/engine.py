"""추천 알고리즘 엔진"""

from typing import Dict, Any, List


class RecommendationEngine:
    
    @staticmethod
    def create_recommendation(analyzed_videos: List[Dict[str, Any]], top_n: int = 1) -> List[Dict[str, Any]]:
        """
        분석된 영상들 중 최고 점수 top_n개 추천
        
        Args:
            analyzed_videos: 분석된 영상 목록
            top_n: 추천할 영상 개수
        
        Returns:
            추천 영상 리스트
        """
        if not analyzed_videos:
            return []
        
        # 요청된 개수만큼 추천 (분석된 영상 개수를 초과하지 않도록)
        recommendations = []
        num_recommendations = min(top_n, len(analyzed_videos))
        
        for rank, video in enumerate(analyzed_videos[:num_recommendations], 1):
            print(f"\n🏆 추천 영상 {rank}: {video['title']} (점수: {video['final_score']:.2f})")
            
            # YouTube 영상 URL 생성
            video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
            
            # 추천 결과 생성
            recommendation = {
                "rank": rank,
                "video_id": video["video_id"],
                "title": video["title"],
                "video_url": video_url,
                "channel": video["channel"],
                "recommendation_score": video["final_score"],
                "quality_score": video["quality_score"],
                "relevance_score": video["relevance_score"],
                "educational_value": video.get("educational_value", 75.0),
                "content_accuracy": video.get("content_accuracy", 75.0),
                "analysis_summary": video["analysis_summary"],
                "trust_comment": video.get("trust_comment", "분석 완료"),
                "gemini_analyzed": True,
                "metrics": {
                    "view_count": str(video["view_count"]),
                    "like_count": str(video["like_count"]),
                    "comment_count": video["comment_count"],
                    "positive_ratio": 85.0  # 기본값
                }
            }
            
            recommendations.append(recommendation)
        
        return recommendations
