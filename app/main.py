import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import close_database, connect_database, ensure_indexes
from app.core.exceptions import AppError
from app.core.responses import error_response
from app.core.scheduler import create_scheduler, run_collect_news_job, run_generate_ai_job, run_translate_news_job
from app.core.session import SessionMiddleware
from app.routers.news_api import router as news_api_router
from app.routers.pages import router as pages_router
from app.routers.saved_api import router as saved_api_router


async def _run_startup_jobs(app: FastAPI) -> None:
    try:
        await run_collect_news_job(app)
    except Exception:
        pass

    try:
        await run_translate_news_job(app)
    except Exception:
        pass

    try:
        await run_generate_ai_job(app)
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    database = await connect_database()
    app.state.database = database

    try:
        await ensure_indexes(database)
    except Exception:
        pass

    scheduler = create_scheduler(app)
    app.state.scheduler = scheduler
    scheduler.start()

    startup_task = asyncio.create_task(_run_startup_jobs(app))
    app.state.startup_task = startup_task

    yield

    try:
        startup_task.cancel()
    except Exception:
        pass

    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass
    await close_database()


app = FastAPI(title="Global Issue Map", lifespan=lifespan)
app.add_middleware(SessionMiddleware)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages_router)
app.include_router(news_api_router)
app.include_router(saved_api_router)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return error_response(exc.status_code, exc.message, exc.error_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    message = exc.errors()[0].get("msg", "잘못된 요청입니다.") if exc.errors() else "잘못된 요청입니다."
    return error_response(400, message, "VALIDATION_ERROR")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, _: Exception):
    if request.url.path.startswith("/api/"):
        return error_response(500, "서버 내부 오류가 발생했습니다.", "INTERNAL_ERROR")
    return HTMLResponse("서버 내부 오류가 발생했습니다.", status_code=500)
