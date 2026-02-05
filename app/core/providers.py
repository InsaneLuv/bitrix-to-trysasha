import asyncio

from aiogram import Bot
from dishka import provide, Provider, Scope
from fast_bitrix24 import BitrixAsync
from pydantic import SecretStr

from app.core.config import get_app_settings
from app.core.settings.production import ProdAppSettings
from app.services.bitrix import BitrixService
from app.services.sasha import SashaService


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ProdAppSettings:
        return get_app_settings()


class NotificationsProvider(Provider):
    @provide(scope=Scope.APP)
    def bot(self, settings: ProdAppSettings) -> Bot:
        return Bot(token=settings.TG_BOT_TOKEN.get_secret_value())


class ServiceProvider(Provider):
    @provide(scope=Scope.APP)
    def bitrix_client(self, settings: ProdAppSettings) -> BitrixAsync:
        webhook_url: SecretStr = settings.BITRIX24_WEBHOOK_URL
        return BitrixAsync(webhook_url.get_secret_value(), verbose=False)

    @provide(scope=Scope.APP)
    def sasha_service(self, settings: ProdAppSettings) -> SashaService:
        return SashaService(
            settings.sasha_webhooks
        )

    @provide(scope=Scope.APP)
    def bitrix_service(self, sasha: SashaService, bitrix: BitrixAsync) -> BitrixService:
        return BitrixService(sasha=sasha, bitrix=bitrix)

    @provide(scope=Scope.APP)
    def lock(self) -> asyncio.Lock:
        return asyncio.Lock()