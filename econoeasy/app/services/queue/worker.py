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
            error_msg = str(e)
            logger.error(f"[{record_id}] 기사 처리 중 오류 발생: {str(e)}")

            # 영구적 에러 조건 (예: DB에 기사가 없음, 잘못된 포맷 등)
            if "Not Found" in error_msg or "Parse Error" in error_msg:
                await mongodb_client.update_summary_status(article_id, "FAILED_PERMANENTLY")
                # 영구적 에러는 재시도하지 않고 바로 DLQ로 보낸 뒤 ACK 처리 (4단계에서 구현)
                await self._send_to_dlq(record_id, stream_data, error_msg)
                redis_consumer.acknowledge_message(record_id)
                
            # 일시적 에러 (네트워크 지연, API Rate Limit 등)
            else:
                await mongodb_client.update_summary_status(article_id, "RETRYING")
                # 핵심: 일시적 에러일 경우 ACK를 하지 않습니다! 
                # ACK를 하지 않으면 Redis의 PEL(Pending Entries List)에 남게 되어 재시도 대상이 됩니다.
            
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
            idle_time_ms = pending["idle_time"]

            # 3단계: 지수 백오프 계산 (예: 1회 실패시 10초, 2회시 20초, 3회시 40초 대기)
            # times_delivered는 처음 읽을 때 1이므로, (2 ** (times_delivered - 1)) 형태 활용
            required_idle_time = (2 ** (times_delivered - 1)) * 10000 

            # 아직 백오프 대기 시간이 지나지 않았다면 스킵 (다음 루프에서 다시 확인)
            if idle_time_ms < required_idle_time:
                continue

            MAX_RETRIES = 3
            
            # 최대 재시도 횟수 초과 시 DLQ로 이동
            if times_delivered > MAX_RETRIES:
                logger.warning(f"메시지 처리 최종 실패 (DLQ 이동): {record_id}")
                
                # 원본 메시지 데이터를 가져옴 (실제로는 get_message_by_id 등의 구현 필요)
                message_data = redis_consumer.get_message(record_id) 
                
                # DLQ 처리 (새로운 Redis Stream인 'article_summary_dlq'로 발행하거나 DB에 기록)
                await self._send_to_dlq(record_id, message_data, "최대 재시도 횟수 초과")
                
                # DLQ에 안전하게 적재했으므로 원본 큐에서는 ACK 처리하여 제거
                redis_consumer.acknowledge_message(record_id)
                continue

            # 대기 시간이 지났고 최대 횟수를 넘지 않았다면 재처리(Claim)
            claimed_message = redis_consumer.claim_message(record_id, min_idle_time=required_idle_time)
            if claimed_message:
                logger.info(f"Pending 메시지 지수 백오프 재처리: {record_id}, 시도 횟수: {times_delivered}")
                await self._process_message(claimed_message)


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

async def _send_to_dlq(self, original_record_id, data, reason):
        dlq_payload = {
            "original_id": original_record_id,
            "articleId": data.get("articleId", "unknown"),
            "failed_at": datetime.utcnow().isoformat(),
            "reason": reason
        }
        # 방법 1: Redis의 다른 Stream(DLQ)에 저장
        # redis_client.xadd("article_summary_dlq", dlq_payload)
        
        # 방법 2: MongoDB의 별도 DLQ 컬렉션에 저장 (추천)
        await mongodb_client.save_dlq_record(dlq_payload)
        pass



if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 워커 실행
    asyncio.run(run_worker())
