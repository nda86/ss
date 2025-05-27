from sqlalchemy.ext.asyncio import AsyncSession

from uow.repo import VoiceRepository
from uow.uow import UnitOfWork


class VoiceService:
    def __init__(self, session: AsyncSession | None = None, uow: UnitOfWork | None = None):
        if uow and session:
            raise ValueError("Передайте либо UnitOfWork, либо AsyncSession, но не оба")
        if not uow and not session:
            raise ValueError("Требуется либо UnitOfWork, либо AsyncSession")

        self.uow = uow
        self.voices = VoiceRepository(session) if session else None

    async def validate_status_transition(self, current_statuses: List[VoteStatus], new_status: VoteStatus):
        invalid_statuses = {VoteStatus.CONFIRMED, VoteStatus.CHANGED, VoteStatus.VIEWED}
        if any(status in invalid_statuses for status in current_statuses):
            raise HTTPException(
                status_code=400, detail=f"Нельзя изменить статус записей с confirmed, changed или viewed"
            )
        if new_status == VoteStatus.CONFIRMED and any(status != VoteStatus.IN_PROGRESS for status in current_statuses):
            raise HTTPException(status_code=400, detail="Подтвердить можно только голоса со статусом in_progress")

    async def change_status_by_filter(
        self, filters: dict, new_status: VoteStatus, user_id: Optional[int] = None
    ) -> None:
        async with self.uow() as uow:
            votes = await uow.votes.get_by_filters(filters)
            if not votes:
                raise HTTPException(status_code=404, detail="Голоса по фильтру не найдены")

            current_statuses = [VoteStatus(vote.status) for vote in votes]
            await self.validate_status_transition(current_statuses, new_status)

            vote_group_ids = [vote.vote_group_id for vote in votes]
            vote_ids = [vote.id for vote in votes]

            batch_size = 10000
            for i in range(0, len(vote_group_ids), batch_size):
                batch_group_ids = vote_group_ids[i : i + batch_size]
                batch_vote_ids = vote_ids[i : i + batch_size]

                if new_status == VoteStatus.IN_PROGRESS:
                    if user_id is None:
                        raise HTTPException(status_code=400, detail="Для статуса in_progress требуется user_id")
                    await uow.votes.update_groups_status(batch_group_ids, VoteStatus.IN_PROGRESS, user_id)
                elif new_status in [VoteStatus.CONFIRMED, VoteStatus.CHANGED]:
                    await uow.votes.update_status_by_ids(batch_vote_ids, new_status)
                    await uow.votes.update_groups_status_except_ids(
                        batch_group_ids, VoteStatus.VIEWED, None, batch_vote_ids
                    )
                elif new_status == VoteStatus.NEW:
                    await uow.votes.update_groups_status(batch_group_ids, VoteStatus.NEW, None)
                else:
                    await uow.votes.update_status_by_ids(batch_vote_ids, new_status)
