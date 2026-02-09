import enum
from typing import Any

from aiogram import Bot
from aiogram.utils.formatting import TextLink
from dishka.integrations.fastapi import (
    DishkaRoute, FromDishka
)
from fast_bitrix24 import BitrixAsync
from fastapi import APIRouter

from app.models.sasha import CallResultEvent, DealFieldsEnum

router = APIRouter(route_class=DishkaRoute)



class CallbackTexts:
    """Класс для генерации текстов callback-сообщений."""

    CALL_FAILED = "📞❌ 3 недозвона!"
    CALL_RECALL = "🔔 Попросил перезвонить!"
    CALL_UNSUCCESS = "❌ Неудачный звонок!"
    CALL_SUCCESS = "✅ Успешный прогрев!"

    MESSAGES = {
        'failed': CALL_FAILED,
        'recall': CALL_RECALL,
        'unsuccess': CALL_UNSUCCESS,
        'success': CALL_SUCCESS
    }

    @classmethod
    def format_message(cls, result: CallResultEvent, message_type: str) -> str:
        if message_type not in cls.MESSAGES:
            raise ValueError(f"Unknown message type: {message_type}")

        title = cls.MESSAGES[message_type]
        record_url = result.call.record_url
        bitrix_url = result.contact.bitrix_url
        facts = result.call.agreements.client_facts or ""

        deal_text = "💎 Сделка" if result.contact.deal_id else "🌈 Лид"

        text_parts = [
            title,
            "",
            facts if facts else "(без комментариев)",
            "",
            TextLink("💾 Аудио", url=record_url).as_html(),
            TextLink(deal_text, url=bitrix_url).as_html()
        ]

        return "\n".join(text_parts)

    @classmethod
    def call_failed(cls, result: CallResultEvent):
        return cls.format_message(result, 'failed')

    @classmethod
    def call_recall(cls, result: CallResultEvent):
        return cls.format_message(result, 'recall')

    @classmethod
    def call_unsuccess(cls, result: CallResultEvent):
        return cls.format_message(result, 'unsuccess')

    @classmethod
    def call_success(cls, result: CallResultEvent):
        return cls.format_message(result, 'success')


async def process_deal(result, bot, bitrix):
    facts = result.call.agreements.client_facts
    record_file_url = result.call.record_url
    deal_id = result.contact.deal_id
    title = result.contact.title

    if not deal_id:
        print(
            f"Deal id is not provided, can not update"
        )
        return
    if record_file_url:
        await bitrix.call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT":
                        f"Дата звонка: {result.call.started_at.strftime("%d.%m %H:%M")}\n"
                        f"С номера: {result.call.call_details.from_phone} На: {result.call.call_details.to_phone}\n"
                        f"Аудио: {record_file_url}\n"
                        f"Текст:\n{result.call.call_details.history_as_string()}",
                }
            },
        )

    if result.call.status == "failed":
        session = result.call.call_session

        print(f"Недозвон {session.attempts_left}")

        if session.attempts_left == 0:
            await bot.send_message(
                chat_id="-1003363598566",
                text=CallbackTexts.call_failed(result),
                parse_mode="HTML"
            )
            await bitrix.call(
                "crm.item.update",
                {
                    "entityTypeId": 2,
                    "id": result.contact.deal_id,
                    "fields": {
                        "STAGE_ID": "C27:APOLOGY",
                        "CATEGORY_ID": "27"
                    },
                },
            )
            return
        return

    if result.call.agreements.lead_transfer.all_data.get("callback_required"):
        ftu = {
            "STAGE_ID": "C27:LOSE",
            "CATEGORY_ID": "27",
            DealFieldsEnum.interaction: result.call.agreements.client_facts
        }
        await bot.send_message(
            chat_id="-1003363598566",
            text=CallbackTexts.call_recall(result),
            parse_mode="HTML"
        )
        await bitrix.call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "fields": ftu
            },
        )
        return

    elif not result.call.agreements.is_commit:
        ftu = {
            "STAGE_ID": "C27:APOLOGY",
            "CATEGORY_ID": "27",
            DealFieldsEnum.interaction: result.call.agreements.client_facts
        }
        await bot.send_message(
            chat_id="-1003363598566",
            text=CallbackTexts.call_unsuccess(result),
            parse_mode="HTML"
        )

        await bitrix.call(
            "crm.item.update",
            {
                "entityTypeId": 2,
                "id": deal_id,
                "fields": ftu
            },
        )
        return None

    ftu = {
        "TITLE": "ПРОГРЕВ ВЫПОЛНЕН " + title,
        "STATUS_ID": "C27:WON",
        "CATEGORY_ID": "27",
        DealFieldsEnum.interaction: result.call.agreements.client_facts
    }
    await bitrix.call(
        "crm.deal.update",
        {
            "id": deal_id,
            "fields": ftu,
        },
    )
    await bot.send_message(
        chat_id="-1003363598566",
        text=CallbackTexts.call_success(result),
        parse_mode="HTML"
    )
    return None


async def process_lead(result, bot, bitrix):
    facts = result.call.agreements.client_facts
    record_file_url = result.call.record_url
    lead_id = result.contact.lead_id
    title = result.contact.title

    if not lead_id:
        print(
            f"Lead id is not provided, can not update"
        )
        return
    if record_file_url:
        await bitrix.call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": lead_id,
                    "ENTITY_TYPE": "lead",
                    "COMMENT":
                        f"Дата звонка: {result.call.started_at.strftime("%d.%m %H:%M")}\n"
                        f"С номера: {result.call.call_details.from_phone} На: {result.call.call_details.to_phone}\n"
                        f"Аудио: {record_file_url}\n"
                        f"Текст:\n{result.call.call_details.history_as_string()}",
                }
            },
        )
    if result.call.status == "failed":
        session = result.call.call_session

        print(f"Недозвон {session.attempts_left}")
        if session.attempts_left == 0:
            await bot.send_message(
                chat_id="-1003363598566",
                text=f"❌ 3 недозвона по лиду!\n\n{facts if facts else ""}\n\n{TextLink("Ссылка", url=record_file_url).as_html()}",
                parse_mode="HTML"
            )
            await bitrix.call(
                "crm.lead.update",
                {
                    "id": lead_id,
                    "fields": {
                        "STATUS_ID": "UC_LLR3RD",
                    },
                },
            )
            return
        return

    if result.call.agreements.lead_transfer.all_data.get("callback_required"):
        ftu = result.call.agreements.as_fields(mode="lead")
        ftu["STATUS_ID"] = "UC_LLR3RD"
        await bot.send_message(
            chat_id="-1003363598566",
            text=CallbackTexts.call_recall(result),
            parse_mode="HTML"
        )
        await bitrix.call(
            "crm.lead.update",
            {
                "id": lead_id,
                "fields": ftu,
            },
        )
        return
    elif not result.call.agreements.is_commit:
        await bot.send_message(
            chat_id="-1003363598566",
            text=CallbackTexts.call_failed(result),
            parse_mode="HTML"
        )
        await bitrix.call(
            "crm.lead.update",
            {
                "id": lead_id,
                "fields": {
                    "STATUS_ID": "UC_LLR3RD",

                },
            },
        )
        return

    ftu = result.call.agreements.as_fields(mode="lead")
    ftu["TITLE"] = title
    ftu["STATUS_ID"] = "UC_DT372Z"  # Стадия квалификация, данные заполнены
    await bitrix.call(
        "crm.lead.update",
        {
            "id": lead_id,
            "fields": ftu,
        },
    )

    await bot.send_message(
        chat_id="-1003363598566",
        text=CallbackTexts.call_success(result),
        parse_mode="HTML",
    )
    return None


@router.post("/webhooks/{webhook_id}")
async def _(
        data: dict,
        bot: FromDishka[Bot],
        bitrix: FromDishka[BitrixAsync],
        webhook_id: Any
):
    print(data)
    print("\n\n")
    result = CallResultEvent(**data)
    print(result)
    if result.contact.deal_id:
        await process_deal(result, bot, bitrix)
    else:
        await process_lead(result, bot, bitrix)
    return data
