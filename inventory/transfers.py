"""Internal atomic transfer command with immutable UUID request deduplication."""

from decimal import Decimal
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from access_control.models import WarehouseRole, WarehouseRoleAssignment
from quality.models import LotDisposition
from quality.services import get_lot_disposition

from .models import StockLedgerEntry, StockTransfer
from .services import get_stock_balance
from .transfer_policy import TransferQualityError, lock_transfer_scope


class TransferValidationError(ValueError):
    pass


class TransferAuthorizationError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


class TransferConflictError(Exception):
    pass


def _existing_transfer(
    request_id, *, lot, source_warehouse, destination_warehouse, actor, quantity, reason
):
    history = (
        StockTransfer.objects.select_related("source_entry", "destination_entry")
        .filter(request_id=request_id)
        .first()
    )
    if history is None:
        return None
    debit, credit = history.source_entry, history.destination_entry
    if (
        debit.lot_id == lot.pk
        and debit.warehouse_id == source_warehouse.pk
        and credit.warehouse_id == destination_warehouse.pk
        and debit.actor_id == actor.pk
        and credit.quantity_delta == quantity
        and debit.reason == reason
    ):
        return debit, credit
    raise TransferConflictError("request_id was already used for another transfer")


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
    *,
    lot,
    source_warehouse,
    destination_warehouse,
    actor,
    quantity: Decimal,
    reason: str,
    request_id: UUID,
) -> tuple[StockLedgerEntry, StockLedgerEntry]:
    """Post a debit/credit pair, requiring current WAREHOUSE authority at both ends.

    Source must be RELEASED; destination Quality is unchanged. Return (debit, credit).
    Exact UUID replays recheck current authorization, returning historical results even
    after Quality changes. New movements require RELEASED source and sufficient stock.
    Legacy NULL request IDs are not adopted. There is no endpoint or automatic retry.
    The atomic block is also a savepoint when the caller owns an outer transaction.
    """
    _validate_payload(quantity, reason)
    if not isinstance(request_id, UUID):
        raise TransferValidationError("request_id must be a UUID")
    user_model = get_user_model()
    if not isinstance(actor, user_model) or actor.pk is None or actor._state.adding:
        raise TransferAuthorizationError("actor must be a saved active user")
    with transaction.atomic():
        # Locks Lot -> Item -> Warehouses (ID order) -> Plant, as ledger/Quality do.
        lot, source_warehouse, destination_warehouse = lock_transfer_scope(
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
        command = dict(
            lot=lot,
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
            actor=saved_actor,
            quantity=quantity,
            reason=reason,
        )
        existing = _existing_transfer(request_id, **command)
        if existing is not None:
            return existing
        if get_lot_disposition(lot=lot, warehouse=source_warehouse) != LotDisposition.RELEASED:
            raise TransferQualityError("source Lot-Warehouse must be RELEASED")
        if get_stock_balance(lot=lot, warehouse=source_warehouse) < quantity:
            raise InsufficientStockError("source balance is insufficient")
        payload = dict(lot=lot, actor=saved_actor, reason=reason)
        try:
            # A global UUID can race across different Lots. Roll back all losing writes
            # before reading the committed winner; do not leave an orphan debit/credit.
            with transaction.atomic():
                debit = StockLedgerEntry.objects.create(
                    **payload, warehouse=source_warehouse, quantity_delta=quantity.copy_negate()
                )
                credit = StockLedgerEntry.objects.create(
                    **payload, warehouse=destination_warehouse, quantity_delta=quantity
                )
                StockTransfer.objects.create(
                    source_entry=debit, destination_entry=credit, request_id=request_id
                )
                return debit, credit
        except IntegrityError:
            existing = _existing_transfer(request_id, **command)
            if existing is not None:
                return existing
            raise
