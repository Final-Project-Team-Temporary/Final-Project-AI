"""백그라운드 워커 - Redis Stream에서 메시지를 소비하고 YouTube 영상을 추천"""

import asyncio
import logging
from typing import Optional
from .redis_consumer import recommend_redis_consumer
from .redis_producer import recommend_redis_producer
from ..recommender import recommender_service
from ...models.schemas import RecommendationRequest, YoutubeVideo, VideoRecommendation

logger = logging.getLogger(__name__)


class RecommendProcessWorker:
    """Redis Stream에서 YouTube 추천 작업을 소비하는 백그라운드 워커"""

    def __init__(self):
        self.running = False
        self.process_count = 0
        self.error_count = 0

    async def start(self):
        """워커 시작"""
        logger.info("=== Recommend Process Worker 시작 ===")

        # Redis 연결 (Consumer & Producer)
        recommend_redis_consumer.connect()
        recommend_redis_producer.connect()

        self.running = True

        # 메시지 처리 루프
        await self._process_loop()

    async def stop(self):
        """워커 중지"""
        logger.info("=== Recommend Process Worker 중지 ===")
        self.running = False

        # 연결 종료
        recommend_redis_consumer.disconnect()
        recommend_redis_producer.disconnect()

        logger.info(f"총 처리: {self.process_count}건, 에러: {self.error_count}건")

    async def _process_loop(self):
        """메시지 처리 루프"""
        while self.running:
            try:
                # Redis Stream에서 메시지 읽기 (최대 5초 대기)
                messages = recommend_redis_consumer.read_messages(count=10, block=5000)

                if not messages:
                    # 메시지가 없으면 계속 대기
                    continue

                # 각 메시지 처리
                for message in messages:
                    await self._process_message(message)

            except Exception as e:
                logger.error(f"메시지 처리 루프 중 오류: {str(e)}")
                await asyncio.sleep(5)  # 에러 시 5초 대기 후 재시도

    async def _process_message(self, message: dict):
        """
        개별 메시지 처리

        Args:
            message: {"id": record_id, "data": KeywordRecommendStreamMessage}
        """
        record_id = message["id"]
        stream_data = message["data"]
        keyword_id = stream_data.keywordId
        keyword_name = stream_data.keywordName

        logger.info(f"[{record_id}] 추천 처리 시작: keywordId={keyword_id}, keyword={keyword_name}")

        try:
            # 1. RecommendationRequest 생성
            recommend_request = RecommendationRequest(
                keyword=keyword_name,
                top_n=3  # 기본값: 3개
            )

            # 2. 추천 서비스 호출
            logger.info(f"[{record_id}] Recommender Service 호출: keyword={keyword_name}")
            recommendation_result = await recommender_service.recommend_videos(recommend_request)

            # 3. 추천 결과 로깅
            if recommendation_result["status"] == "success":
                logger.info(f"[{record_id}] 추천 완료:")
                logger.info(f"  - 분석된 영상 수: {recommendation_result['total_analyzed']}")
                logger.info(f"  - 추천 영상 수: {len(recommendation_result['recommendations'])}")

                # 4. VideoRecommendation을 YoutubeVideo로 변환
                youtube_videos = []
                for rec_dict in recommendation_result['recommendations']:
                    # dict를 VideoRecommendation으로 변환
                    video_rec = VideoRecommendation(**rec_dict)
                    # YoutubeVideo로 변환
                    youtube_video = YoutubeVideo.from_recommendation(video_rec)
                    youtube_videos.append(youtube_video)

                # 5. 결과를 Redis Stream에 전송
                message_id = recommend_redis_producer.send_result(
                    keyword_id=keyword_id,
                    videos=youtube_videos
                )

                if message_id:
                    logger.info(f"[{record_id}] 결과 전송 완료: messageId={message_id}")
                else:
                    logger.error(f"[{record_id}] 결과 전송 실패")
                    self.error_count += 1
            else:
                # 추천 서비스 실패
                logger.error(f"[{record_id}] 추천 서비스 실패: {recommendation_result.get('message', 'Unknown error')}")
                self.error_count += 1

            # 6. Redis 메시지 ACK
            recommend_redis_consumer.acknowledge_message(record_id)

            self.process_count += 1
            logger.info(f"[{record_id}] 추천 처리 완료: keywordId={keyword_id}, keyword={keyword_name}")

        except Exception as e:
            logger.error(f"[{record_id}] 추천 처리 중 오류 발생: {str(e)}")

            # 메시지 ACK (재처리 방지)
            recommend_redis_consumer.acknowledge_message(record_id)

            self.error_count += 1


# 전역 워커 인스턴스
recommend_worker = RecommendProcessWorker()


async def run_recommend_worker():
    """워커 실행 함수 (메인 함수)"""
    try:
        await recommend_worker.start()
    except KeyboardInterrupt:
        logger.info("워커 종료 요청")
    except Exception as e:
        logger.error(f"워커 실행 중 치명적 오류: {str(e)}")
    finally:
        await recommend_worker.stop()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 워커 실행
    asyncio.run(run_recommend_worker())
