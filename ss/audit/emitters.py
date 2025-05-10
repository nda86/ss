import itertools
import json
import os
from typing import Iterable, Generator, TypeVar
from ss.audit.event_types import EventTypeRegistry
from ss.audit.transport import BaseAuditTransport
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
