"""YouTube API 클라이언트"""

from typing import Dict, List, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ...core.config import settings
import os


class YouTubeClient:
    
    def __init__(self):
        self.youtube_api_key = settings.YOUTUBE_API_KEY
        self.max_results = settings.YOUTUBE_MAX_RESULTS
        
        # API 키 확인
        if not self.youtube_api_key or self.youtube_api_key == "your_youtube_api_key_here":
            raise ValueError("YouTube API 키가 설정되지 않았습니다. .env 파일에 YOUTUBE_API_KEY를 추가하세요.")
        
        # YouTube API 클라이언트 초기화
        self.youtube = build('youtube', 'v3', 
                           developerKey=self.youtube_api_key,
                           cache_discovery=False,
                           static_discovery=False)
        print(f"✅ YouTube API 클라이언트 초기화 완료 (API 키: {self.youtube_api_key[:10]}...)")
    
    async def search_videos(self, keyword: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        YouTube API를 사용한 영상 검색
        조회수/좋아요 기준으로 정렬하여 상위 top_n개 반환
        """
        print(f"🔍 YouTube API로 '{keyword}' 검색 중...")
        
        try:
            # Step 1: 교육/정보 콘텐츠만 선별하여 검색
            educational_query = f"{keyword} 강의 OR 해설 OR 튜토리얼 OR 리뷰 OR 설명 OR 기초"
            print(f"🔍 검색 키워드: '{keyword}' -> 쿼리: '{educational_query}'")
            
            search_response = self.youtube.search().list(
                q=educational_query,
                part='id,snippet',
                type='video',
                # videoCategoryId='27',  # 교육 카테고리 제한 완화
                maxResults=min(top_n * 10, 50),  # top_n의 10배 검색 (철저한 필터링)
                order='relevance',  # 관련성순
                regionCode='KR',  # 한국
                relevanceLanguage='ko'  # 한국어
            ).execute()
            
            print(f"  📥 교육 콘텐츠 검색 결과: {len(search_response.get('items', []))}개 영상")
            print(f"  🔍 검색 쿼리: '{educational_query}'")
            
            # 검색된 영상 제목 출력 (디버깅)
            for idx, item in enumerate(search_response.get('items', [])[:5], 1):
                print(f"    {idx}. {item['snippet']['title'][:60]}")
            
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            if not video_ids:
                raise ValueError(f"'{keyword}' 검색 결과가 없습니다.")
            
            # Step 2: 영상 통계 정보 가져오기
            videos_response = self.youtube.videos().list(
                part='snippet,statistics',
                id=','.join(video_ids)
            ).execute()
            
            videos_data = []
            # 키워드를 공백으로 분리
            keyword_parts = keyword.lower().split()
            
            for item in videos_response.get('items', []):
                video_id = item['id']
                snippet = item['snippet']
                statistics = item['statistics']
                
                # 조회수와 좋아요 수가 있는 영상만 포함
                if 'viewCount' in statistics and 'likeCount' in statistics:
                    view_count = int(statistics['viewCount'])
                    like_count = int(statistics['likeCount'])
                    comment_count = int(statistics.get('commentCount', 0))
                    
                    # 최소 조회수 필터 (1000회 이상)
                    if view_count < 1000:
                        continue
                    
                    # 제목이나 설명에서 키워드 관련성 확인
                    title = snippet['title']
                    title_lower = title.lower()
                    description_lower = snippet.get('description', '').lower()
                    
                    # 키워드의 각 단어가 제목이나 설명에 있는지 확인
                    # 최소 1개 이상의 키워드 단어가 포함되어야 함
                    keyword_match_count = 0
                    for part in keyword_parts:
                        if len(part) > 1:  # 1글자 키워드는 제외
                            if part in title_lower or part in description_lower:
                                keyword_match_count += 1
                    
                    # 키워드 단어의 50% 이상이 매칭되어야 함
                    required_matches = max(1, len([p for p in keyword_parts if len(p) > 1]) // 2)
                    
                    if keyword_match_count < required_matches:
                        print(f"  ⏭️ 스킵: '{title[:40]}...' (키워드 불일치: {keyword_match_count}/{required_matches})")
                        continue
                    
                    videos_data.append({
                        'video_id': video_id,
                        'title': snippet['title'],
                        'channel': snippet['channelTitle'],
                        'view_count': view_count,
                        'like_count': like_count,
                        'comment_count': comment_count,
                        'description': snippet.get('description', '')[:200],  # 설명 200자까지
                        'published_at': snippet['publishedAt']
                    })
            
            # 검색 결과가 충분하지 않으면 오류
            if len(videos_data) < top_n:
                print(f"⚠️ 필터링 후 영상 {len(videos_data)}개만 발견 (필요: {top_n}개)")
                if len(videos_data) == 0:
                    raise ValueError(f"'{keyword}'에 대한 적절한 영상을 찾을 수 없습니다.")
            
            # Step 3: 조회수 70% + 좋아요 30% 가중치로 정렬
            sorted_videos = sorted(
                videos_data,
                key=lambda x: (x['view_count'] * 0.7 + x['like_count'] * 0.3),
                reverse=True
            )
            
            # Step 4: 상위 top_n개 선택
            top_videos = sorted_videos[:top_n]
            
            print(f"📺 YouTube API 검색 완료: {len(top_videos)}개 영상 선택")
            for i, video in enumerate(top_videos, 1):
                print(f"  {i}. {video['title'][:50]} (조회수: {video['view_count']:,}, 좋아요: {video['like_count']:,})")
            
            # Step 5: 각 영상의 댓글 가져오기
            for video in top_videos:
                video['comments'] = await self._get_video_comments(video['video_id'], max_comments=15)
            
            return top_videos
            
        except HttpError as e:
            error_msg = f"YouTube API 오류: {e}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"YouTube 검색 중 오류 발생: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    async def _get_video_comments(self, video_id: str, max_comments: int = 15) -> List[str]:
        """
        YouTube API를 사용하여 영상의 댓글 가져오기
        """
        try:
            comments_response = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=max_comments,
                order='relevance',  # 관련성순 (인기 댓글)
                textFormat='plainText'
            ).execute()
            
            comments = []
            for item in comments_response.get('items', []):
                comment_text = item['snippet']['topLevelComment']['snippet']['textDisplay']
                # 너무 짧은 댓글 제외 (3자 이상)
                if len(comment_text) >= 3:
                    comments.append(comment_text)
            
            print(f"  💬 댓글 {len(comments)}개 수집: {video_id[:11]}...")
            return comments
            
        except HttpError as e:
            # 댓글이 비활성화된 경우 등
            print(f"  ⚠️ 댓글 가져오기 실패 ({video_id}): {e}")
            return []
        except Exception as e:
            print(f"  ⚠️ 댓글 가져오기 오류: {e}")
            return []
