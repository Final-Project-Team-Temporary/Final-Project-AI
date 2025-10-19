"""백그라운드 워커 - Redis Stream에서 메시지를 소비하고 기사를 요약"""

import asyncio
import logging
from typing import Optional
from .mongodb_client import mongodb_client
from .redis_consumer import redis_consumer
from ..summarizer import summarizer_service
from ...models.schemas import ArticleInput

logger = logging.getLogger(__name__)


class ArticleProcessWorker:
    """Redis Stream에서 기사 처리 작업을 소비하는 백그라운드 워커"""

    def __init__(self):
        self.running = False
        self.process_count = 0
        self.error_count = 0

    async def start(self):
        """워커 시작"""
        logger.info("=== Article Process Worker 시작 ===")

        # MongoDB 연결
        await mongodb_client.connect()

        # Redis 연결
        redis_consumer.connect()

        self.running = True

        # 메시지 처리 루프
        await self._process_loop()

    async def stop(self):
        """워커 중지"""
        logger.info("=== Article Process Worker 중지 ===")
        self.running = False

        # 연결 종료
        await mongodb_client.disconnect()
        redis_consumer.disconnect()

        logger.info(f"총 처리: {self.process_count}건, 에러: {self.error_count}건")

    async def _process_loop(self):
        """메시지 처리 루프"""
        while self.running:
            try:
                # Redis Stream에서 메시지 읽기 (최대 5초 대기)
                messages = redis_consumer.read_messages(count=10, block=5000)

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
            message: {"id": record_id, "data": RedisStreamMessage}
        """
        record_id = message["id"]
        stream_data = message["data"]
        article_id = stream_data.articleId

        logger.info(f"[{record_id}] 기사 처리 시작: articleId={article_id}")

        try:
            # 1. MongoDB에서 기사 조회
            article_doc = await mongodb_client.get_article_by_id(article_id)

            if not article_doc:
                logger.warning(f"[{record_id}] 기사를 찾을 수 없음: {article_id}")
                redis_consumer.acknowledge_message(record_id)
                self.error_count += 1
                return

            # 2. 기사 상태를 PROCESSING으로 업데이트
            await mongodb_client.update_summary_status(article_id, "PROCESSING")

            # 3. 요약 서비스 호출
            article_input = ArticleInput(
                title=article_doc.title,
                content=article_doc.content
            )

            summary_result = await summarizer_service.summarize_article(article_input)

            # 4. 요약 결과 로깅
            logger.info(f"[{record_id}] 요약 완료:")
            logger.info(f"  - Easy: {summary_result.easy[:50]}...")
            logger.info(f"  - Medium: {summary_result.medium[:50]}...")
            logger.info(f"  - Advanced: {summary_result.advanced[:50]}...")

            # 5. 요약 결과를 MongoDB에 저장
            await mongodb_client.save_summary(
                article_id=article_id,
                article_title=article_doc.title,
                published_at=article_doc.publishedAt,
                summary_output=summary_result
            )

            # 6. 기사 상태를 COMPLETED로 업데이트
            await mongodb_client.update_summary_status(article_id, "COMPLETED")

            # 7. Redis 메시지 ACK
            redis_consumer.acknowledge_message(record_id)

            self.process_count += 1
            logger.info(f"[{record_id}] 기사 처리 완료: articleId={article_id}")

        except Exception as e:
            logger.error(f"[{record_id}] 기사 처리 중 오류 발생: {str(e)}")

            # 에러 발생 시 상태를 FAILED로 업데이트
            try:
                await mongodb_client.update_summary_status(article_id, "FAILED")
            except Exception as update_error:
                logger.error(f"상태 업데이트 실패: {str(update_error)}")

            # 메시지 ACK (재처리 방지)
            redis_consumer.acknowledge_message(record_id)

            self.error_count += 1

    async def process_pending_messages(self):
        """
        Pending 상태의 메시지를 재처리합니다.
        (다른 워커가 가져갔지만 처리하지 못한 메시지)
        """
        logger.info("Pending 메시지 확인 중...")

        pending_messages = redis_consumer.get_pending_messages(count=100)

        if not pending_messages:
            logger.info("Pending 메시지 없음")
            return

        logger.info(f"{len(pending_messages)}개의 Pending 메시지 발견")

        for pending in pending_messages:
            record_id = pending["id"]
            times_delivered = pending["times_delivered"]

            # 3번 이상 실패한 메시지는 건너뛰기
            if times_delivered >= 3:
                logger.warning(f"메시지 처리 포기 (3회 이상 실패): {record_id}")
                redis_consumer.acknowledge_message(record_id)
                continue

            # 메시지 재할당 (1분 이상 유휴 상태인 경우)
            claimed_message = redis_consumer.claim_message(record_id, min_idle_time=60000)

            if claimed_message:
                logger.info(f"Pending 메시지 재처리: {record_id}")
                # 재처리 로직은 일반 메시지 처리와 동일
                # (실제로는 XCLAIM으로 가져온 메시지를 파싱해서 처리해야 함)


# 전역 워커 인스턴스
article_worker = ArticleProcessWorker()


async def run_worker():
    """워커 실행 함수 (메인 함수)"""
    try:
        await article_worker.start()
    except KeyboardInterrupt:
        logger.info("워커 종료 요청")
    except Exception as e:
        logger.error(f"워커 실행 중 치명적 오류: {str(e)}")
    finally:
        await article_worker.stop()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 워커 실행
    asyncio.run(run_worker())
