"""PaymentProvider interface.

OrderService depends only on this contract; swapping in a real PG later means
adding a new implementation, not touching order logic.
"""

import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentRequest:
    order_id: uuid.UUID
    amount: int
    currency: str
    method: str


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    provider: str
    provider_payment_id: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None


class PaymentProvider(Protocol):
    async def pay(self, request: PaymentRequest) -> PaymentResult: ...
