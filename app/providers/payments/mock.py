"""MockPaymentProvider — always-approve mock for the MVP.

A tiny hook lets tests force a failure (amount == FAIL_TRIGGER_AMOUNT) so the
failure path can be exercised without a real PG.
"""

import uuid

from app.providers.payments.base import PaymentProvider, PaymentRequest, PaymentResult

PROVIDER_NAME = "mock"
# Any order whose total equals this sentinel is treated as a declined payment.
FAIL_TRIGGER_AMOUNT = 13


class MockPaymentProvider(PaymentProvider):
    async def pay(self, request: PaymentRequest) -> PaymentResult:
        if request.amount == FAIL_TRIGGER_AMOUNT:
            return PaymentResult(
                success=False,
                provider=PROVIDER_NAME,
                failure_code="PAYMENT_DECLINED",
                failure_message="모의 결제가 거절되었습니다.",
            )
        return PaymentResult(
            success=True,
            provider=PROVIDER_NAME,
            provider_payment_id=f"mock_{uuid.uuid4().hex}",
        )
