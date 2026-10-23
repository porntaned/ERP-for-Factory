"""Internal atomic transfer command. No request deduplication or transport yet."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction

from access_control.models import WarehouseRole, WarehouseRoleAssignment

from .models import StockLedgerEntry
from .services import get_stock_balance
from .transfer_policy import require_transfer_quality


class TransferValidationError(ValueError):
    pass


class TransferAuthorizationError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


def _validate_payload(quantity, reason):
    if (
        not isinstance(quantity, Decimal)
        or not quantity.is_finite()
        or not Decimal("0") < quantity < Decimal("100000000000000")
    ):
        raise TransferValidationError("quantity must be a positive finite Decimal below 10^14")
    _, digits, exponent = quantity.as_tuple()
    extra_places = -6 - exponent
    if extra_places > 0 and any(digits[-extra_places:]):
        raise TransferValidationError("quantity must be representable at six fractional places")
    if not isinstance(reason, str) or not reason.strip():
        raise TransferValidationError("reason must be nonblank")


def transfer_stock(
    *, lot, source_warehouse, destination_warehouse, actor, quantity: Decimal, reason: str
) -> tuple[StockLedgerEntry, StockLedgerEntry]:
    """Post a debit/credit pair, requiring current WAREHOUSE authority at both ends.

    Source must be RELEASED; destination Quality is unchanged. Return (debit, credit).
    Each invocation is a NEW transfer: not retry-safe, no persistent transfer identity.
    There is no endpoint or automatic retry. Those require the later request contract.
    The atomic block is also a savepoint when the caller owns an outer transaction.
    """
    _validate_payload(quantity, reason)
    user_model = get_user_model()
    if not isinstance(actor, user_model) or actor.pk is None or actor._state.adding:
        raise TransferAuthorizationError("actor must be a saved active user")
    with transaction.atomic():
        # Locks Lot -> Item -> Warehouses (ID order) -> Plant, as ledger/Quality do.
        require_transfer_quality(
            lot=lot,
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
        )
        saved_actor = user_model.objects.select_for_update().filter(pk=actor.pk).first()
        grants = list(
            WarehouseRoleAssignment.objects.select_for_update()
            .filter(
                user_id=actor.pk,
                warehouse_id__in=(source_warehouse.pk, destination_warehouse.pk),
                role=WarehouseRole.WAREHOUSE,
            )
            .order_by("warehouse_id")
        )
        if saved_actor is None or not saved_actor.is_active or len(grants) != 2:
            raise TransferAuthorizationError("active WAREHOUSE authority at both ends is required")
        if get_stock_balance(lot=lot, warehouse=source_warehouse) < quantity:
            raise InsufficientStockError("source balance is insufficient")
        payload = dict(lot=lot, actor=saved_actor, reason=reason)
        debit = StockLedgerEntry.objects.create(
            **payload, warehouse=source_warehouse, quantity_delta=quantity.copy_negate()
        )
        credit = StockLedgerEntry.objects.create(
            **payload, warehouse=destination_warehouse, quantity_delta=quantity
        )
        return debit, credit
