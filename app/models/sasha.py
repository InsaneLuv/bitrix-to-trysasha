import enum
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class SashaBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )


class CallbackTiming(SashaBase):
    max_attempts: int
    retry_delay: int


class WorkingHours(SashaBase):
    end: str
    start: str
    work_days: list[int]


class CallListSettings(SashaBase):
    call_map_type: str
    callback_timing: CallbackTiming
    consider_subscriber_timezone: bool
    skillbase_name: str
    working_hours: list[WorkingHours]


class CallList(SashaBase):
    communication_channels: list[Any] = []
    created_at: datetime
    deleted: bool
    id: str
    name: str
    organization: Any | None = None
    phones: list[Any] = []
    settings: CallListSettings
    status: str
    updated_at: datetime


class DealFieldsEnum(enum.StrEnum):
    sqm = "UF_CRM_668D021E4CCFE"
    width = "UF_CRM_1720783729"
    length = "UF_CRM_1720783739"
    height = "UF_CRM_1720783750"
    region = "UF_CRM_628B829FDFAED"

    interaction = "UF_CRM_69395837EC62E"  # Комментарий по взаимодействию
    size_anchor = "UF_CRM_693976DF42581"  # Комментарий по размерам объекта
    purpose = "UF_CRM_693976DF51E15"  # Комментарий по назначению
    build_field = "UF_CRM_693976DF60AD2"  # Комментарий по земельному участку
    construct = "UF_CRM_693976DF6ECCA"  # Комментарий по конструктиву
    parameters = "UF_CRM_693976DF7C906"  # Комментарий по техническим параметрам
    other_constructs = "UF_CRM_693976DF89C77"  # Комментарий по ограждающим конструкциям
    roof = "UF_CRM_693976DF9C285"  # Комментарии по кровле
    doors = "UF_CRM_693976DFAB4F7"  # Комментарий по проемам


class LeadFieldsEnum(enum.StrEnum):
    sqm = "UF_CRM_1720170287"
    width = "UF_CRM_1720783603"
    length = "UF_CRM_1720783619"
    height = "UF_CRM_1720783631"
    region = "UF_CRM_1653303699"

    interaction = "UF_CRM_1765365691799"  # Комментарий по взаимодействию
    size_anchor = "UF_CRM_1765365898533"  # Комментарий по размерам объекта
    purpose = "UF_CRM_1765366058980"  # Комментарий по назначению
    build_field = "UF_CRM_1765366115884"  # Комментарий по земельному участку
    construct = "UF_CRM_1765366244236"  # Комментарий по конструктиву
    parameters = "UF_CRM_1765366434141"  # Комментарий по техническим параметрам
    other_constructs = "UF_CRM_1765366513858"  # Комментарий по ограждающим конструкциям
    roof = "UF_CRM_1765366567514"  # Комментарии по кровле
    doors = "UF_CRM_1765366594074"  # Комментарий по проемам


class LeadTransfer(BaseModel):
    data: Any | None = "{}"
    data_2: Any | None = "{}"
    data_3: Any | None = "{}"
    data_4: Any | None = "{}"
    data_5: Any | None = "{}"

    all_data: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @model_validator(mode='after')
    def parse_json_and_combine_data(self) -> 'LeadTransfer':
        """Парсит JSON строки и объединяет все данные в all_data"""

        # Словарь для хранения всех данных
        combined_data = {}

        # Обрабатываем каждое поле, содержащее JSON строку
        for field_name, field_value in self.model_dump().items():
            # Пропускаем поле all_data
            if field_name == 'all_data':
                continue

            # Преобразуем JSON строку в словарь
            if isinstance(field_value, str) and field_value:
                try:
                    parsed_data = json.loads(field_value)
                    if isinstance(parsed_data, dict):
                        # Обновляем общий словарь
                        combined_data.update(parsed_data)
                        # Также обновляем исходное поле (преобразуем строку в dict)
                        setattr(self, field_name, parsed_data)
                except json.JSONDecodeError:
                    # Если JSON некорректен, оставляем как есть
                    pass

        # Устанавливаем объединенные данные
        self.all_data = combined_data

        return self

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        """Переопределяем dump для включения all_data при сериализации"""
        dump = super().model_dump(*args, **kwargs)
        dump['all_data'] = self.all_data
        return dump



class Agreements(SashaBase):
    model_config = ConfigDict(
        extra='allow',
        alias_generator=to_camel,
        populate_by_name=True
    )

    agreements: str | None = None
    agreements_time: datetime | None = None
    agreements_time_local: datetime | None = None
    client_facts: str | None = None
    client_name: str | None = None
    is_commit: bool
    lead_transfer: LeadTransfer | None = None
    sms_text: str | None = None

    """
    "callback_required" *Если клиент не готов разговаривать сейчас, и/или попросил перезвонить позднее (bool),
    "height": *Высота (int)
    "width": *Ширина (int),
    "lenght": *Длинна  (int),
    "sqm": *Площадь (int),
    "gate_count" *Колво ворот (int),
    "gate_height" *Высота ворот (int),
    "gate_width" *Ширина ворот (int),
    "region": *Регион строительства (str),
    "purpose": *назначение здания(str),
    - "building_type": *Тип помещения (str),
    "insulation_required" *Нужно ли утепление (bool),
    "fundament_required" *Нужен ли фундамент (bool),
    "roof_type": *Тип кровли (str),
    "material_wall": *Материал стен (str),
    "floor_count": *Кол-во этажей (int),
    "device": *установка доп оборудования (краны или другое) (str),
    - "deadline": *Примерные Сроки строительства (str),
    "door_count": *Кол во дверей (int),
    "size_anchor": *К чему привязка размеров. (str),
    "frame_material": *технология каркаса (str),
    "building_count": *колв строений (int),
    """

    def as_fields(self, mode: Literal["deal", "lead"]) -> dict:
        en = DealFieldsEnum if mode == "deal" else LeadFieldsEnum
        tdata = self.lead_transfer.all_data

        height = tdata.get("height")
        width = tdata.get("width")
        lenght = tdata.get("lenght")
        sqm = tdata.get("sqm")
        if not sqm and width and lenght:
            sqm = width * lenght

        # gate_count = tdata.get("gate_count")
        # gate_height = tdata.get("gate_height")
        # gate_width = tdata.get("gate_width")
        # door_count = tdata.get("door_count")

        region = tdata.get("region")
        purpose = tdata.get("purpose")
        insulation_required = tdata.get("insulation_required")
        fundament_required = tdata.get("fundament_required")
        roof_type = tdata.get("roof_type")
        material_wall = tdata.get("material_wall")
        floor_count = tdata.get("floor_count")
        device = tdata.get("device")
        size_anchor = tdata.get("size_anchor")
        frame_material = tdata.get("frame_material")
        building_count = tdata.get("building_count")
        field_exists = tdata.get("field_exists")
        position_summary = tdata.get("position_summary")
        doors_and_others_summary = tdata.get("doors_and_others_summary")
        frame_material_summary = tdata.get("frame_material_summary")
        building_type_summary = tdata.get("building_type_summary")

        fields_to_update = {}

        if self.client_facts:
            fields_to_update[en.interaction] = self.client_facts

        data = []
        if size_anchor:
            data.append(
                size_anchor
            )

        if building_count:
            data.append(
                f"Кол. зданий: {building_count}"
            )
        min_data = []
        if width:
            min_data.append(
                f"Ш: {width}"
            )
        if lenght:
            min_data.append(
                f"Д: {lenght}"
            )
        if height:
            min_data.append(
                f"В: {height}"
            )

        if min_data:
            data.append(
                ", ".join(min_data)
            )

        if sqm:
            data.append(f"м²: {sqm}")

        if data:
            fields_to_update[en.size_anchor] = " | ".join(data)


        data = []
        if purpose:
            data.append(purpose)
        if building_type_summary:
            data.append(building_type_summary)

        fields_to_update[en.purpose] = " | ".join(data)


        data = []
        data.append(
            f"Отопление: {'✅' if insulation_required else '❌'}"
        )
        if material_wall:
            data.append(
                f"Материал стен: {material_wall}"
            )
        fields_to_update[en.other_constructs] = " | ".join(data)


        data = []
        data.append(
            f"Наличие участка: {"✅" if field_exists else "❌"}"
        )
        data.append(
            f"Требуется фундамент: {"✅" if fundament_required else "❌"}"
        )
        if position_summary:
            data.append(
                f"Расположение: {position_summary}"
            )
        if region:
            data.append(
                f"Регион: {region}"
            )
        fields_to_update[en.build_field] = " | ".join(data)

        data = []
        if frame_material:
            data.append(
                f"Каркас: {frame_material}"
            )
        if frame_material_summary:
            data.append(
                frame_material_summary
            )
        if data:
            fields_to_update[en.construct] = " | ".join(data)

        data = []
        if floor_count:
            data.append(
                f"Этажность: {floor_count}"
            )
        if device:
            data.append(
                f"Допы: {device}"
            )
        if data:
            fields_to_update[en.parameters] = " | ".join(data)

        if roof_type:
            fields_to_update[en.roof] = f"Кровля: {roof_type}"

        if doors_and_others_summary:
            fields_to_update[en.doors] = doors_and_others_summary


        return fields_to_update


class ChatMessage(SashaBase):
    content: str
    role: str


class CallDetails(SashaBase):
    channel_id: str
    chat_history: list[ChatMessage]
    destination_phone: str
    from_phone: str | None = Field(default=None, alias="from")
    to_phone: str | None = Field(default=None,alias="to")

    def history_as_string(self):
        history_str = ""
        user_emoji, bot_emoji = "😎", "🤖"
        for item in self.chat_history:
            role = item.role
            if role and role == "user":
                history_str += f"{user_emoji}: {item.content}\n"
            else:
                history_str += f"{bot_emoji}: {item.content}\n"
        return history_str


class Contact(SashaBase):
    additional_fields: dict
    blacklist: bool
    call_list: CallList
    call_sessions: list[Any] = []
    created_at: datetime
    created_by_user_id: str
    id: str
    is_deleted: bool
    phone: str
    tags: list[str]
    updated_at: datetime

    @property
    def deal_id(self) -> str:
        return self.additional_fields.get("deal_id")

    @property
    def lead_id(self) -> str:
        return self.additional_fields.get("lead_id")

    @property
    def title(self) -> str:
        return self.additional_fields.get("title")

    @property
    def bitrix_url(self) -> str:
        return f"https://aaaeuroangar.bitrix24.ru/crm/deal/details/{self.deal_id}/" if self.deal_id else f"https://aaaeuroangar.bitrix24.ru/crm/lead/details/{self.lead_id}/"


class CallSession(SashaBase):
    attempts: int
    attempts_left: int
    calls: list[Any] = []
    contact: Contact
    created_at: datetime
    id: str
    status: str
    updated_at: datetime


class Call(SashaBase):
    agreements: Agreements
    call_details: CallDetails
    call_session: CallSession
    connected_at: datetime | None = None
    created_at: datetime
    ended_at: datetime | None = None
    hangup_reason: str
    id: str
    record_url: str | None = None
    started_at: datetime
    status: str
    type: str
    updated_at: datetime


class CallResultEvent(SashaBase):
    call: Call
    contact: Contact
    id: str
    timestamp: datetime
