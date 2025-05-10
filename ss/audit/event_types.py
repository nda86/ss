from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Type, Optional

from jinja2 import Template

# from conf.ss import AUDIT_SOURCE_NAME
# from core.utils.helpers import EnvDict
from ss.audit.audit_types import AuditEventClass


AUDIT_SOURCE_NAME = "TEST_AUDIT"


class EnvDict(dict):
    def __getitem__(self, key):
        return os.getenv(key)

    def __setitem__(self, key, value):
        raise NotImplementedError()


class EventTypeRegistry:
    __EVENTS: list[Type[BaseEventType]] = []

    @classmethod
    def registry(cls, type_: Type[BaseEventType]):
        cls.__EVENTS.append(type_)

    @classmethod
    def all(cls) -> list[Type[BaseEventType]]:
        return cls.__EVENTS

    @classmethod
    def all_json(cls) -> list[dict[str, Any]]:
        return [event_type.audit_admin_message() for event_type in cls.__EVENTS]


@dataclass
class AuditClass:
    title: str
    class_: str


@dataclass
class BaseEventType:
    """
    Базовый класс для типа аудита
    """

    title: str
    code: str
    type: str
    business_object: str
    business_operation: str
    info_system_code: str = os.getenv("INFO_SYSTEM_CODE", "TBCA")
    classes: list[AuditClass] = field(default_factory=list)

    payload_override: dict[str, Any] = field(default_factory=dict)
    object_ref: str = ""
    success_message_tpl: str = ""
    failure_message_tpl: str = ""
    error: Optional[Any] = None

    def __init_subclass__(cls, **kwargs):
        EventTypeRegistry.registry(cls)

    def _render(self, tpl: str) -> str:
        return Template(tpl).render(
            this=self,
            error=self.error,
            env=EnvDict(),
        )

    @property
    def message(self) -> str:
        return self._render(self.success_message_tpl) if not self.error else self._render(self.failure_message_tpl)

    @property
    def pk(self):
        return self.payload_override.get("pk", None)

    @classmethod
    def audit_admin_message(cls):
        return {
            "code": cls.code,
            "type": cls.type,
            "businessObject": cls.business_object,
            "businessOperation": cls.business_operation,
            "infoSystemCode": cls.info_system_code,
            "classes": [{"title": cls.title, "class": stage.value} for stage in AuditEventClass],
        }


@dataclass
class UserLoginEventType(BaseEventType):
    title: str = "Вход пользователя"
    code: str = f"{AUDIT_SOURCE_NAME}_USER_LOGIN"
    type: str = "Логин"
    business_object: str = "Пользовательская сессия"
    business_operation: str = "Вход пользователя"

    success_message_tpl: str = "Вход пользователя (Login={{this.pk}})"
    failure_message_tpl: str = "Вход пользователя (Login={{this.pk}}) завершен с ошибкой: {{ error | pprint }}"
