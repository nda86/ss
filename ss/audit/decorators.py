import inspect
from functools import wraps

from ss.audit.transport import BaseAuditTransport
from ss.di import inject


@inject
def audit(transport: BaseAuditTransport):
    transport.send_sync(1)


audit()

def audit_event(event_type: str):
    def decorator(func):
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = make_context()
            event = make_event(event_type, context)
            try:
                await emit_audit_event("start", config, context)
                result = await func(*args, **kwargs)
                await emit_audit_event("success", config, context)
                return result
            except Exception as e:
                await emit_audit_event("fail", config, context, error=str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            config = get_audit_config(event_type)
            context = resolve_fields(config.fields, kwargs)
            try:
                emit_audit_event("start", config, context)
                result = func(*args, **kwargs)
                emit_audit_event("success", config, context)
                return result
            except Exception as e:
                emit_audit_event("fail", config, context, error=str(e))
                raise

        return async_wrapper if is_async else sync_wrapper
    return decorator