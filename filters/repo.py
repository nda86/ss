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

    async def get_all_categories(self) -> list[SqlCategory]:
        stmt = select(SqlCategory)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_category_levels(self, ids: list[str]) -> dict:
        match ids:
            case [] | None:
                stmt = select(SqlCategory.level_1_id.label("id"), SqlCategory.level_1_name.label("name")).distinct()
            case [l1]:
                stmt = (
                    select(SqlCategory.level_2_id.label("id"), SqlCategory.level_2_name.label("name"))
                    .where(SqlCategory.level_1_id == l1)
                    .distinct()
                )
            case [l1, l2]:
                stmt = (
                    select(SqlCategory.level_3_id.label("id"), SqlCategory.level_3_name.label("name"))
                    .where(
                        SqlCategory.level_1_id == l1,
                        SqlCategory.level_2_id == l2,
                    )
                    .distinct()
                )
            case [l1, l2, l3]:
                stmt = (
                    select(SqlCategory.level_4_id.label("id"), SqlCategory.level_4_name.label("name"))
                    .where(
                        SqlCategory.level_1_id == l1,
                        SqlCategory.level_2_id == l2,
                        SqlCategory.level_3_id == l3,
                    )
                    .distinct()
                )
            case _:
                return {}

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
        stmt = filter_engine.apply_distinct(filter_payload, user)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        voices = result.scalars().all()

        count_stmt = select(func.count()).select_from(SqlVoice)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        return voices, total
