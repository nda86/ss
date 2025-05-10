import asyncio

from ss.audit.emitters import emit_audit_catalog_sync, emit_audit_catalog_async


async def main():
    await emit_audit_catalog_async()


if __name__ == "__main__":
    # emit_audit_catalog_sync()
    asyncio.run(main())
