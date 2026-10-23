"""Internal stock snapshots and authorized synthetic receipt commands."""

from decimal import Decimal
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.models import Sum

from access_control.models import WarehouseRole, WarehouseRoleAssignment
from facilities.models import Warehouse

from .models import Lot, StockLedgerEntry, StockReceipt


def get_stock_balance(*, lot: Lot, warehouse: Warehouse) -> Decimal:
    for value, model in ((lot, Lot), (warehouse, Warehouse)):
        if not isinstance(value, model) or value.pk is None or value._state.adding:
            raise ValueError("lot and warehouse must be saved records")
    lot_org = Lot.objects.filter(pk=lot.pk).values_list("item__organization_id", flat=True).first()
    warehouse_org = (
        Warehouse.objects.filter(pk=warehouse.pk)
        .values_list("plant__organization_id", flat=True)
        .first()
    )
    if lot_org is None or warehouse_org is None or lot_org != warehouse_org:
        raise ValueError("lot and warehouse must exist in the same organization")
    total = StockLedgerEntry.objects.filter(lot_id=lot.pk, warehouse_id=warehouse.pk).aggregate(
        total=Sum("quantity_delta")
    )["total"]
    return total if total is not None else Decimal("0")


class ReceiptValidationError(Exception):
    pass


class ReceiptAuthorizationError(Exception):
    pass


class ReceiptConflictError(Exception):
    pass


def _saved_record(value, model):
    return isinstance(value, model) and value.pk is not None and not value._state.adding


def _validate_receipt_payload(lot, warehouse, quantity, reason, request_id):
    if not _saved_record(lot, Lot) or not _saved_record(warehouse, Warehouse):
        raise ReceiptValidationError("lot and warehouse must be saved records")
    if (
        not isinstance(quantity, Decimal)
        or not quantity.is_finite()
        or not Decimal("0") < quantity < Decimal("100000000000000")
    ):
        raise ReceiptValidationError(
            "quantity must be a positive finite base-UOM Decimal below 10^14"
        )
    # Inspect digits without rounding or depending on the caller's Decimal context.
    # Trailing zeros beyond six fractional places do not change representability.
    _, digits, exponent = quantity.as_tuple()
    extra_places = -6 - exponent
    if extra_places > 0 and any(digits[-extra_places:]):
        raise ReceiptValidationError("quantity must have at most six fractional places")
    if not isinstance(reason, str) or not reason.strip():
        raise ReceiptValidationError("reason must be nonblank")
    if not isinstance(request_id, UUID):
        raise ReceiptValidationError("request_id must be a UUID")


def _lock_receipt_parents(lot, warehouse):
    """Match ledger lock order/modes before taking authorization locks."""
    with connection.cursor() as cursor:
        cursor.execute("SHOW transaction_isolation")
        if cursor.fetchone()[0] != "read committed":
            raise ReceiptValidationError("receipt commands require READ COMMITTED")
    locked_lot = Lot.objects.select_for_update().filter(pk=lot.pk).first()
    if locked_lot is None:
        raise ReceiptValidationError("lot must exist")
    # These are persisted identities, not caller-cached related objects. SHARE matches
    # ledger triggers and protects first-receipt identity until both writes commit.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT organization_id FROM catalog_item WHERE id = %s FOR SHARE",
            [locked_lot.item_id],
        )
        item = cursor.fetchone()
        cursor.execute(
            "SELECT plant_id FROM facilities_warehouse WHERE id = %s FOR SHARE", [warehouse.pk]
        )
        destination = cursor.fetchone()
        if item is None or destination is None:
            raise ReceiptValidationError("receipt parents must exist")
        cursor.execute(
            "SELECT organization_id FROM facilities_plant WHERE id = %s FOR SHARE",
            [destination[0]],
        )
        plant = cursor.fetchone()
    if plant is None or item[0] != plant[0]:
        raise ReceiptValidationError("lot and warehouse must belong to one organization")
    return locked_lot


def _existing_receipt(request_id, *, lot, warehouse, actor, quantity, reason):
    receipt = (
        StockReceipt.objects.select_related("ledger_entry").filter(request_id=request_id).first()
    )
    if receipt is None:
        return None
    entry = receipt.ledger_entry
    if (
        entry.lot_id == lot.pk
        and entry.warehouse_id == warehouse.pk
        and entry.actor_id == actor.pk
        and entry.quantity_delta == quantity
        and entry.reason == reason
    ):
        return receipt
    raise ReceiptConflictError("request_id was already used for another receipt")


def receive_stock(*, lot, warehouse, actor, quantity: Decimal, reason: str, request_id: UUID):
    """Receive into an existing pair without changing its Quality disposition.

    Storage primitives alone do not authorize a receipt. Every command, including
    retries, locks current parent identities, active actor and exact Warehouse grant.
    The Lot lock coordinates with Quality; HOLD/default HOLD/RELEASED all remain as-is.
    """
    _validate_receipt_payload(lot, warehouse, quantity, reason, request_id)
    user_model = get_user_model()
    if not _saved_record(actor, user_model):
        raise ReceiptAuthorizationError("actor must be a saved active user")
    with transaction.atomic():
        locked_lot = _lock_receipt_parents(lot, warehouse)
        saved_actor = user_model.objects.select_for_update().filter(pk=actor.pk).first()
        grant = (
            WarehouseRoleAssignment.objects.select_for_update()
            .filter(user_id=actor.pk, warehouse_id=warehouse.pk, role=WarehouseRole.WAREHOUSE)
            .first()
        )
        if saved_actor is None or not saved_actor.is_active or grant is None:
            raise ReceiptAuthorizationError("actor needs an active WAREHOUSE grant at destination")
        payload = dict(
            lot=locked_lot, warehouse=warehouse, actor=saved_actor, quantity=quantity, reason=reason
        )
        existing = _existing_receipt(request_id, **payload)
        if existing is not None:
            return existing
        try:
            # Global UUID uniqueness can race across different Lots. Roll back BOTH
            # writes before reading the winning receipt, never leave an extra delta.
            with transaction.atomic():
                entry = StockLedgerEntry.objects.create(
                    lot=locked_lot,
                    warehouse=warehouse,
                    actor=saved_actor,
                    quantity_delta=quantity,
                    reason=reason,
                )
                return StockReceipt.objects.create(request_id=request_id, ledger_entry=entry)
        except IntegrityError:
            existing = _existing_receipt(request_id, **payload)
            if existing is not None:
                return existing
            raise
