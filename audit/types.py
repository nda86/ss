import enum
from typing import Annotated, Union

from pydantic import Field, BaseModel

NotEmptyStr = Annotated[str, Field(min_length=1)]
NotEmptyMessageStr = Annotated[str, Field(min_length=1, max_length=20480)]
NullOrNotEmptyStr = Union[None, Annotated[str, Field(min_length=1)]]


class AuditEventClass(str, enum.Enum):
    START = "START"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class EventObject(BaseModel):
    id: str
    name: str


class Initiator(BaseModel):
    sub: NotEmptyStr
    channel: NotEmptyStr


class Context(BaseModel):
    session_id: str
    url: str
    method: str
    trace_id: str
    span_id: str


class DeploymentContext(BaseModel):
    namespace: NotEmptyStr
    pod_name: NotEmptyStr


class SecurityOfficerDataDef(BaseModel):
    login: NotEmptyStr
    user_id: NotEmptyStr
    user_full_name: NotEmptyStr
    inn: NotEmptyStr
    client_name: NotEmptyStr
    client_id: NotEmptyStr
    account_number: NotEmptyStr
    signature_type: NotEmptyStr
    certificate_number: NotEmptyStr
    document_id: NotEmptyStr
    signature_id: NotEmptyStr
    doc_type: NotEmptyStr
    client_phone_number: NotEmptyStr
    user_phone_number: NotEmptyStr
    device_id: NotEmptyStr


class TechSectionDef(BaseModel):
    codes: list[str]


class SecurityData(BaseModel):
    security_officer_data: SecurityOfficerDataDef


AdditionalParams = Union[None, Annotated[str, Field(max_length=10240)], SecurityData]


class SCMCategory(str, enum.Enum):
    ENTRY_EXIT_OPERATIONS = "ENTRY_EXIT_OPERATIONS"
    ACCOUNT_MANAGEMENT_OPERATIONS = "ACCOUNT_MANAGEMENT_OPERATIONS"
    PRIVILEGES_MANAGEMENT_OPERATIONS = "PRIVILEGES_MANAGEMENT_OPERATIONS"
    SYSTEM_ERRORS = "SYSTEM_ERRORS"
