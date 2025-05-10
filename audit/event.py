from typing import Optional

from pydantic import BaseModel, AwareDatetime, IPvAnyAddress

from ss.audit.types import (
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
    additional_params: Optional[AdditionalParams]
    scm_category: Optional[SCMCategory]
    ip_nearby_node: Optional[str]
    ip_recipient: Optional[str]
