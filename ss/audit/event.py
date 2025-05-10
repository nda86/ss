from typing import Optional

from pydantic import BaseModel, AwareDatetime, IPvAnyAddress, Field

from ss.audit.audit_types import (
    EventObject,
    Initiator,
    NotEmptyStr,
    NotEmptyMessageStr,
    Context,
    DeploymentContext,
    AuditEventClass,
    AdditionalParams,
    SCMCategory,
)


class AuditEvent(BaseModel):
    """
    Верхнеуровневый класс события аудита
    """

    timestamp: AwareDatetime
    version: NotEmptyStr = "1.0"
    id: NotEmptyStr

    # from EventType
    correlation_id: NotEmptyStr
    type: NotEmptyStr
    code: NotEmptyStr
    title: NotEmptyStr
    message: NotEmptyMessageStr
    operation: str
    object: EventObject

    initiator: Initiator
    ip_address: IPvAnyAddress
    context: Context
    deployment_context: Optional[DeploymentContext]
    mandatory: bool
    info_system_code: str
    info_system_id: str
    class_: AuditEventClass
    additional_params: Optional[AdditionalParams] = None
    scm_category: Optional[SCMCategory] = None
    ip_nearby_node: Optional[str] = None
    ip_recipient: Optional[str] = None
