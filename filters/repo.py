import asyncio

from api.v1.schemas import FilterPayload
from core.models.voice import ApiVoice
from core.repositories.alchemy.db import AsyncSessionLocal
from core.repositories.alchemy.models import SqlCategory, SqlVoice
from core.repositories.base_repository import BaseRepository
from core.repositories.filters.filter_engine import SqlAlchemyFilterEngine
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError


class SqlAlchemyRepository(BaseRepository):
    def __init__(self, db: AsyncSessionLocal):
        self.db = db
        self.voice_model = SqlVoice
        self.category_model = SqlCategory
        self.base_category_stmt = select(SqlCategory)
        if hasattr(self.category_model, "is_active"):
            self.base_category_stmt = self.base_category_stmt.where(self.category_model.is_active == True)

    async def get_all_categories(self) -> list[SqlCategory]:
        result = await self.db.execute(self.base_category_stmt)
        return result.scalars().all()

    async def get_category_by_id(self, _id: str) -> SqlCategory | None:
        stmt = self.base_category_stmt.where(self.category_model.id == _id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_category_levels(self, ids: list[str]) -> list[dict]:
        level_fields = [
            (SqlCategory.level_1_id, SqlCategory.level_1_name),
            (SqlCategory.level_2_id, SqlCategory.level_2_name),
            (SqlCategory.level_3_id, SqlCategory.level_3_name),
            (SqlCategory.level_4_id, SqlCategory.level_4_name),
        ]

        if ids is None or len(ids) > len(level_fields):
            return []

        level = len(ids)
        id_field, name_field = level_fields[level]
        stmt = self.base_category_stmt.with_only_columns(id_field.label("id"), name_field.label("name")).distinct(
            id_field
        )

        for i, id_value in enumerate(ids):
            stmt = stmt.where(level_fields[i][0] == id_value)

        result = await self.db.execute(stmt)
        return result.mappings().all()

    async def save_voices(self, voices: list[SqlVoice]) -> bool:
        try:
            self.db.add_all(voices)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            print(f"Error during bulk insert: {e}")
            return False

    async def get_voices(
        self, filter_payload: FilterPayload, user, limit: int, offset: int
    ) -> tuple[list[ApiVoice], int]:
        filter_engine = SqlAlchemyFilterEngine(model=self.voice_model, white_list=self.voice_model.FILTER_WHITE_LIST)
        stmt_voice = filter_engine.apply(filter_payload, user)
        stmt_voice = stmt_voice.limit(limit).offset(offset)
        stmt_voice_cnt = select(func.count()).select_from(filter_engine.apply(filter_payload, user))
        voice_result, total_result = await asyncio.gather(
            self.db.execute(stmt_voice),
            self.db.execute(stmt_voice_cnt),
        )
        voices = voice_result.scalars().all()
        total = total_result.scalar_one()

        return voices, total
