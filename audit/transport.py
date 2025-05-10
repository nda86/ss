from abc import ABC, abstractmethod

from ss.audit.event import AuditEvent
from ss.di import container


class BaseAuditTransport(ABC):
    @abstractmethod
    def send_sync(self, event: AuditEvent):
        raise NotImplementedError

    @abstractmethod
    async def send_async(self, event: AuditEvent):
        raise NotImplementedError


class FluentAuditTransport(BaseAuditTransport):
    def send_sync(self, event: AuditEvent):
        print("sync send via fluent")

    async def send_async(self, event: AuditEvent):
        pass


class KafkaAuditTransport(BaseAuditTransport):
    def send_sync(self, event: AuditEvent):
        print("sync send via kafka")

    async def send_async(self, event: AuditEvent):
        pass


container.bind(BaseAuditTransport, FluentAuditTransport)
