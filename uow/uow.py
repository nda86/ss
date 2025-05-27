from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker


from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from uow.repo import VoiceRepository


class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.session = None

    @asynccontextmanager
    async def __call__(self):
        self.session = self.session_factory()
        try:
            yield self
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        finally:
            await self.session.close()
            self.session = None

    @property
    def voices(self):
        if self.session is None:
            raise RuntimeError("Сессия не инициализирована. Используйте 'async with uow()' для транзакций.")
        return VoiceRepository(self.session)
