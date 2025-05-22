from typing import Any, Callable, Optional

from api.v1.schemas import FilterPayload, FilterSource
from core.repositories.filters.filter_config import (
    MAPPING_ROLES_DATA,
    SOURCE_FIELD_MAP,
    unknown_role_filter,
)
from sqlalchemy import CTE, Select, and_, or_, select
from sqlalchemy.orm import aliased


class SqlAlchemyFilterEngine:
    def __init__(self, model, white_list: Optional[list[str]]):
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
        return MAPPING_ROLES_DATA.get(user.role, unknown_role_filter)(self.model, user)

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

    def apply_distinct(
        self, payload: FilterPayload, user, base_stmt: Select | None = None, use_sorting: bool = False
    ) -> Select:
        base_stmt = base_stmt or select(self.model)
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
