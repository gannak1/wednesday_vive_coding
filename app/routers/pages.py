from fastapi import APIRouter, Query, Request

from app.core.constants import CATEGORY_LABELS, CATEGORY_ROUTES
from app.core.exceptions import AppError
from app.core.templating import templates
from app.services.news_query_service import NewsQueryService
from app.services.saved_articles_service import SavedArticlesService

router = APIRouter()


def _nav_items() -> list[dict[str, str]]:
    return [
        {"href": "/", "label": "홈"},
        {"href": "/war", "label": "전쟁"},
        {"href": "/economy", "label": "경제"},
        {"href": "/disaster", "label": "자연재해"},
        {"href": "/politics", "label": "정치"},
        {"href": "/my-articles", "label": "나만의 기사"},
    ]


@router.get("/")
async def home_page(request: Request):
    service = NewsQueryService(request.app.state.database)
    home_data = {"map_pins": [], "top_headlines": []}
    load_error = None
    try:
        home_data = await service.get_home_data(continent=None, keyword=None, limit=5)
    except AppError as exc:
        load_error = exc.message
    except Exception:
        load_error = "초기 데이터를 불러오지 못했습니다."

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "page_title": "Global Issue Map",
            "page_name": "home",
            "nav_items": _nav_items(),
            "home_data": home_data,
            "load_error": load_error,
            "page_payload": home_data,
        },
    )


@router.get("/war")
async def war_page(request: Request, continent: str | None = Query(default=None), keyword: str | None = Query(default=None)):
    return await _render_category_page(request, "war", continent, keyword)


@router.get("/economy")
async def economy_page(request: Request, continent: str | None = Query(default=None), keyword: str | None = Query(default=None)):
    return await _render_category_page(request, "economy", continent, keyword)


@router.get("/disaster")
async def disaster_page(request: Request, continent: str | None = Query(default=None), keyword: str | None = Query(default=None)):
    return await _render_category_page(request, "disaster", continent, keyword)


@router.get("/politics")
async def politics_page(request: Request, continent: str | None = Query(default=None), keyword: str | None = Query(default=None)):
    return await _render_category_page(request, "politics", continent, keyword)


@router.get("/my-articles")
async def my_articles_page(request: Request, category: str | None = Query(default=None), continent: str | None = Query(default=None)):
    service = SavedArticlesService(request.app.state.database)
    saved_data = {"articles": []}
    load_error = None
    try:
        saved_data = await service.list_saved_articles(
            session_id=request.state.session_id,
            category=category,
            continent=continent,
            sort="latest",
        )
    except AppError as exc:
        load_error = exc.message
    except Exception:
        load_error = "저장 기사 목록을 불러오지 못했습니다."

    return templates.TemplateResponse(
        "my_articles.html",
        {
            "request": request,
            "page_title": "나만의 기사",
            "page_name": "my-articles",
            "nav_items": _nav_items(),
            "saved_data": saved_data,
            "load_error": load_error,
            "page_payload": saved_data,
        },
    )


async def _render_category_page(
    request: Request,
    category: str,
    continent: str | None,
    keyword: str | None,
):
    service = NewsQueryService(request.app.state.database)
    category_data = {"category": category, "articles": []}
    load_error = None
    try:
        category_data = await service.get_category_data(
            category=category,
            continent=continent,
            keyword=keyword,
            sort="importance",
            limit=50,
        )
    except AppError as exc:
        load_error = exc.message
    except Exception:
        load_error = "카테고리 기사를 불러오지 못했습니다."

    return templates.TemplateResponse(
        "category.html",
        {
            "request": request,
            "page_title": CATEGORY_LABELS[category],
            "page_name": "category",
            "category_key": category,
            "category_label": CATEGORY_LABELS[category],
            "category_route": CATEGORY_ROUTES[category],
            "nav_items": _nav_items(),
            "category_data": category_data,
            "load_error": load_error,
            "page_payload": category_data,
        },
    )
