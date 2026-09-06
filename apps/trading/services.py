from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.common.utils import quantize_money, quantize_weight
from apps.invoices.models import Invoice
from apps.transactions.models import Transaction
from apps.trading.models import Order, OrderExecution
from apps.wallet.models import AssetHolding
from apps.wallet.services import WalletService


class TradingService:
    """منطق کسب‌وکار خرید/فروش؛ تمام محاسبات مالی داخل سرویس هستند و API فقط لایه‌ی ورودی است."""

    @staticmethod
    def create_buy_order(user, metal_code: str, quantity: Decimal | str, price_per_gram: Decimal | str, idempotency_key: str = ""):
        quantity = quantize_weight(quantity)
        price_per_gram = quantize_money(price_per_gram)
        total_amount = quantize_money(quantity * price_per_gram)

        if not idempotency_key:
            raise ValueError("IDEMPOTENCY_KEY_REQUIRED")

        existing = Order.objects.filter(user=user, idempotency_key=idempotency_key).first()
        if existing:
            return existing

        with transaction.atomic():
            wallet = WalletService.get_or_create_wallet(user)
            wallet = wallet.__class__.objects.select_for_update().get(pk=wallet.pk)
            if wallet.available_balance < total_amount:
                raise ValueError("INSUFFICIENT_BALANCE")

            order = Order.objects.create(
                user=user,
                metal_code=metal_code,
                side="buy",
                order_type="limit",
                quantity=quantity,
                remaining_quantity=quantity,
                price_per_gram=price_per_gram,
                total_amount=total_amount,
                idempotency_key=idempotency_key,
                status="pending",
            )

            wallet.available_balance -= total_amount
            wallet.pending_balance += total_amount
            wallet.save(update_fields=["available_balance", "pending_balance", "updated_at"])

            Transaction.objects.create(
                user=user,
                transaction_type="buy_order",
                amount=total_amount,
                currency=wallet.currency,
                status="pending",
                reference_id=f"buy-order-{order.id}",
                metadata={"order_id": order.id, "metal_code": metal_code},
            )

            Invoice.objects.create(
                user=user,
                invoice_number=f"INV-{order.id}",
                order_type="buy",
                metal_code=metal_code,
                quantity=quantity,
                unit_price=price_per_gram,
                total_amount=total_amount,
                status="issued",
                metadata={"order_id": order.id},
            )

            return order

    @staticmethod
    def create_sell_order(user, metal_code: str, quantity: Decimal | str, price_per_gram: Decimal | str, idempotency_key: str = ""):
        quantity = quantize_weight(quantity)
        price_per_gram = quantize_money(price_per_gram)
        total_amount = quantize_money(quantity * price_per_gram)

        if not idempotency_key:
            raise ValueError("IDEMPOTENCY_KEY_REQUIRED")

        existing = Order.objects.filter(user=user, idempotency_key=idempotency_key).first()
        if existing:
            return existing

        with transaction.atomic():
            holding = AssetHolding.objects.select_for_update().filter(user=user, metal_code=metal_code).first()
            if holding is None or holding.available_quantity < quantity:
                raise ValueError("INSUFFICIENT_ASSET")

            holding.available_quantity -= quantity
            holding.locked_quantity += quantity
            holding.save(update_fields=["available_quantity", "locked_quantity", "updated_at"])

            order = Order.objects.create(
                user=user,
                metal_code=metal_code,
                side="sell",
                order_type="limit",
                quantity=quantity,
                remaining_quantity=quantity,
                price_per_gram=price_per_gram,
                total_amount=total_amount,
                idempotency_key=idempotency_key,
                status="pending",
            )

            Transaction.objects.create(
                user=user,
                transaction_type="sell_order",
                amount=total_amount,
                currency="IRR",
                status="pending",
                reference_id=f"sell-order-{order.id}",
                metadata={"order_id": order.id, "metal_code": metal_code},
            )

            Invoice.objects.create(
                user=user,
                invoice_number=f"INV-{order.id}",
                order_type="sell",
                metal_code=metal_code,
                quantity=quantity,
                unit_price=price_per_gram,
                total_amount=total_amount,
                status="issued",
                metadata={"order_id": order.id},
            )

            return order

    @staticmethod
    def execute_trade(buy_order: Order, sell_order: Order, executed_quantity: Decimal | str, executed_price: Decimal | str):
        executed_quantity = quantize_weight(executed_quantity)
        executed_price = quantize_money(executed_price)
        executed_amount = quantize_money(executed_quantity * executed_price)

        with transaction.atomic():
            buy_order = Order.objects.select_for_update().get(pk=buy_order.pk)
            sell_order = Order.objects.select_for_update().get(pk=sell_order.pk)

            if buy_order.status == "filled" or sell_order.status == "filled":
                raise ValueError("ORDER_ALREADY_FILLED")

            buy_order.remaining_quantity -= executed_quantity
            sell_order.remaining_quantity -= executed_quantity
            buy_order.status = "filled" if buy_order.remaining_quantity <= 0 else "partially_filled"
            sell_order.status = "filled" if sell_order.remaining_quantity <= 0 else "partially_filled"
            buy_order.save(update_fields=["remaining_quantity", "status", "updated_at"])
            sell_order.save(update_fields=["remaining_quantity", "status", "updated_at"])

            OrderExecution.objects.create(
                buy_order=buy_order,
                sell_order=sell_order,
                executed_quantity=executed_quantity,
                executed_price=executed_price,
                executed_amount=executed_amount,
            )

            return executed_amount
