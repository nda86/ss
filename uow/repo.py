from sqlalchemy.ext.asyncio import AsyncSession


class VoiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_status_by_ids(self, vote_ids: List[int], status: VoteStatus, author_id: Optional[int] = None):
        await self.session.execute(
            Vote.__table__.update().where(Vote.id.in_(vote_ids)).values(status=status.value, author_id=author_id)
        )

    async def update_groups_status(
        self, vote_group_ids: List[int], status: VoteStatus, author_id: Optional[int] = None
    ):
        await self.session.execute(
            Vote.__table__.update()
            .where(Vote.vote_group_id.in_(vote_group_ids))
            .values(status=status.value, author_id=author_id)
        )

    async def update_groups_status_except_ids(
        self,
        vote_group_ids: List[int],
        status: VoteStatus,
        author_id: Optional[int] = None,
        exclude_ids: List[int] = None,
    ):
        query = Vote.__table__.update().where(Vote.vote_group_id.in_(vote_group_ids))
        if exclude_ids:
            query = query.where(~Vote.id.in_(exclude_ids))
        await self.session.execute(query.values(status=status.value, author_id=author_id))
