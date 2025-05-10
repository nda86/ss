from ss.audit.transport import BaseAuditTransport
from ss.di import inject


@inject
def audit(transport: BaseAuditTransport):
    transport.send_sync(1)


audit()
