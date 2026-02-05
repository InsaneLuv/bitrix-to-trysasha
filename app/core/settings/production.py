from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import SettingsConfigDict

from app.core.settings.app import AppSettings


class SashaWebhookStorage(BaseModel):
    default: SecretStr | None = None
    potencial: SecretStr | None = None
    stuck: SecretStr | None = None


class ProdAppSettings(AppSettings):
    model_config = SettingsConfigDict(env_file=".env")

    BITRIX24_WEBHOOK_URL: SecretStr = Field()
    TG_BOT_TOKEN: SecretStr = Field()
    SASHA_WEBHOOK_UUIDS: list[SecretStr] = Field()

    @property
    def sasha_webhooks(self) -> SashaWebhookStorage:
        return SashaWebhookStorage(default=self.SASHA_WEBHOOK_UUIDS[0] if len(self.SASHA_WEBHOOK_UUIDS) > 0 else None,
                                   potencial=self.SASHA_WEBHOOK_UUIDS[1] if len(self.SASHA_WEBHOOK_UUIDS) > 1 else None,
                                   stuck=self.SASHA_WEBHOOK_UUIDS[2] if len(self.SASHA_WEBHOOK_UUIDS) > 2 else None, )
