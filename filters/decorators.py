import functools
import logging
from typing import Callable, TypeVar, Any

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

T = TypeVar("T")


def handle_db_errors(default_return: Any = None) -> Callable:
    """
    Декоратор для обработки ошибок базы данных в методах репозитория.

    Args:
        default_return: Значение, возвращаемое при ошибке (None, [], False и т.д.).
    Returns:
        Декорированный метод.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except SQLAlchemyError as e:
                logger.error(f"Database error in {func.__name__} with args {args}, kwargs {kwargs}: {e}")
                return default_return

        return wrapper

    return decorator
