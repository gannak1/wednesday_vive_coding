from fastapi import APIRouter, Query, Request

from app.core.responses import success_response
from app.services.news_query_service import NewsQueryService

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/home")
async def get_home_news(
    request: Request,
    continent: str | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=5, ge=1, le=20),
):
    data = await NewsQueryService(request.app.state.database).get_home_data(continent, keyword, limit)
    return success_response("홈 뉴스 조회 성공", data)


@router.get("/category/{category}")
async def get_category_news(
    request: Request,
    category: str,
    continent: str | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=100),
    sort: str = Query(default="importance"),
    limit: int = Query(default=50, ge=1, le=100),
):
    data = await NewsQueryService(request.app.state.database).get_category_data(category, continent, keyword, sort, limit)
    return success_response("카테고리 뉴스 조회 성공", data)


@router.get("/continent/{continent}")
async def get_continent_news(
    request: Request,
    continent: str,
    category: str | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
):
    data = await NewsQueryService(request.app.state.database).get_continent_data(continent, category, keyword, limit)
    return success_response("대륙별 뉴스 조회 성공", data)


@router.get("/search")
async def search_news(
    request: Request,
    q: str = Query(min_length=1, max_length=100),
    continent: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    page: int = Query(default=1, ge=1),
):
    data = await NewsQueryService(request.app.state.database).search_news(q, continent, category, limit, page)
    return success_response("검색 성공", data)


@router.get("/{article_id}")
async def get_article_detail(request: Request, article_id: str):
    data = await NewsQueryService(request.app.state.database).get_article_detail(article_id)
    return success_response("기사 상세 조회 성공", data)


@router.get("/{article_id}/analysis")
async def get_article_analysis(request: Request, article_id: str):
    data = await NewsQueryService(request.app.state.database).get_article_analysis(article_id)
    return success_response("AI 분석 조회 성공", data)
