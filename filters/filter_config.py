from api.v1.schemas import FilterSource
from core.repositories.alchemy.models import StatusChoices, UserRole
from sqlalchemy import and_, or_


def unknown_role_filter():
    return False


def operator_role_filter(model, user):
    return or_(model.user_id == user.id, and_(model.user_id.is_(None), model.status == StatusChoices.NEW))


MAPPING_ROLES_DATA = {
    UserRole.ADMIN: lambda model, user: True,
    UserRole.OPERATOR: operator_role_filter,
}


SOURCE_FIELD_MAP = {
    FilterSource.ASSIGMENT_AREA: ("status", [StatusChoices.NEW]),
    FilterSource.WORK_AREA: ("status", [StatusChoices.IN_PROGRESS]),
}
