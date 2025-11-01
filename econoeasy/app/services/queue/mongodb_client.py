"""MongoDB 클라이언트"""

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from datetime import datetime
from bson import ObjectId
from ...core.config import settings
from ...models.schemas import ArticleDocument, SummarizedArticle, SummaryOutput, SummaryLevel
import logging

logger = logging.getLogger(__name__)


class MongoDBClient:
    """MongoDB 연결 및 기사 조회를 담당하는 클라이언트"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.articles_collection = None
        self.summarized_articles_collection = None

    async def connect(self):
        """MongoDB 연결"""
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGO_URI,
                authSource=settings.MONGO_AUTHENTICATION_DATABASE
            )
            self.db = self.client[settings.MONGO_DATABASE]
            self.articles_collection = self.db["articles"]
            self.summarized_articles_collection = self.db["summarized_articles"]

            # 연결 테스트
            await self.client.admin.command('ping')
            logger.info("MongoDB 연결 성공")
        except Exception as e:
            logger.error(f"MongoDB 연결 실패: {str(e)}")
            raise

    async def disconnect(self):
        """MongoDB 연결 종료"""
        if self.client:
            self.client.close()
            logger.info("MongoDB 연결 종료")

    async def get_article_by_id(self, article_id: str) -> Optional[ArticleDocument]:
        """
        articleId로 기사를 조회합니다.

        Args:
            article_id: MongoDB의 _id 값

        Returns:
            ArticleDocument 또는 None
        """
        try:
            if self.articles_collection is None:
                raise RuntimeError("MongoDB가 연결되지 않았습니다")

            # MongoDB에서 기사 조회 (ObjectId로 변환)
            try:
                # ObjectId로 변환 시도
                object_id = ObjectId(article_id)
                article_data = await self.articles_collection.find_one({"_id": object_id})
            except Exception:
                # ObjectId 변환 실패 시 문자열로 조회
                article_data = await self.articles_collection.find_one({"_id": article_id})

            if not article_data:
                logger.warning(f"기사를 찾을 수 없습니다: {article_id}")
                return None

            # MongoDB 데이터를 Pydantic 모델에 맞게 변환
            # ObjectId를 문자열로 변환
            if '_id' in article_data:
                article_data['_id'] = str(article_data['_id'])
            
            # datetime을 문자열로 변환
            if 'publishedAt' in article_data and isinstance(article_data['publishedAt'], datetime):
                article_data['publishedAt'] = article_data['publishedAt'].isoformat()

            # Pydantic 모델로 변환
            return ArticleDocument(**article_data)

        except Exception as e:
            logger.error(f"기사 조회 중 오류 발생 (articleId={article_id}): {str(e)}")
            raise

    async def update_summary_status(self, article_id: str, status: str):
        """
        기사의 요약 상태를 업데이트합니다.

        Args:
            article_id: MongoDB의 _id 값
            status: 새로운 상태 (예: PROCESSING, COMPLETED, FAILED)
        """
        try:
            if self.articles_collection is None:
                raise RuntimeError("MongoDB가 연결되지 않았습니다")

            # ObjectId로 변환하여 업데이트
            try:
                object_id = ObjectId(article_id)
                result = await self.articles_collection.update_one(
                    {"_id": object_id},
                    {"$set": {"summaryStatus": status}}
                )
            except Exception:
                # ObjectId 변환 실패 시 문자열로 업데이트
                result = await self.articles_collection.update_one(
                    {"_id": article_id},
                    {"$set": {"summaryStatus": status}}
                )

            if result.modified_count > 0:
                logger.info(f"기사 상태 업데이트 완료: {article_id} -> {status}")
            else:
                logger.warning(f"기사 상태 업데이트 실패 (없거나 동일한 상태): {article_id}")

        except Exception as e:
            logger.error(f"기사 상태 업데이트 중 오류 (articleId={article_id}): {str(e)}")
            raise

    async def save_summary(
        self,
        article_id: str,
        article_title: str,
        published_at: Optional[str],
        summary_output: SummaryOutput
    ):
        """
        요약 결과를 MongoDB summarized_articles 컬렉션에 저장합니다.
        3가지 난이도(EASY, MEDIUM, ADVANCED)를 각각 별도 문서로 저장합니다.

        Args:
            article_id: 원본 기사 ID
            article_title: 기사 제목
            published_at: 기사 발행일
            summary_output: 요약 결과 (3가지 난이도 포함)
        """
        try:
            if self.summarized_articles_collection is None:
                raise RuntimeError("MongoDB가 연결되지 않았습니다")

            summarized_at = datetime.utcnow()

            # 3가지 난이도별로 문서 생성
            summaries_to_insert = []

            # EASY 레벨
            easy_summary = SummarizedArticle(
                originalArticleId=article_id,
                title=article_title,
                summarizedContent=summary_output.easy,
                summaryLevel=SummaryLevel.EASY,
                summarizedAt=summarized_at,
                publishedAt=published_at
            )
            summaries_to_insert.append(easy_summary.model_dump(by_alias=True, exclude={"id"}))

            # MEDIUM 레벨
            medium_summary = SummarizedArticle(
                originalArticleId=article_id,
                title=article_title,
                summarizedContent=summary_output.medium,
                summaryLevel=SummaryLevel.MEDIUM,
                summarizedAt=summarized_at,
                publishedAt=published_at
            )
            summaries_to_insert.append(medium_summary.model_dump(by_alias=True, exclude={"id"}))

            # ADVANCED 레벨
            advanced_summary = SummarizedArticle(
                originalArticleId=article_id,
                title=article_title,
                summarizedContent=summary_output.advanced,
                summaryLevel=SummaryLevel.ADVANCED,
                summarizedAt=summarized_at,
                publishedAt=published_at
            )
            summaries_to_insert.append(advanced_summary.model_dump(by_alias=True, exclude={"id"}))

            # MongoDB에 3개 문서 일괄 삽입
            result = await self.summarized_articles_collection.insert_many(summaries_to_insert)

            logger.info(
                f"요약 결과 저장 완료: articleId={article_id}, "
                f"inserted_ids={len(result.inserted_ids)}"
            )

        except Exception as e:
            logger.error(f"요약 결과 저장 중 오류 (articleId={article_id}): {str(e)}")
            raise


# 전역 MongoDB 클라이언트 인스턴스
mongodb_client = MongoDBClient()
