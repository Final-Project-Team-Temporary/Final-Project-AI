"""
공통 테스트 픽스처 및 환경 설정.

실제 외부 서비스(Gemini API, ChromaDB, MongoDB, YouTube API)를 사용하지 않도록
환경변수를 테스트용 더미값으로 고정하고, 초기화 시 네트워크 호출하는 클라이언트는 mock한다.
"""

import pytest
import os
from unittest.mock import MagicMock, patch

# YouTube API: build()는 discovery 문서를 네트워크에서 가져오므로 테스트 시 mock 필요
# app.main 임포트 전에 패치해야 YouTubeClient.__init__ 호출을 막을 수 있다
_youtube_mock = patch(
    "googleapiclient.discovery.build",
    return_value=MagicMock()
)
_youtube_mock.start()

# 테스트 실행 전 환경변수를 더미값으로 설정
# 실제 API 호출 없이 mock만으로 테스트 가능하게 함
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("YOUTUBE_API_KEY", "test-youtube-key")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DATABASE", "econoeasy_test")
os.environ.setdefault("MONGO_AUTHENTICATION_DATABASE", "admin")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_USE_TLS", "False")
os.environ.setdefault("REDIS_SSL_CERT_REQS", "none")
os.environ.setdefault("REDIS_STREAM_KEY", "test-stream")
os.environ.setdefault("REDIS_CONSUMER_GROUP", "test-group")
os.environ.setdefault("REDIS_CONSUMER_NAME", "test-worker")
os.environ.setdefault("REDIS_RECOMMEND_STREAM_KEY", "test-recommend-stream")
os.environ.setdefault("REDIS_RECOMMEND_RESULT_STREAM_KEY", "test-recommend-result-stream")
os.environ.setdefault("REDIS_RECOMMEND_CONSUMER_GROUP", "test-recommend-group")
os.environ.setdefault("REDIS_RECOMMEND_CONSUMER_NAME", "test-recommend-worker")
os.environ.setdefault("REDIS_KEYWORD_STREAM_KEY", "test-keyword-stream")
os.environ.setdefault("REDIS_KEYWORD_RESULT_STREAM_KEY", "test-keyword-result-stream")
os.environ.setdefault("REDIS_KEYWORD_CONSUMER_GROUP", "test-keyword-group")
os.environ.setdefault("REDIS_KEYWORD_CONSUMER_NAME", "test-keyword-worker")
os.environ.setdefault("REDIS_DEDUP_KEY", "test-dedup")
os.environ.setdefault("EMBEDDING_MODEL", "models/text-embedding-004")
os.environ.setdefault("CHROMA_HOST", "localhost")
os.environ.setdefault("CHROMA_PORT", "8001")
os.environ.setdefault("CHROMA_COLLECTION_NAME", "test_articles")
os.environ.setdefault("RAG_TOP_K", "5")
os.environ.setdefault("RAG_MIN_SCORE", "0.4")
