import httpx
import structlog

from app.core.settings.production import SashaWebhookStorage

logger = structlog.get_logger(service="SashaService")


class SashaService:
    def __init__(self, webhooks: SashaWebhookStorage):
        self.webhooks: SashaWebhookStorage = webhooks
        self.client = httpx.AsyncClient(
            base_url="https://platform.trysasha.ru/api/upload-contacts-integrations/webhook/",
            timeout=120
        )

    async def add_contacts(self, contacts: list[dict], webhook: str):
        logger.info("adding contacts to Sasha", contacts=len(contacts))
        try:
            r = await self.client.post(webhook, json=contacts)
            r.raise_for_status()
            logger.info("Request to platform successfully done", response=r.json())
            return r.json()
        except httpx.HTTPStatusError as e:
            logger.error("Failed to add contacts to Sasha", error=e.response.text)
            raise
        except httpx.RequestError as e:
            logger.error("An error occurred while requesting Sasha API", error=e)
            raise
