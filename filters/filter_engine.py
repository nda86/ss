from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional

from api.v1.schemas import FilterPayload, FilterSource
from core.repositories.filters.filter_config import (
    MAPPING_ROLES_DATA,
    SOURCE_FIELD_MAP,
    unknown_role_filter,
)
from sqlalchemy import Select, and_, or_, select


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

    def _voice_filter(self, payload: FilterPayload):
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

    def _top_filter(self):
        return self.model.is_top.is_(True)

    def _deep_search(self):
        deep_date = datetime.now(timezone.utc) - timedelta(days=30)
        return self.model.created_at >= deep_date

    def build_stmt(self, base_stmt: Select, payload: FilterPayload, user, use_cte) -> Select:
        role_filter = self._role_filter(user)
        source_filter = self._source_filter(payload.source)
        voice_filters = self._voice_filter(payload)
        top_filter = self._top_filter()
        deep_search = self._deep_search()

        if use_cte:
            cte = base_stmt.cte("initial")
            filters = {
                "deep_search": deep_search,
                "role_filter": role_filter,
                "source_filter": source_filter,
                "top_filter": top_filter,
                "voice_filters": and_(*voice_filters) if voice_filters else None,
            }
            for name, conditions in filters:
                if conditions is not None:
                    cte = select(cte).where(conditions).cte(name).prefix_with("NOT MATERIALIZED")
            stmt = select(cte)
        else:
            stmt = base_stmt.where(role_filter, source_filter, *voice_filters, top_filter, deep_search)

        return stmt

    def apply(
        self,
        payload: FilterPayload,
        user,
        base_stmt: Select | None = None,
        use_sorting: bool = False,
        use_cte: bool = True,
    ) -> Select:
        base_stmt = base_stmt or select(self.model)
        stmt = self.build_stmt(base_stmt, payload, user, use_cte)
        global_order_col = getattr(stmt, payload.global_order_by, None)
        if use_sorting and global_order_col:
            stmt = stmt.order_by(
                global_order_col.desc() if payload.global_order_direction == "desc" else global_order_col.asc()
            )

        return stmt
