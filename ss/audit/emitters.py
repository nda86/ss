import itertools
import json
import os
from typing import Iterable, Generator, TypeVar, Type

from ss.audit.audit_types import AuditEventClass, AuditContext
from ss.audit.event_types import EventTypeRegistry, BaseEventType
from ss.audit.transport import BaseAuditTransport
from ss.audit.utils import make_audit_event
from ss.di import inject

T = TypeVar("T")


def chunked_iterable(iterable: Iterable[T], n: int) -> Generator[list[T], None, None]:
    it = iter(iterable)
    while chunk := list(itertools.islice(it, n)):
        yield chunk


@inject
def emit_audit_catalog_sync(transport: BaseAuditTransport):
    CHUNK_SIZE = 15

    audit_catalog_fluent_host = os.getenv("AUDIT_CATALOG_FLUENT_HOST", "localhost")
    audit_catalog_fluent_port = int(os.getenv("AUDIT_CATALOG_FLUENT_PORT", 5170))

    source: str = os.getenv("AUDIT_SOURCE_NAME", "TBCV_OMDA")
    version: str = "1.0.0.0"

    event_type_registry = EventTypeRegistry()
    event_types = event_type_registry.all_json()
    for events_to_send in chunked_iterable(event_types, CHUNK_SIZE):
        audit_message = json.dumps(
            {"source": source, "version": version, "events": events_to_send},
            ensure_ascii=False,
            indent=4,
        )
        transport.send_sync(audit_message, host=audit_catalog_fluent_host, port=audit_catalog_fluent_port)


@inject
async def emit_audit_catalog_async(transport: BaseAuditTransport):
    CHUNK_SIZE = 15

    audit_catalog_fluent_host = os.getenv("AUDIT_CATALOG_FLUENT_HOST", "localhost")
    audit_catalog_fluent_port = int(os.getenv("AUDIT_CATALOG_FLUENT_PORT", 5170))

    source: str = os.getenv("AUDIT_SOURCE_NAME", "TBCV_OMDA")
    version: str = "1.0.0.0"

    event_type_registry = EventTypeRegistry()
    event_types = event_type_registry.all_json()
    for events_to_send in chunked_iterable(event_types, CHUNK_SIZE):
        audit_message = json.dumps(
            {"source": source, "version": version, "events": events_to_send},
            ensure_ascii=False,
            indent=4,
        )
        await transport.send_async(audit_message, host=audit_catalog_fluent_host, port=audit_catalog_fluent_port)


@inject
async def emit_audit_event_async(
    event_class: AuditEventClass,
    event_type_class: Type[BaseEventType],
    audit_context: AuditContext,
    transport: BaseAuditTransport,
    error=None,
):

    audit_fluent_host = os.getenv("AUDIT_FLUENT_HOST", "localhost")
    audit_fluent_port = int(os.getenv("AUDIT_FLUENT_PORT", 5170))

    audit_message = make_audit_event(event_class, event_type_class, audit_context, error)

    await transport.send_async(audit_message, host=audit_fluent_host, port=audit_fluent_port)


@inject
def emit_audit_event_sync(
    event_class: AuditEventClass,
    event_type_class: Type[BaseEventType],
    audit_context: AuditContext,
    transport: BaseAuditTransport,
    error=None,
):

    audit_fluent_host = os.getenv("AUDIT_FLUENT_HOST", "localhost")
    audit_fluent_port = int(os.getenv("AUDIT_FLUENT_PORT", 5170))

    audit_message = make_audit_event(event_class, event_type_class, audit_context, error)

    transport.send_sync(audit_message, host=audit_fluent_host, port=audit_fluent_port)
