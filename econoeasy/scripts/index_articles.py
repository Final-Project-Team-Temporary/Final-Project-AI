"""
[역할] MongoDB의 기존 articles를 ChromaDB에 일괄 인덱싱하는 배치 스크립트.

RAG 기능을 처음 켤 때 또는 ChromaDB 데이터가 초기화됐을 때 1회 실행.
이후 신규 기사는 기사 요약 워커(queue/worker.py)가 처리 후 자동 인덱싱하면 됨.

실행:
    cd econoeasy
    python -m scripts.index_articles

옵션:
    --limit N     : 처음 N개만 인덱싱 (기본: 전체)
    --batch N     : 한 번에 처리할 개수 (기본: 50)
    --dry-run     : 실제 인덱싱 없이 조회만 (테스트용)
"""

import asyncio
import argparse
import logging
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.services.rag.rag_service import RAGService
from app.services.rag.embedding_service import EmbeddingService
from app.services.rag.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def run(limit: int | None, batch_size: int, dry_run: bool):
    logger.info("=" * 50)
    logger.info("RAG 기사 일괄 인덱싱 시작")
    logger.info(f"  MongoDB  : {settings.MONGO_URI}")
    logger.info(f"  ChromaDB : {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
    logger.info(f"  컬렉션    : {settings.CHROMA_COLLECTION_NAME}")
    logger.info(f"  limit    : {limit or '전체'}")
    logger.info(f"  dry-run  : {dry_run}")
    logger.info("=" * 50)

    # ── 서비스 초기화 ─────────────────────────────────────
    embedding_svc = EmbeddingService()
    vector_store = VectorStore()
    rag_svc = RAGService(embedding_service=embedding_svc, vector_store=vector_store)

    # ── MongoDB 연결 ──────────────────────────────────────
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DATABASE]
    articles_col = db["articles"]

    # 전체 기사 수 확인
    total = await articles_col.count_documents({})
    target = min(total, limit) if limit else total
    logger.info(f"MongoDB 기사 총 {total}개 → 이번 실행 대상: {target}개")

    if dry_run:
        logger.info("[dry-run] 실제 인덱싱 없이 종료합니다.")
        client.close()
        return

    # ── 배치 처리 ─────────────────────────────────────────
    cursor = articles_col.find({}, {"_id": 1, "title": 1, "content": 1, "publishedAt": 1, "url": 1})
    if limit:
        cursor = cursor.limit(limit)

    success = 0
    skip = 0
    errors = 0

    batch = []
    async for doc in cursor:
        batch.append(doc)
        if len(batch) >= batch_size:
            s, sk, e = await _process_batch(rag_svc, batch)
            success += s; skip += sk; errors += e
            batch.clear()
            logger.info(f"  진행: {success + skip + errors}/{target} (성공={success}, 스킵={skip}, 오류={errors})")

    # 나머지 배치
    if batch:
        s, sk, e = await _process_batch(rag_svc, batch)
        success += s; skip += sk; errors += e

    client.close()
    logger.info("=" * 50)
    logger.info(f"완료: 성공={success}, 스킵(빈본문)={skip}, 오류={errors}")
    logger.info("=" * 50)


async def _process_batch(rag_svc: RAGService, docs: list) -> tuple[int, int, int]:
    success = skip = errors = 0
    for doc in docs:
        article_id = str(doc["_id"])
        title = doc.get("title", "")
        content = doc.get("content", "")
        published_at = str(doc.get("publishedAt", ""))
        url = doc.get("url", "")

        if not content or not content.strip():
            logger.debug(f"  스킵 (빈 본문): {article_id}")
            skip += 1
            continue

        try:
            await rag_svc.index_article(
                article_id=article_id,
                title=title,
                content=content,
                published_at=published_at,
                url=url,
            )
            logger.debug(f"  인덱싱 완료: {article_id} - {title[:40]}")
            success += 1
        except Exception as e:
            logger.warning(f"  인덱싱 실패: {article_id} - {e}")
            errors += 1

    return success, skip, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MongoDB 기사를 ChromaDB에 일괄 인덱싱")
    parser.add_argument("--limit", type=int, default=None, help="최대 인덱싱 개수")
    parser.add_argument("--batch", type=int, default=50, help="배치 크기 (기본 50)")
    parser.add_argument("--dry-run", action="store_true", help="조회만 하고 인덱싱 안 함")
    args = parser.parse_args()

    asyncio.run(run(limit=args.limit, batch_size=args.batch, dry_run=args.dry_run))
