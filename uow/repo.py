import asyncio

from api.v1.schemas import FilterPayload
from core.repositories.alchemy.db import AsyncSessionLocal
from core.repositories.alchemy.decorators import handle_db_errors
from core.repositories.alchemy.filters.filter_engine import SqlAlchemyFilterEngine
from core.repositories.alchemy.models import SqlThematic, SqlVoice, VoiceStatus
from core.repositories.base_repository import BaseRepository
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import SQLAlchemyError


class VoiceRepository(BaseRepository):
    """
    Репозиторий для работы с данными в базе данных с использованием SQLAlchemy.
    """

    def __init__(self, db: AsyncSessionLocal):
        """
        Инициализация репозитория.

        Args:
            db: Экземпляр асинхронной сессии базы данных.
        """
        self.db = db
        self.voice_model = SqlVoice
        self.thematic_model = SqlThematic
        self.base_thematic_stmt = select(SqlThematic)
        self.base_voice_stmt = select(SqlVoice)
        self.active_thematic_stmt = self.base_thematic_stmt.where(self.thematic_model.is_active())
        self.active_voice_stmt = self.base_voice_stmt.where(self.voice_model.is_active())

    @handle_db_errors(default_return=[])
    async def get_all_thematics(self) -> list[SqlThematic]:
        """
        Возвращает все категории из базы данных.

        Returns:
            Список всех категорий.
        """
        result = await self.db.execute(self.active_thematic_stmt)
        return result.scalars().all()

    @handle_db_errors(default_return=None)
    async def get_thematic_by_id(self, _id: str) -> SqlThematic | None:
        """
        Возвращает тематику по её идентификатору.

        Args:
            _id: Идентификатор тематики.

        Returns:
            Объект тематики или None, если тематика не найдена.
        """
        stmt = self.active_thematic_stmt.where(self.thematic_model.get_ext_id() == _id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @handle_db_errors(default_return=[])
    async def get_thematic_levels(self, ids: list[str]) -> list[dict]:
        """
        Возвращает уровни категорий по списку идентификаторов.

        Args:
            ids: Список идентификаторов категорий.

        Returns:
            Список словарей с уровнями категорий.
        """
        level_fields = [
            (SqlThematic.level_1_id, SqlThematic.level_1_name),
            (SqlThematic.level_2_id, SqlThematic.level_2_name),
            (SqlThematic.level_3_id, SqlThematic.level_3_name),
            (SqlThematic.level_4_id, SqlThematic.level_4_name),
        ]

        if ids is None or len(ids) > len(level_fields):
            return []

        level = len(ids)

        id_field, name_field = level_fields[level]
        columns = [
            id_field.label("id"),
            name_field.label("name"),
        ]
        if level == 4:
            columns.append(SqlThematic.get_ext_id().label("thematic_id"))
        stmt = self.active_thematic_stmt.with_only_columns(*columns).distinct(id_field)

        for i, id_value in enumerate(ids):
            stmt = stmt.where(level_fields[i][0] == id_value)

        result = await self.db.execute(stmt)
        return result.mappings().all()

    @handle_db_errors(default_return=([], 0))
    async def get_voices_with_paginates(
        self, filter_payload: FilterPayload, user, limit: int, offset: int
    ) -> tuple[list[SqlVoice], int]:
        """
        Возвращает список голосов и общее количество голосов, соответствующих фильтру.

        Args:
            filter_payload: Объект FilterPayload для фильтрации голосов
            user: Объект пользователя
            limit: Максимальное количество возвращаемых голосов
            offset: Сдвиг для пагинации.

        Returns:
            Кортеж, содержащий список голосов и общее количество голосов.
        """
        filter_engine = SqlAlchemyFilterEngine(model=self.voice_model, white_list=self.voice_model.FILTER_WHITE_LIST)
        stmt_voice = filter_engine.apply(filter_payload, user)
        stmt_voice = stmt_voice.limit(limit).offset(offset)
        stmt_voice_cnt = select(func.count()).select_from(filter_engine.apply(filter_payload, user).subquery())
        voice_result, total_result = await asyncio.gather(
            self.db.execute(stmt_voice),
            self.db.execute(stmt_voice_cnt),
        )
        voices = voice_result.scalars().all()
        total = total_result.scalar_one()

        return voices, total

    @handle_db_errors(default_return=([], 0))
    async def get_voices(self, filter_payload: FilterPayload, user) -> list[SqlVoice]:
        """
        Возвращает список голосов соответствующих фильтру.

        Args:
            filter_payload: Объект FilterPayload для фильтрации голосов
            user: Объект пользователя


        Returns:
            список голосов
        """
        filter_engine = SqlAlchemyFilterEngine(model=self.voice_model, white_list=self.voice_model.FILTER_WHITE_LIST)
        stmt_voice = filter_engine.apply(filter_payload, user)

        voice_result = await self.db.execute(stmt_voice)
        voices = voice_result.scalars().all()
        return voices

    @handle_db_errors(default_return=None)
    async def get_voice_by_id(self, _id: str) -> list[SqlVoice]:
        stmt = self.active_voice_stmt.where(self.voice_model.get_voice_id() == _id)
        res = await self.db.execute(stmt)
        return res.mappings.all()

    async def save_voices(self, voices: list[SqlVoice]) -> bool:
        """
        Сохраняет список голосов в базу данных.

        Args:
            voices: Список объектов SqlVoice для сохранения.

        Returns:
            True, если сохранение прошло успешно, иначе False.
        """
        try:
            self.db.add_all(voices)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            print(f"Error during bulk insert: {e}")
            return False

    async def annotate(self, record_ids: list[str], voice_ids: list[str], status: VoiceStatus):
        stmt_record = (
            update(self.voice_model).where(self.voice_model.get_record_id().in_(record_ids)).values(status=status.value)
        )
        stmt_voice = update(self.voice_model).where(
            and_(self.voice_model.get_voice_id().in_(voice_ids), self.voice_model.get_record_id().not_in(record_ids))
        )
        await asyncio.gather(
            *[
                self.db.execute(stmt_record),
                self.db.execute(stmt_voice),
            ]
        )

    async def assign(self, voice_ids: list[str], status: VoiceStatus, user):
        stmt = (
            update(self.voice_model)
            .where(self.voice_model.get_voice_id().in_(voice_ids))
            .values(status=status.value, author_id=user.id)
        )
        await self.db.execute(stmt)

    async def unassign(self, voice_ids: list[str], status: VoiceStatus):
        stmt = (
            update(self.voice_model)
            .where(self.voice_model.get_voice_id().in_(voice_ids))
            .values(status=status.value, author_id=None)
        )
        await self.db.execute(stmt)
