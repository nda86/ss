import inspect
from functools import wraps

from ss.audit.audit_types import AuditEventClass
from ss.audit.emitters import emit_audit_event_async, emit_audit_event_sync
from ss.audit.event_types import EventTypeRegistry
from ss.audit.utils import make_audit_context


def audit_event(event_type_str: str):
    def decorator(func):
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            event_type = EventTypeRegistry.get_by_title(event_type_str)
            if event_type is None:
                return await func(*args, **kwargs)
            context = make_audit_context()
            try:
                await emit_audit_event_async(AuditEventClass.START, event_type, context)
                result = await func(*args, **kwargs)
                await emit_audit_event_async(AuditEventClass.SUCCESS, event_type, context)
                return result
            except Exception as e:
                await emit_audit_event_async(AuditEventClass.FAILURE, event_type, context, error=e)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            event_type = EventTypeRegistry.get_by_title(event_type_str)
            if event_type is None:
                return func(*args, **kwargs)
            context = make_audit_context()
            try:
                emit_audit_event_sync(AuditEventClass.START, event_type, context)
                result = func(*args, **kwargs)
                emit_audit_event_sync(AuditEventClass.SUCCESS, context)
                return result
            except Exception as e:
                emit_audit_event_sync(AuditEventClass.FAILURE, context, error=e)
                raise

        return async_wrapper if is_async else sync_wrapper

    return decorator
