import os
import uuid
import datetime

from ss.audit.audit_types import Initiator, AuditContext, Context, DeploymentContext
from ss.audit.event import AuditEvent


def get_user():
    return "undefined"


def create_initiator() -> Initiator:

    return Initiator(
        sub=get_user(),
        channel="internal",
    )


def get_ip():
    return "127.0.0.1"


def get_session_id():
    return "session_id"


def create_context():
    # current_span = trace.get_current_span()
    current_span = None

    if current_span is not None and current_span.get_span_context().is_valid:
        trace_id = current_span.get_span_context().trace_id
        span_id = current_span.get_span_context().span_id
        trace_id_hex = format(trace_id, "032x")
        span_id_hex = format(span_id, "016x")
    else:
        trace_id_hex = "Undefined"
        span_id_hex = "Undefined"
    return Context(
        session_id=get_session_id(),
        url="/",
        method="GET",
        trace_id=trace_id_hex,
        span_id=span_id_hex,
    )


def create_deployment_context() -> DeploymentContext:
    return DeploymentContext(
        namespace=os.getenv("K8S_NAMESPACE", "superset"), pod_name=os.getenv("K8S_POD_NAME", "superset")
    )


def make_audit_context(kwargs: dict = None) -> AuditContext:
    return AuditContext(
        uuid_event=str(uuid.uuid4()),
        initiator=create_initiator(),
        ip_address=get_ip(),
        context=create_context(),
        deployment_context=create_deployment_context(),
    )


def make_audit_event(event_class, event_type_class, audit_context, error):
    event_type = event_type_class()
    event_type.error = error

    return AuditEvent(
        timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        version="1.0",
        id=audit_context.uuid_event,
        # from EventType
        correlation_id=event_type.correlation_id,
        type=event_type.type,
        code=event_type.code,
        title=event_type.title,
        message=event_type.message,
        operation=event_type.business_operation,
        object=event_type.object,
        initiator=audit_context.initiator,
        ip_address=audit_context.ip_address,
        context=audit_context.context,
        deployment_context=audit_context.deployment_context,
        mandatory=True,
        info_system_code=os.getenv("INFO_SYSTEM_CODE", "INFO_SYSTEM_CODE"),
        info_system_id=os.getenv("INFO_SYSTEM_ID", "INFO_SYSTEM_ID"),
        class_=event_class,
        # additional_params: Optional[AdditionalParams]
        # scm_category: Optional[SCMCategory]
        # ip_nearby_node: Optional[str]
        # ip_recipient: Optional[str]
    ).model_dump_json()
