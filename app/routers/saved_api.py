from fastapi import APIRouter, Query, Request

from app.core.responses import success_response
from app.schemas.request_models import SaveArticleRequest
from app.services.saved_articles_service import SavedArticlesService

router = APIRouter(prefix="/api/articles", tags=["saved-articles"])


@router.post("/save")
async def save_article(request: Request, payload: SaveArticleRequest):
    data = await SavedArticlesService(request.app.state.database).save_article(
        session_id=request.state.session_id,
        article_id=payload.article_id,
    )
    return success_response("기사 저장 성공", data)


@router.get("/saved")
async def list_saved_articles(
    request: Request,
    category: str | None = Query(default=None),
    continent: str | None = Query(default=None),
    sort: str = Query(default="latest"),
):
    data = await SavedArticlesService(request.app.state.database).list_saved_articles(
        session_id=request.state.session_id,
        category=category,
        continent=continent,
        sort=sort,
    )
    return success_response("저장 기사 조회 성공", data)


@router.delete("/saved/{saved_id}")
async def delete_saved_article(request: Request, saved_id: str):
    data = await SavedArticlesService(request.app.state.database).delete_saved_article(
        session_id=request.state.session_id,
        saved_id=saved_id,
    )
    return success_response("저장 기사 삭제 성공", data)
