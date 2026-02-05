import asyncio
from contextlib import asynccontextmanager

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import make_async_container
from dishka.integrations.fastapi import (
    FastapiProvider, setup_dishka,
)
from dishka.integrations.taskiq import FromDishka, inject, setup_dishka as setup_dishka_taskiq, TaskiqProvider
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from taskiq import InMemoryBroker

from app.api.routes.webhooks import router
from app.core.config import get_app_settings
from app.core.providers import NotificationsProvider, ServiceProvider, SettingsProvider
from app.services.bitrix import BitrixService

broker = InMemoryBroker()
scheduler = AsyncIOScheduler()

logger = structlog.get_logger()


@broker.task
@inject
async def move_cold_deals_to_prepairing(bitrix: FromDishka[BitrixService]):
    logger.info("Moving cold deals to prepairing task executed")
    await bitrix.move_cold_deals_prepairing()
    logger.info("Moving cold deals to prepairing task DONE")


@broker.task
@inject
async def load_deals_to_sasha(bitrix: FromDishka[BitrixService]):
    logger.info("Loading DEALS to Sasha task executed")
    await bitrix.load_to_sasha()
    logger.info("Loading DEALS to Sasha task done")


@broker.task
@inject
async def test_task(bitrix: FromDishka[BitrixService], lock: FromDishka[asyncio.Lock]):
    async with lock:
        logger.info("Loading LEADS to Sasha task executed")
        await bitrix.load_leads_to_sasha()
        logger.info("Loading LEADS to Sasha task DONE")

@broker.task
@inject
async def rollback_task(bitrix: FromDishka[BitrixService], lock: FromDishka[asyncio.Lock]):
    logger.info("Rolling back executed")
    await bitrix.rollback_frozen_deals()
    logger.info("Rolling back done")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not broker.is_worker_process:
        await broker.startup()

    scheduler.start()
    scheduler.add_job(move_cold_deals_to_prepairing.kiq, 'interval', seconds=360)
    scheduler.add_job(load_deals_to_sasha.kiq, 'interval', seconds=50)
    await test_task.kiq()
    await rollback_task.kiq()
    scheduler.add_job(test_task.kiq, 'interval', seconds=30)
    scheduler.add_job(rollback_task.kiq, 'interval', seconds=300)

    yield

    if not broker.is_worker_process:
        await broker.shutdown()

    scheduler.shutdown()


def get_application() -> FastAPI:
    settings = get_app_settings()

    application = FastAPI(**settings.fastapi_kwargs, lifespan=lifespan)
    fastapi_container = make_async_container(SettingsProvider(), ServiceProvider(), NotificationsProvider(),
                                             FastapiProvider())
    taskiq_container = make_async_container(SettingsProvider(), ServiceProvider(), TaskiqProvider())
    setup_dishka(container=fastapi_container, app=application)
    setup_dishka_taskiq(container=taskiq_container, broker=broker)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router, prefix=settings.api_prefix)
    return application


app = get_application()

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
