from datetime import datetime, timedelta, UTC

from fast_bitrix24 import BitrixAsync

from app.models.sasha import DealFieldsEnum, LeadFieldsEnum
from app.services.sasha import SashaService
import structlog

logger = structlog.get_logger()

class BitrixService:
    def __init__(
            self,
            sasha: SashaService,
            bitrix: BitrixAsync,
    ):
        self.bitrix = bitrix
        self.sasha = sasha

        self.raw_sources = (
            "Сайт", "Реклама", "CRM-форма", "Квиз", "Яндекс Директ", "Авито", "Таргетированная реклама",
            "Социальные сети",
        )

        self.raw_potencial_sources = (
            "Скан", "Скан KZ", "Обзвон базы ИИ", "Обзвон базы RUS"
        )

        self.parsed_sources: list[dict] = []

    async def sources(self) -> list[dict]:
        sources = await self.bitrix.get_all('crm.status.list', params=
        {
            'filter': {"filter[ENTITY_ID]": "SOURCE"}
        })
        for status in sources:
            if status["NAME"] in self.raw_sources or status["NAME"] in self.raw_potencial_sources:
                parsed_source = {
                    "name": status["NAME"],
                    "id": status["STATUS_ID"],
                    "is_potencial": True if status["NAME"] in self.raw_potencial_sources else False
                }
                self.parsed_sources.append(parsed_source)
        return self.parsed_sources

    async def contact(self, contact_id: str):
        contact = await self.bitrix.get_by_ID('crm.contact.get', [contact_id])
        return contact

    async def load_deals_to_sasha(self, deals: list[dict]):
        # potencial_deals = []
        # general_deals = []
        # for deal in deals:
        #     print(deal)
        #     is_potencial = True if "potencial" in deal.get("tags") else False
        #     if is_potencial:
        #         potencial_deals.append(deal)
        #     else:
        #         general_deals.append(deal)
        #
        skipped_results = []
        # if potencial_deals:
        #     r = await self.sasha.add_contacts(potencial_deals, webhook_id=2)
        #     skipped_results.extend(r.get("skippedPhones", []))
        # if general_deals:
        r = await self.sasha.add_contacts(deals, webhook=self.sasha.webhooks.stuck.get_secret_value())
        skipped_results.extend(r.get("skippedPhones", []))
        #     skipped_results.extend(r.get("skippedPhones", []))
        return skipped_results

    async def deals(self, filters: dict) -> list[dict]:
        deals: list[dict] = await self.bitrix.get_all('crm.deal.list', params=
        {
            'filter': filters,
            "select": [
                "SOURCE_ID",
                "CONTACT_ID",
                "TITLE",
                "UF_CRM_668D021E4CCFE",
                "UF_CRM_1697023059779",
                "UF_CRM_1697023812515",
                "UF_CRM_1720783729",
                "UF_CRM_1720783739",
                "UF_CRM_1720783750",
                "UF_CRM_628B829FDFAED",
                "UF_CRM_671265881185F",
                "PHONE"
            ]
        })
        return deals

    async def move_cold_deals_prepairing(self) -> None:
        """
        Перенос сделок, находящихся более 30 дней в "Ожидании решения" в прогрев.
                        # "@SOURCE_ID": [s["id"] for s in self.parsed_sources],
        :return:
        """
        if not self.parsed_sources:
            await self.sources()
        deals = await self.deals(
            {
                "STAGE_ID": "C20:FINAL_INVOICE",
                "<MOVED_TIME": f"{(datetime.now(tz=UTC) - timedelta(seconds=10)).isoformat()}",
                ">DATE_CREATE": f"{(datetime(2026, 1, 13, tzinfo=UTC)).isoformat()}",
                "=%TITLE": "%test%"
            }
        )
        for deal in deals:

            await self.bitrix.call(
                "crm.timeline.comment.add",
                {
                    "fields": {
                        "ENTITY_ID": deal["ID"],
                        "ENTITY_TYPE": "deal",
                        "COMMENT": 'Сделка перенесена в [B]"Новый прогрев"[/B] так как более [B]30 дней[/B] находится на стадии [B]"Ожидание решения"[/B].',
                    }
                },
            )
            await self.bitrix.call(
                "crm.item.update",
                {
                    "entityTypeId": 2,
                    "id": deal["ID"],
                    "fields": {
                        "STAGE_ID": "C27:NEW",
                        "CATEGORY_ID": "27"
                    },
                },
            )

    async def load_to_sasha(self) -> None:
        deals = await self.deals(
            {
                "STAGE_ID": "C27:NEW",
                "<MOVED_TIME": f"{(datetime.now(tz=UTC) - timedelta(seconds=30)).isoformat()}",
            }
        )
        if not deals:
            return

        datas = []

        to_load = {}

        for deal in deals:
            phone = None
            if deal.get("PHONE") and len(deal.get("PHONE")) > 0:
                phone = deal.get("PHONE")[0].get("VALUE")

            if deal.get("CONTACT_ID") and deal.get("CONTACT_ID") != '0':
                contact = await self.contact(deal.get("CONTACT_ID"))
                phone = contact.get("PHONE")[0].get("VALUE")
                if not contact:
                    continue

            if not phone:
                print(f"Телефон не найден для сделки, {deal}")
                continue

            # potencial = next(
            #     (source["is_potencial"] for source in self.parsed_sources if source["id"] == deal.get("SOURCE_ID")),
            #     False
            # )
            tags = ["Сделка"]
            # if potencial:
            #     tags.append("potencial")

            deal["PHONE"] = phone

            data = {
                "phone": phone,
                "tags": tags,
                "additionalFields": {
                    "deal_id": deal.get("ID"),
                    "title": deal.get("TITLE"),
                    "sqm": deal.get(DealFieldsEnum.sqm, "Не указано"),
                    "width": deal.get(DealFieldsEnum.width, "Не указано"),
                    "length": deal.get(DealFieldsEnum.length, "Не указано"),
                    "height": deal.get(DealFieldsEnum.height, "Не указано"),
                    "region": deal.get(DealFieldsEnum.region, "Не указано"),
                    "building_type": deal.get("UF_CRM_671265881185F", "Не указано"),
                    "insulation_walls": deal.get("UF_CRM_1697023059779", "Не указано"),
                }
            }
            to_load[phone] = deal
            datas.append(data)

        skipped_list = await self.load_deals_to_sasha(
            datas
        )

        for deal in deals:
            await self.bitrix.call(
                "crm.item.update",
                {
                    "entityTypeId": 2,
                    "id": deal["ID"],
                    "fields": {
                        "STAGE_ID": "C27:PREPARATION",
                        "CATEGORY_ID": "27"
                    },
                },
            )

        # for skipped in skipped_list:
        #     skipped_phone = skipped.get("phone")
        #     skipped_reason = skipped.get("reason")
        #     deal_id = to_load[skipped_phone].get("ID")
        #     await self.bitrix.call(
        #         "crm.item.update",
        #         {
        #             "entityTypeId": 2,
        #             "id": deal_id,
        #             "fields": {
        #                 "STAGE_ID": "C27:NEW",
        #                 "CATEGORY_ID": "27"
        #             },
        #         },
        #     )

    async def rollback_frozen_deals(self) -> None:
        deals = await self.deals(
            {
                "STAGE_ID": "C27:PREPARATION",
                "<MOVED_TIME": f"{(datetime.now(tz=UTC) - timedelta(days=1)).isoformat()}",
            }
        )
        if not deals:
            return

        for deal in deals:
            await self.bitrix.call(
                "crm.item.update",
                {
                    "entityTypeId": 2,
                    "id": deal["ID"],
                    "fields": {
                        "STAGE_ID": "C27:NEW",
                        "CATEGORY_ID": "27"
                    },
                },
            )


    async def leads(self, filters: dict) -> list[dict]:
        leads: list[dict] = await self.bitrix.get_all('crm.lead.list', params=
        {
            'filter': filters,
            "select": [
                "SOURCE_ID",
                "CONTACT_ID",
                "PHONE",
                "TITLE",

                "UF_*",
                # "UF_CRM_1653303699", # регион строит,
                # "UF_CRM_1720783603", # ширина,
                # "UF_CRM_1720783619", # длина,
                # "UF_CRM_1720783631", # высота,
                # "UF_CRM_1725886337", # назначение,
                # "UF_CRM_1738307952054" # ориентировачные сроки,
            ]
        })
        return leads

    async def load_leads_to_sasha(self):
        if not self.parsed_sources:
            await self.sources()
        logger.info("load_leads_to_sasha")
        leads = await self.leads(
            {
                "@SOURCE_ID": [s["id"] for s in self.parsed_sources],
                "STATUS_ID": "NEW",
                ">DATE_CREATE": f"{(datetime.now(tz=UTC) - timedelta(days=7)).isoformat()}",
                "=%TITLE": "%test%",
                "UF_CRM_1765365691799": False # ПРОЗВОНИВШИЕ УЖЕ НЕ НАДО
            }
        )
        logger.info(f"{len(leads)} leads can be loaded to sasha")
        datas = []
        potential_datas = []

        for lead in leads:
            phone = None

            if lead.get("PHONE") and len(lead.get("PHONE")) > 0:
                phone = lead.get("PHONE")[0].get("VALUE")

            if lead.get("CONTACT_ID") and lead.get("CONTACT_ID") != '0':
                contact = await self.contact(lead.get("CONTACT_ID"))
                phone = contact.get("PHONE")[0].get("VALUE")
                if not contact:
                    continue

            if not phone:
                print(f"Телефон не найден для лида, {lead}")
                continue
            is_potencial = next(
                (source["is_potencial"] for source in self.parsed_sources if source["id"] == lead.get("SOURCE_ID")),
                False
            )
            tags = ["Лид"]

            data = {
                "phone": phone,
                "tags": tags,
                "additionalFields": {
                    "lead_id": lead.get("ID"),
                    "title": lead.get("TITLE"),
                    "region": lead.get(LeadFieldsEnum.region, "Не указано"),
                    "width": lead.get(LeadFieldsEnum.width, "Не указано"),
                    "length": lead.get(LeadFieldsEnum.length, "Не указано"),
                    "height": lead.get(LeadFieldsEnum.height, "Не указано"),
                    "purpose": lead.get("UF_CRM_1725886337", "Не указано"),
                    "deadline": lead.get("UF_CRM_1738307952054", "Не указано"),
                }
            }
            if is_potencial:
                tags.append("potencial")
                potential_datas.append(data)
            else:
                datas.append(data)

        if datas:
            await self.sasha.add_contacts(datas, webhook=self.sasha.webhooks.default.get_secret_value())

        if potential_datas:
            await self.sasha.add_contacts(potential_datas, webhook=self.sasha.webhooks.potencial.get_secret_value())
