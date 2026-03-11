from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.core.config import get_settings
from app.services.ai_analysis import AIAnalysisService
from app.services.news_ingestion import NewsIngestionService
from app.services.papago_translation import PapagoTranslationService


async def run_collect_news_job(app: FastAPI) -> None:
    database = getattr(app.state, "database", None)
    if database is None:
        return
    await NewsIngestionService(database).collect_latest_news()


async def run_translate_news_job(app: FastAPI) -> None:
    database = getattr(app.state, "database", None)
    if database is None:
        return
    await PapagoTranslationService(database).translate_pending_articles()


async def run_generate_ai_job(app: FastAPI) -> None:
    database = getattr(app.state, "database", None)
    if database is None:
        return
    await AIAnalysisService(database).generate_pending_analyses()


async def run_cleanup_news_job(app: FastAPI) -> None:
    database = getattr(app.state, "database", None)
    if database is None:
        return
    await NewsIngestionService(database).cleanup_old_news()


def create_scheduler(app: FastAPI) -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
    scheduler.add_job(run_collect_news_job, "interval", minutes=10, kwargs={"app": app}, id="collect_news_job", replace_existing=True)
    scheduler.add_job(run_translate_news_job, "interval", minutes=10, kwargs={"app": app}, id="translate_news_job", replace_existing=True)
    scheduler.add_job(run_generate_ai_job, "interval", minutes=15, kwargs={"app": app}, id="generate_ai_analysis_job", replace_existing=True)
    scheduler.add_job(run_cleanup_news_job, "cron", hour=3, minute=0, kwargs={"app": app}, id="cleanup_old_news_job", replace_existing=True)
    return scheduler
