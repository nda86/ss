from conf.settings import settings
from core.models.voice import ApiThematic, ApiThematicLevel, ApiVoice
from core.repositories.alchemy.filters.filter_engine import FilterPayload
from core.repositories.alchemy.models import VoiceStatus
from core.repositories.alchemy.repository import VoiceRepository
from core.repositories.alchemy.uow import UnitOfWork
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


class VoiceService:
    """
    Сервис для управления голосами и тематиками.
    """

    def __init__(self, session: AsyncSession | None = None, uow: UnitOfWork | None = None):
        if uow and session:
            raise ValueError("Передайте либо UnitOfWork, либо AsyncSession, но не оба")
        if not uow and not session:
            raise ValueError("Требуется либо UnitOfWork, либо AsyncSession")

        self.uow = uow
        self.voices = VoiceRepository(session) if session else None

    async def get_all_thematics(self) -> list[ApiThematic]:
        """
        Возвращает все тематики
        в виде списка объектов ApiCategory.

        Returns:
            Список объектов ApiCategory.
        """
        thematics = await self.voices.get_all_thematics()
        return [ApiThematic.model_validate(th) for th in thematics]

    async def get_thematic_by_id(self, _id) -> ApiThematic | None:
        """
        Возвращает тематику по ид

        Returns:
            Объект тематики или None, если тематика не найдена.
        """
        res = await self.voices.get_thematic_by_id(_id)
        return ApiThematic.model_validate(res) if res is not None else None

    async def get_thematic_levels(self, ids: list[str]) -> list[ApiThematicLevel]:
        """
        Возвращает уровни тематик по списку идентификаторов в виде списка объектов ApiCategoryLevel.

        Args:
            ids: Список идентификаторов уровней тематики.

        Returns:
            Список объектов ApiThematicLevel.
        """
        levels = await self.voices.get_thematic_levels(ids)
        return [ApiThematicLevel.model_validate(level) for level in levels]

    async def get_voices(
        self, filter_payload: FilterPayload, user, limit: int, offset: int
    ) -> tuple[list[ApiVoice], int]:
        """
        Возвращает список голосов и общее количество голосов, соответствующих фильтру, в виде кортежа.

        Args:
            filter_payload: Объект FilterPayload для фильтрации голосов
            user: Объект пользователя
            limit: Максимальное количество возвращаемых голосов
            offset: Сдвиг для пагинации.

        Returns:
            Кортеж, содержащий список объектов ApiVoice и общее количество голосов.
        """
        voices, total = await self.voices.get_voices_with_paginates(filter_payload, user, limit, offset)
        return [ApiVoice.model_validate(voice) for voice in voices], total

    async def get_voice_by_id(self, _id: str) -> list[ApiVoice]:
        """
        Возвращает записи с одинаковым ид голоса

        Args:
            _id: voice_id записи
        Returns:
            Список объектов ApiVoice с одинаковым voice_id
        """
        voices = await self.voices.get_voice_by_id(_id)
        return [ApiVoice.model_validate(voice) for voice in voices]

    async def _validate_status_transition(self, current_statuses: list[VoiceStatus], new_status: VoiceStatus):
        transition_status_rules = {
            VoiceStatus.NEW: (lambda x: x == VoiceStatus.IN_PROGRESS, "IN_PROGRESS => NEW"),
            VoiceStatus.IN_PROGRESS: (lambda x: x == VoiceStatus.NEW, "NEW => IN_PROGRESS"),
            VoiceStatus.CHANGED: (lambda x: x == VoiceStatus.IN_PROGRESS, "IN_PROGRESS => CHANGED"),
            VoiceStatus.CONFIRMED: (lambda x: x == VoiceStatus.IN_PROGRESS, "IN_PROGRESS => CONFIRMED"),
            VoiceStatus.VIEWED: (lambda x: x == VoiceStatus.IN_PROGRESS, "IN_PROGRESS => VIEWED"),
        }
        rule, msg = transition_status_rules[new_status]
        if not all(rule(status) for status in current_statuses):
            raise HTTPException(status_code=400, detail=f"Для выбранных голосов разрешено только {msg}")

    async def change_status_by_filter(self, filter_payload: FilterPayload, new_status: VoiceStatus, user) -> None:
        async with self.uow() as uow:
            voices = await uow.voices.get_voices(filter_payload, user)
            if not voices:
                raise HTTPException(status_code=404, detail="Голоса по фильтру не найдены")

            current_statuses = [VoiceStatus(vote.status) for vote in voices]
            await self._validate_status_transition(current_statuses, new_status)

            voice_ids = [voice.get_voice_id() for voice in voices]
            record_ids = [voice.get_record_id() for voice in voices]

            batch_size = settings.db.voice_count_for_update
            for i in range(0, len(voice_ids), batch_size):
                batch_voice_ids = voice_ids[i : i + batch_size]
                batch_record_ids = record_ids[i : i + batch_size]

                if new_status == VoiceStatus.IN_PROGRESS:
                    await uow.voices.assign(batch_voice_ids, VoiceStatus.IN_PROGRESS, user)
                elif new_status in [VoiceStatus.CONFIRMED, VoiceStatus.CHANGED]:
                    await uow.voices.annotate(batch_record_ids, batch_voice_ids, new_status)
                elif new_status == VoiceStatus.NEW:
                    await uow.voices.unassign(batch_voice_ids, VoiceStatus.NEW)
