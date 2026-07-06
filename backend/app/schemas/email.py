from dataclasses import dataclass
from typing import Literal

EmailDeliveryStatus = Literal["sent", "dry_run", "skipped"]


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: EmailDeliveryStatus
    recipient: str | None
    subject: str
    reason: str | None = None
