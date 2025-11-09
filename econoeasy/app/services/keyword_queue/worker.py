"""백그라운드 워커 - Redis Stream에서 메시지를 소비하고 키워드를 추출"""

import asyncio
import logging
from typing import Optional
from .redis_consumer import keyword_redis_consumer
from .redis_producer import keyword_redis_producer
from ..queue.mongodb_client import mongodb_client
from ..keyword.service import keyword_service
from ...models.schemas import ArticleInput

logger = logging.getLogger(__name__)


class KeywordProcessWorker:
    """Redis Stream에서 키워드 추출 작업을 소비하는 백그라운드 워커"""

    def __init__(self):
        self.running = False
        self.process_count = 0
        self.error_count = 0

    async def start(self):
        """워커 시작"""
        logger.info("=== Keyword Process Worker 시작 ===")

        # MongoDB 연결
        await mongodb_client.connect()

        # Redis 연결 (Consumer & Producer)
        keyword_redis_consumer.connect()
        keyword_redis_producer.connect()

        self.running = True

        # 메시지 처리 루프
        await self._process_loop()

    async def stop(self):
        """워커 중지"""
        logger.info("=== Keyword Process Worker 중지 ===")
        self.running = False

        # 연결 종료
        await mongodb_client.disconnect()
        keyword_redis_consumer.disconnect()
        keyword_redis_producer.disconnect()

        logger.info(f"총 처리: {self.process_count}건, 에러: {self.error_count}건")

    async def _process_loop(self):
        """메시지 처리 루프"""
        while self.running:
            try:
                # Redis Stream에서 메시지 읽기 (최대 5초 대기)
                messages = keyword_redis_consumer.read_messages(count=10, block=5000)

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

        logger.info(f"[{record_id}] 키워드 추출 처리 시작: articleId={article_id}")

        try:
            # 1. MongoDB에서 기사 조회
            article_doc = await mongodb_client.get_article_by_id(article_id)

            if not article_doc:
                logger.warning(f"[{record_id}] 기사를 찾을 수 없음: {article_id}")
                keyword_redis_consumer.acknowledge_message(record_id)
                self.error_count += 1
                return

            # 2. ArticleInput 생성
            article_input = ArticleInput(
                title=article_doc.title,
                content=article_doc.content
            )

            # 3. 키워드 추출 서비스 호출
            logger.info(f"[{record_id}] Keyword Service 호출: articleId={article_id}")
            keyword_result = await keyword_service.extract_related_terms(article_input)

            # 4. 키워드 추출 결과 로깅
            logger.info(f"[{record_id}] 키워드 추출 완료:")
            logger.info(f"  - 추출된 키워드 수: {len(keyword_result.results)}")
            for term in keyword_result.results:
                logger.info(f"    - {term.term}: {term.term_summary[:50]}...")

            # 5. 결과를 Redis Stream에 전송
            message_id = keyword_redis_producer.send_result(
                article_id=article_id,
                terms=keyword_result.results
            )

            if message_id:
                logger.info(f"[{record_id}] 결과 전송 완료: messageId={message_id}")
            else:
                logger.error(f"[{record_id}] 결과 전송 실패")
                self.error_count += 1

            # 6. Redis 메시지 ACK
            keyword_redis_consumer.acknowledge_message(record_id)

            self.process_count += 1
            logger.info(f"[{record_id}] 키워드 추출 처리 완료: articleId={article_id}")

        except Exception as e:
            logger.error(f"[{record_id}] 키워드 추출 처리 중 오류 발생: {str(e)}")

            # 메시지 ACK (재처리 방지)
            keyword_redis_consumer.acknowledge_message(record_id)

            self.error_count += 1


# 전역 워커 인스턴스
keyword_worker = KeywordProcessWorker()


async def run_keyword_worker():
    """워커 실행 함수 (메인 함수)"""
    try:
        await keyword_worker.start()
    except KeyboardInterrupt:
        logger.info("워커 종료 요청")
    except Exception as e:
        logger.error(f"워커 실행 중 치명적 오류: {str(e)}")
    finally:
        await keyword_worker.stop()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 워커 실행
    asyncio.run(run_keyword_worker())
