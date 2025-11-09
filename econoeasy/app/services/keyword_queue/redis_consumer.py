"""Redis Streams Consumer - Keyword Extraction용"""

import redis
import logging
from typing import Optional, Dict, Any, List
from ...core.config import settings
from ...models.schemas import RedisStreamMessage

logger = logging.getLogger(__name__)


class KeywordRedisConsumer:
    """Redis Streams를 사용하여 키워드 추출 작업을 소비하는 컨슈머"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.stream_key = settings.REDIS_KEYWORD_STREAM_KEY
        self.consumer_group = settings.REDIS_KEYWORD_CONSUMER_GROUP
        self.consumer_name = settings.REDIS_KEYWORD_CONSUMER_NAME

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
            logger.info("Redis 연결 성공 (Keyword Consumer)")

            # Consumer Group 생성 또는 확인
            self._ensure_consumer_group()

        except Exception as e:
            logger.error(f"Redis 연결 실패 (Keyword Consumer): {str(e)}")
            raise

    def _ensure_consumer_group(self):
        """Consumer Group이 정상 상태인지 확인하고 필요시 생성"""
        try:
            # Consumer Group 생성 시도
            self.redis_client.xgroup_create(
                name=self.stream_key,
                groupname=self.consumer_group,
                id='0',  # consumer group 생성 시에는 0부터 message 읽기
                mkstream=True
            )
            logger.info(f"Consumer Group 생성: {self.consumer_group}")

        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer Group 이미 존재: {self.consumer_group}")
                # Consumer Group 정보 로깅
                info = self.get_consumer_group_info()
                if info:
                    logger.info(
                        f"Consumer Group 상태 - "
                        f"Lag: {info.get('lag', 0)}, "
                        f"Pending: {info.get('pending', 0)}, "
                        f"Last Delivered: {info.get('last_delivered_id', '0-0')}"
                    )
            else:
                raise

    def disconnect(self):
        """Redis 연결 종료"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis 연결 종료 (Keyword Consumer)")

    def read_messages(self, count: int = 10, block: int = 5000) -> List[Dict[str, Any]]:
        """
        Redis Stream에서 메시지를 읽어옵니다.

        Args:
            count: 한 번에 읽을 메시지 수
            block: 블록킹 시간 (밀리초), 0이면 무한 대기

        Returns:
            메시지 리스트 [{"id": record_id, "data": RedisStreamMessage}, ...]
        """
        try:
            if not self.redis_client:
                raise RuntimeError("Redis가 연결되지 않았습니다")

            # 1. 새 메시지 읽기 시도
            # '>'는 Consumer Group이 아직 읽지 않은 새 메시지만 가져옴
            messages = self.redis_client.xreadgroup(
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                streams={self.stream_key: '>'},
                count=count,
                block=block
            )

            # 디버깅: Consumer Group 상태 로깅
            if not messages:
                info = self.get_consumer_group_info()
                logger.debug(f"새 메시지 없음 - Consumer Group 상태: {info}")

            # 2. 새 메시지가 없으면 Pending 메시지 확인 및 재처리
            if not messages:
                messages = self._handle_pending_messages(count)

                # 3. Pending도 없고 Stream에 메시지가 있다면 Consumer Group 리셋 시도
                if not messages:
                    stream_length = self.redis_client.xlen(self.stream_key)
                    if stream_length > 0:
                        logger.warning(f"Stream에 {stream_length}개 메시지가 있지만 Consumer Group이 읽지 않음. 리셋 시도")
                        self._reset_consumer_group()
                        # 리셋 후 다시 새 메시지 읽기 시도
                        messages = self.redis_client.xreadgroup(
                            groupname=self.consumer_group,
                            consumername=self.consumer_name,
                            streams={self.stream_key: '>'},
                            count=count,
                            block=0
                        )

            if not messages:
                logger.debug("처리할 메시지가 없음 (새 메시지 및 Pending 메시지 모두 없음)")
                return []

            return self._process_messages(messages)

        except Exception as e:
            logger.error(f"메시지 읽기 중 오류: {str(e)}")
            return []

    def _process_messages(self, messages: List) -> List[Dict[str, Any]]:
        """
        읽어온 메시지를 파싱하고 처리합니다.

        Args:
            messages: Redis에서 읽어온 원시 메시지들

        Returns:
            처리된 메시지 리스트
        """
        result = []
        for stream_name, stream_messages in messages:
            for record_id, data in stream_messages:
                try:
                    # 불필요한 따옴표 제거
                    for key in data:
                        if isinstance(data[key], str):
                            data[key] = data[key].strip('"')

                    # Pydantic 모델로 변환
                    message = RedisStreamMessage(**data)
                    result.append({
                        "id": record_id,
                        "data": message
                    })
                except Exception as e:
                    logger.error(f"메시지 파싱 실패 (recordId={record_id}): {str(e)}")
                    # 파싱 실패한 메시지는 ACK 처리하여 재처리 방지
                    self.acknowledge_message(record_id)

        if result:
            logger.info(f"Redis Stream에서 {len(result)}개 메시지 읽음")

        return result

    def _handle_pending_messages(self, count: int) -> List:
        """
        Pending 메시지를 처리합니다.
        (실패한 Consumer가 남긴 메시지 재처리)

        Args:
            count: 처리할 메시지 수

        Returns:
            재할당된 메시지 리스트
        """
        try:
            # Pending 메시지 확인
            pending_summary = self.redis_client.xpending(
                self.stream_key,
                self.consumer_group
            )

            if not pending_summary or pending_summary.get('pending', 0) == 0:
                return []

            logger.info(f"Pending 메시지 {pending_summary['pending']}개 발견")

            # 오래된 Pending 메시지들을 가져옴 (60초 이상 처리되지 않은 메시지)
            MIN_IDLE_TIME = 60000  # 60초
            pending_messages = self.redis_client.xpending_range(
                name=self.stream_key,
                groupname=self.consumer_group,
                min='-',
                max='+',
                count=count,
                consumername=None  # 모든 컨슈머의 Pending 메시지
            )

            # 오래된 Pending 메시지만 필터링
            stale_messages = [
                msg for msg in pending_messages
                if msg['time_since_delivered'] >= MIN_IDLE_TIME
            ]

            if not stale_messages:
                logger.debug(f"재처리가 필요한 오래된 Pending 메시지 없음 (idle time < {MIN_IDLE_TIME}ms)")
                return []

            # 오래된 메시지들을 현재 컨슈머로 재할당
            message_ids = [msg['message_id'] for msg in stale_messages]
            claimed_messages = self.redis_client.xclaim(
                name=self.stream_key,
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                min_idle_time=MIN_IDLE_TIME,
                message_ids=message_ids
            )

            if claimed_messages:
                logger.info(f"{len(claimed_messages)}개의 오래된 Pending 메시지를 재할당하여 처리")
                # xclaim의 결과를 xreadgroup 형식으로 변환
                return [(self.stream_key, claimed_messages)]

            return []

        except Exception as e:
            logger.error(f"Pending 메시지 처리 중 오류: {str(e)}")
            return []

    def acknowledge_message(self, record_id: str):
        """
        메시지 처리 완료를 확인(ACK)합니다.

        Args:
            record_id: 메시지 ID
        """
        try:
            if not self.redis_client:
                raise RuntimeError("Redis가 연결되지 않았습니다")

            self.redis_client.xack(
                self.stream_key,
                self.consumer_group,
                record_id
            )
            logger.debug(f"메시지 ACK 완료: {record_id}")

        except Exception as e:
            logger.error(f"메시지 ACK 실패 (recordId={record_id}): {str(e)}")

    def get_consumer_group_info(self) -> Dict[str, Any]:
        """
        Consumer Group의 상태 정보를 조회합니다.

        Returns:
            Consumer Group 정보 딕셔너리
        """
        try:
            if not self.redis_client:
                raise RuntimeError("Redis가 연결되지 않았습니다")

            groups = self.redis_client.xinfo_groups(self.stream_key)

            for group in groups:
                if group['name'] == self.consumer_group:
                    return {
                        "name": group['name'],
                        "consumers": group.get('consumers', 0),
                        "pending": group.get('pending', 0),
                        "last_delivered_id": group.get('last-delivered-id'),
                        "entries_read": group.get('entries-read', 0),
                        "lag": group.get('lag', 0)  # 처리되지 않은 메시지 수
                    }

            return {}

        except Exception as e:
            logger.error(f"Consumer Group 정보 조회 중 오류: {str(e)}")
            return {}

    def _reset_consumer_group(self):
        """Consumer Group을 리셋합니다 (삭제 후 재생성)"""
        try:
            if not self.redis_client:
                raise RuntimeError("Redis가 연결되지 않았습니다")

            # Consumer Group 삭제
            self.redis_client.xgroup_destroy(self.stream_key, self.consumer_group)
            logger.info(f"Consumer Group 삭제: {self.consumer_group}")

            # Consumer Group 재생성
            self.redis_client.xgroup_create(
                name=self.stream_key,
                groupname=self.consumer_group,
                id='$',  # 새로운 메시지부터 읽기
                mkstream=True
            )
            logger.info(f"Consumer Group 재생성: {self.consumer_group}")

        except Exception as e:
            logger.error(f"Consumer Group 리셋 중 오류: {str(e)}")


# 전역 Keyword Redis Consumer 인스턴스
keyword_redis_consumer = KeywordRedisConsumer()
