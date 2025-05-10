import asyncio
import logging
import socket
import time
from abc import ABC, abstractmethod

from ss.di import container

transport_logger = logging.getLogger("audit.transport_logger")


class BaseAuditTransport(ABC):
    @abstractmethod
    def send_sync(self, message: str, host: str, port: int, retries: int = 3, backoff: int = 2):
        raise NotImplementedError

    @abstractmethod
    async def send_async(self, message: str, host: str, port: int, retries: int = 3, backoff: int = 2):
        raise NotImplementedError


class FluentAuditTransport(BaseAuditTransport):

    async def send_async(self, message: str, host: str, port: int, retries: int = 3, backoff: int = 2):
        for attempt in range(1, retries + 1):
            try:
                reader, writer = await asyncio.open_connection(host, port)
                writer.write(message.encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return
            except (socket.error, BrokenPipeError) as e:
                wait_time = backoff**attempt
                transport_logger.warning(f"Failed to send message (attempts {attempt}/{retries}) \nerror: {e}")
                await asyncio.sleep(wait_time)
        transport_logger.error(f"Failed send message after {attempt} retries")

    def send_sync(self, message: str, host: str, port: int, retries: int = 3, backoff: int = 2):
        try:
            with socket.create_connection((host, port)) as fluent_socket:
                for attempt in range(1, retries + 1):
                    try:
                        fluent_socket.sendall(message.encode("utf-8"))
                        return
                    except (socket.error, BrokenPipeError) as e:
                        wait_time = backoff**attempt
                        transport_logger.warning(f"Failed to send message (attempts {attempt}/{retries}) \nerror: {e}")
                        time.sleep(wait_time)
                transport_logger.error(f"Failed send message after {attempt} retries")
        except Exception as e:
            transport_logger.exception(f"Error sending audit message: {e}")


class KafkaAuditTransport(BaseAuditTransport):
    def send_sync(self, message: str, host: str, port: int, retries: int = 3, backoff: int = 2):
        print("sync send via kafka")

    async def send_async(self, message: str, host: str, port: int, retries: int = 3, backoff: int = 2):
        pass


container.bind(BaseAuditTransport, FluentAuditTransport)
