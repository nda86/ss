from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine("postgresql+asyncpg://user:password@localhost:5432/dbname", echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_uow():
    async with UnitOfWork(AsyncSessionLocal) as uow:
        yield uow


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


# Зависимости для получения сервиса
async def get_service_with_uow(uow: UnitOfWork = Depends(get_uow)) -> VoteService:
    return VoteService(uow=uow)


async def get_service_with_session(session: AsyncSession = Depends(get_session)) -> VoteService:
    return VoteService(session=session)
