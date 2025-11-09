"""Redis Streams Producer - Keyword Extraction 결과 전송용"""

import redis
import logging
import json
from typing import Optional, List
from ...core.config import settings
from ...models.schemas import TermSummary

logger = logging.getLogger(__name__)


class KeywordRedisProducer:
    """Redis Streams를 사용하여 키워드 추출 결과를 전송하는 프로듀서"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.result_stream_key = settings.REDIS_KEYWORD_RESULT_STREAM_KEY

    def connect(self):
        """Redis 연결"""
        try:
            # Redis 호스트에서 포트 정보 제거 (있는 경우)
            redis_host = settings.REDIS_HOST.split(':')[0] if ':' in settings.REDIS_HOST else settings.REDIS_HOST

            # Redis 클라이언트 생성 (TLS 지원)
            self.redis_client = redis.Redis(
                host=redis_host,
                port=settings.REDIS_PORT,
                decode_responses=True,
                ssl=settings.REDIS_USE_TLS,
                ssl_cert_reqs=settings.REDIS_SSL_CERT_REQS
            )

            # 연결 테스트
            self.redis_client.ping()
            logger.info("Redis 연결 성공 (Keyword Producer)")

        except Exception as e:
            logger.error(f"Redis 연결 실패 (Keyword Producer): {str(e)}")
            raise

    def disconnect(self):
        """Redis 연결 종료"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis 연결 종료 (Keyword Producer)")

    def send_result(self, article_id: str, terms: List[TermSummary]) -> Optional[str]:
        """
        키워드 추출 결과를 Redis Stream에 전송합니다.

        Args:
            article_id: 기사 ID
            terms: 추출된 키워드 리스트

        Returns:
            메시지 ID (성공 시) 또는 None (실패 시)
        """
        try:
            if not self.redis_client:
                raise RuntimeError("Redis가 연결되지 않았습니다")

            # terms에서 term 필드만 추출하여 문자열 배열로 변환
            # 형식: ["term1", "term2", "term3"]
            term_strings = [term.term for term in terms]
            terms_json = json.dumps(term_strings, ensure_ascii=False)

            # Redis Stream에 전송할 데이터 준비
            # AI 서버가 보낼 메시지 형식: {"articleId": "xxx", "terms": "[\"term1\", \"term2\"]"}
            stream_data = {
                "articleId": str(article_id),
                "terms": terms_json
            }

            # Redis Stream에 추가
            message_id = self.redis_client.xadd(
                self.result_stream_key,
                stream_data
            )

            logger.info(f"키워드 추출 결과 전송 완료: articleId={article_id}, terms={len(terms)}개, messageId={message_id}")
            return message_id

        except Exception as e:
            logger.error(f"키워드 추출 결과 전송 중 오류 (articleId={article_id}): {str(e)}")
            return None

    def get_stream_length(self) -> int:
        """
        결과 스트림의 메시지 개수를 반환합니다.

        Returns:
            스트림 내 메시지 개수
        """
        try:
            if not self.redis_client:
                raise RuntimeError("Redis가 연결되지 않았습니다")

            return self.redis_client.xlen(self.result_stream_key)

        except Exception as e:
            logger.error(f"스트림 길이 조회 중 오류: {str(e)}")
            return 0

    def trim_stream(self, max_len: int = 10000, approximate: bool = True):
        """
        Stream 크기를 제한합니다. (오래된 메시지 삭제)

        Args:
            max_len: 최대 메시지 개수
            approximate: True면 대략적인 trimming (성능 향상)
        """
        try:
            if not self.redis_client:
                raise RuntimeError("Redis가 연결되지 않았습니다")

            # MAXLEN 옵션으로 Stream 크기 제한
            if approximate:
                # ~를 사용하면 Redis가 성능 최적화된 방식으로 trimming
                self.redis_client.xtrim(
                    name=self.result_stream_key,
                    maxlen=max_len,
                    approximate=True
                )
            else:
                # 정확한 개수로 trimming
                self.redis_client.xtrim(
                    name=self.result_stream_key,
                    maxlen=max_len,
                    approximate=False
                )

            logger.info(f"Keyword Result Stream trimming 완료 (max_len={max_len}, approximate={approximate})")

        except Exception as e:
            logger.error(f"Keyword Result Stream trimming 중 오류: {str(e)}")


# 전역 Keyword Redis Producer 인스턴스
keyword_redis_producer = KeywordRedisProducer()
