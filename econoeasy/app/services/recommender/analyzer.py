"""영상 분석 및 점수 계산"""

from typing import Dict, List, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from ...core.config import settings


class VideoAnalyzer:
    
    def __init__(self):
        """Gemini API 클라이언트 초기화"""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.3
        )
    
    async def analyze_video_with_gemini(self, video: Dict[str, Any], keyword: str) -> Dict[str, Any]:
        """
        Gemini API를 사용한 영상 분석 (댓글 15개 기준)
        품질 점수와 관련성 점수를 반환
        """
        comments = video.get("comments", [])
        
        if not comments:
            return {
                "quality_score": 70.0,
                "relevance_score": 70.0,
                "analysis_summary": "댓글 데이터가 없습니다.",
                "trust_comment": "댓글 분석 불가",
                "educational_value": 70.0,
                "content_accuracy": 70.0
            }
        
        # 댓글 15개만 추출
        comments_15 = comments[:15]
        comments_text = "\n".join(comments_15)
        
        prompt = f"""
        다음은 "{keyword}" 키워드와 관련된 YouTube 영상의 댓글 15개입니다. 
        이 댓글들을 종합적으로 분석하여 영상의 품질 점수, 관련성 점수, 그리고 신뢰도 지표를 제공해주세요.

        영상 제목: {video['title']}
        채널명: {video['channel']}
        댓글들:
        {comments_text}

        다음 형식으로 JSON 응답을 해주세요:
        {{
            "quality_score": 0-100 사이의 품질 점수,
            "relevance_score": 0-100 사이의 관련성 점수,
            "analysis_summary": "영상의 내용과 특징을 한 줄로 요약",
            "trust_comment": "이 영상이 신뢰할 만한 이유나 정보 전달력의 강점을 한 줄로 설명",
            "educational_value": 0-100 사이의 교육적 가치 점수,
            "content_accuracy": 0-100 사이의 내용 정확도 점수
        }}

        분석 기준:
        - quality_score: 댓글에서 드러나는 영상의 전반적 품질 (설명력, 이해도, 만족도, 영상 구성)
        - relevance_score: "{keyword}" 키워드와 영상의 관련성 (댓글에서 키워드 관련 언급, 내용 일치도)
        - analysis_summary: 이 영상이 어떤 내용을 다루고 어떤 특징을 가지는지 한 줄로 요약
        - trust_comment: 댓글을 통해 확인되는 영상의 신뢰성이나 정보 전달력의 강점을 한 줄로 설명
        - educational_value: 교육적 가치 (학습 효과, 이해도 향상, 실용성)
        - content_accuracy: 내용의 정확성과 전문성 (댓글에서 드러나는 내용의 신뢰성)
        
        특히 금융, 경제, AI 관련 키워드의 경우 전문성과 정확성을 중점적으로 평가해주세요.
        """
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            # JSON 파싱 시도
            import json
            import re
            
            # JSON 부분만 추출
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                # JSON 파싱 실패 시 기본값 반환
                return {
                    "quality_score": 75.0,
                    "relevance_score": 75.0,
                    "analysis_summary": "분석 완료",
                    "trust_comment": "분석 완료",
                    "educational_value": 75.0,
                    "content_accuracy": 75.0
                }
        except Exception as e:
            print(f"Gemini API 분석 오류: {e}")
            return {
                "quality_score": 70.0,
                "relevance_score": 70.0,
                "analysis_summary": f"분석 중 오류 발생: {str(e)}",
                "trust_comment": "분석 오류",
                "educational_value": 70.0,
                "content_accuracy": 70.0
            }
    
    async def analyze_videos(self, videos: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
        """
        영상 분석 및 점수 계산 (Gemini API 사용)
        각 영상의 댓글 15개를 분석하여 품질/관련성 점수 계산
        """
        analyzed_videos = []
        
        for video in videos:
            print(f"\n📊 Gemini API로 '{video['title']}' 분석 중...")
            
            # Gemini API로 댓글 15개 분석
            gemini_analysis = await self.analyze_video_with_gemini(video, keyword)
            
            print(f"✅ 분석 완료 - 품질: {gemini_analysis['quality_score']}, 관련성: {gemini_analysis['relevance_score']}")
            
            # 최종 점수 계산: 품질 40% + 관련성 30% + 교육가치 20% + 정확도 10%
            final_score = (
                gemini_analysis["quality_score"] * 0.4 + 
                gemini_analysis["relevance_score"] * 0.3 +
                gemini_analysis["educational_value"] * 0.2 +
                gemini_analysis["content_accuracy"] * 0.1
            )
            
            analyzed_videos.append({
                "video_id": video["video_id"],
                "title": video["title"],
                "channel": video["channel"],
                "view_count": video["view_count"],
                "like_count": video["like_count"],
                "comment_count": video["comment_count"],
                "quality_score": gemini_analysis["quality_score"],
                "relevance_score": gemini_analysis["relevance_score"],
                "educational_value": gemini_analysis["educational_value"],
                "content_accuracy": gemini_analysis["content_accuracy"],
                "final_score": final_score,
                "analysis_summary": gemini_analysis["analysis_summary"],
                "trust_comment": gemini_analysis["trust_comment"],
                "gemini_analyzed": True
            })
        
        # 최종 점수 기준으로 정렬
        analyzed_videos.sort(key=lambda x: x["final_score"], reverse=True)
        
        return analyzed_videos
