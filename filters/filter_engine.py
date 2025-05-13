from enum import Enum
from typing import Optional, Literal, Callable, Any, Type

from pydantic import BaseModel, model_validator
from sqlalchemy import Select, and_, or_, select, CTE
from sqlalchemy.orm import aliased

from filters.models import Shop


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"


class VoiceStatus(str, Enum):
    NEW = "новая"
    IN_WORK = "в работе"


class User(BaseModel):
    id: int
    name: str
    role: UserRole

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_operator(self) -> bool:
        return self.role == UserRole.OPERATOR


UNKNOWN_ROLE_FILTER = lambda model, user: False


def operator_role_filter(model, user):
    return or_(model.user_id == user.id, and_(model.user_id.is_(None), model.status == VoiceStatus.NEW))


MAPPING_ROLES_DATA = {
    UserRole.ADMIN: lambda model, user: True,
    UserRole.OPERATOR: operator_role_filter,
}


class FilterSource(str, Enum):
    ASSIGMENT_AREA = "Область назначения"
    WORK_AREA = "Рабочая область"


SOURCE_FIELD_MAP = {
    FilterSource.ASSIGMENT_AREA: ("status", [VoiceStatus.NEW]),
    FilterSource.WORK_AREA: ("status", [VoiceStatus.IN_WORK]),
}


class FilterField(BaseModel):
    field: str
    op: Literal["=", "!=", "<", "<=", ">", ">=", "in", "not in", "between", "is_null"]
    value: str

    @model_validator(mode="before")
    @classmethod
    def validate_operator(cls, values):
        op = values.get("op")
        val = values.get("value")
        if op in {"in", "not_in"}:
            if not isinstance(val, (list, tuple)):
                raise ValueError(f"{op} требует список")
            if not val:
                raise ValueError(f"Список значений для '{op}' не может быть пустым")
        if op == "between" and len(val) != 2:
            raise ValueError("between требует 2 значения")
        if op in ("is_null") and not isinstance(val, bool):
            raise ValueError("is_null требует true/false")
        return values


class FilterPayload(BaseModel):
    and_: list[FilterField] = []
    or_: list[FilterField] = []
    source: FilterSource | None = None
    order_by: str | None = None
    order_direction: Literal["asc", "desc"] = "asc"
    distinct_by: str | None = "voice_id"  # TODO: проверить эти поля
    distinct_by_order: str | None = "probability"
    distinct_by_order_direction: Literal["asc", "desc"] = "desc"


class SqlAlchemyFilterEngine:
    def __init__(self, model: Type[Shop], white_list: Optional[list[str]]):
        self.model = model
        self.white_list = white_list or []
        self.operator_map: dict[str, Callable[[Any, Any], Any]] = {
            "=": lambda col, val: col == val,
            "!=": lambda col, val: col != val,
            "<": lambda col, val: col < val,
            ">": lambda col, val: col > val,
            ">=": lambda col, val: col >= val,
            "<=": lambda col, val: col <= val,
            "in": lambda col, val: col.in_(val),
            "not_in": lambda col, val: ~col.in_(val),
            "is_null": lambda col, val: col.is_(None) if val else col.is_not(None),
            "between": lambda col, val: col.between(val[0], val[1]),
        }

    def _build_conditions(self, payload: FilterPayload):
        and_clauses = list(filter(None, [self._build_clause(f) for f in payload.and_ if f.field in self.white_list]))
        or_clauses = list(filter(None, [self._build_clause(f) for f in payload.or_ if f.field in self.white_list]))
        result = []
        if and_clauses:
            result.append(and_(*and_clauses))
        if or_clauses:
            result.append(or_(*or_clauses))
        return result

    def _build_clause(self, f):
        col = getattr(self.model, f.field)
        op_func = self.operator_map.get(f.op)
        return op_func(col, f.value) if col and op_func else None

    def _role_filter(self, user):
        return MAPPING_ROLES_DATA.get(user.role, UNKNOWN_ROLE_FILTER)(self.model, user)

    def _source_filter(self, source: FilterSource):
        entry = SOURCE_FIELD_MAP.get(source)
        if not entry:
            return False
        field, values = entry
        col = getattr(self.model, field)
        return col.in_(values)

    def build_cte_pipline(self, base_stmt: Select, payload: FilterPayload, user) -> CTE:
        role_filter = self._role_filter(user)
        source_filter = self._source_filter(payload.source)
        voice_filters = self._build_conditions(payload)

        cte_role = base_stmt.where(role_filter).cte("cte_role")
        cte_source = select(cte_role).where(source_filter).cte("cte_source")
        cte_final = select(cte_source).where(*voice_filters).cte("cte_final")
        return cte_final

    def apply_distinct(self, base_stmt: Select, payload: FilterPayload, user, use_sorting: bool = False) -> Select:
        cte = self.build_cte_pipline(base_stmt, payload, user)
        cte_alias = aliased(self.model, cte)
        top_1_subq = (
            select(cte_alias)
            .distinct(getattr(cte_alias, payload.distinct_by))
            .order_by(
                getattr(cte_alias, payload.distinct_by),
                getattr(cte_alias, payload.distinct_by_order).desc(),  # TODO: вынести в фильтр
            )
            .subquery()
        )

        stmt = select(top_1_subq)
        global_order_col = getattr(top_1_subq.c, payload.global_order_by, None)
        if use_sorting and global_order_col:
            stmt = stmt.order_by(
                global_order_col.desc() if payload.global_order_direction == "desc" else global_order_col.asc()
            )

        return stmt
