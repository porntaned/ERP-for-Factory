"""M4.5: reverse one receipt or transfer with compensating entries that reference it.

Owner policy (Issue #59): APPROVER at every warehouse involved; whole transaction only;
once only (a reversal is itself never reversible); insufficient stock is rejected rather
than cascading; receipt reversal in any Quality state; transfer reversal requires the
original destination, where the goods leave, to be RELEASED. Quality never changes.
M6.2 (Issue #103): reverse_transfer also puts stock back, so it is refused with LotRejectedError
while the Lot is REJECTED at ANY warehouse (checked after the RELEASED gate and the exact-replay
check). reverse_receipt only takes stock out and stays allowed.
Internal command only; there is no endpoint or automatic retry.
"""

from decimal import Decimal
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from access_control.models import WarehouseRole, WarehouseRoleAssignment
from quality.models import LotDisposition
from quality.services import get_lot_disposition

from .lot_gate import require_lot_not_rejected
from .models import StockLedgerEntry, StockReceipt, StockReversal, StockTransfer
from .request_keys import owned_by_other_command
from .services import ReceiptValidationError, _lock_receipt_parents, get_stock_balance
from .transfer_policy import TransferQualityValidationError, lock_transfer_scope
from .transfers import InsufficientStockError

__all__ = [
    "AlreadyReversedError",
    "InsufficientStockError",
    "ReversalAuthorizationError",
    "ReversalConflictError",
    "ReversalQualityError",
    "ReversalValidationError",
    "reverse_receipt",
    "reverse_transfer",
]


class ReversalValidationError(ValueError):
    pass


class ReversalAuthorizationError(Exception):
    pass


class ReversalConflictError(Exception):
    pass


class AlreadyReversedError(Exception):
    pass


class ReversalQualityError(Exception):
    pass


def _saved(value, model):
    return isinstance(value, model) and value.pk is not None and not value._state.adding


def _validate(original, model, actor, reason, request_id):
    if not _saved(original, model):
        raise ReversalValidationError("original must be a saved record")
    if not isinstance(reason, str) or not reason.strip():
        raise ReversalValidationError("reason must be nonblank")
    if not isinstance(request_id, UUID):
        raise ReversalValidationError("request_id must be a UUID")
    if not _saved(actor, get_user_model()):
        raise ReversalAuthorizationError("actor must be a saved active user")


def _lock_authority(actor, warehouse_ids):
    """Lock the persisted actor and APPROVER grants after the stock scope locks."""
    saved_actor = get_user_model().objects.select_for_update().filter(pk=actor.pk).first()
    granted = {
        grant.warehouse_id
        for grant in WarehouseRoleAssignment.objects.select_for_update()
        .filter(user_id=actor.pk, warehouse_id__in=warehouse_ids, role=WarehouseRole.APPROVER)
        .order_by("warehouse_id")
    }
    if saved_actor is None or not saved_actor.is_active or granted != set(warehouse_ids):
        raise ReversalAuthorizationError("active APPROVER authority at every warehouse is required")
    return saved_actor


def _existing(request_id, *, field, original, actor, reason):
    reversal = StockReversal.objects.select_related("debit_entry").filter(request_id=request_id)
    reversal = reversal.first()
    if reversal is None:
        return None
    entry = reversal.debit_entry
    if (
        getattr(reversal, f"{field}_id") == original.pk
        and entry.actor_id == actor.pk
        and entry.reason == reason
    ):
        return reversal
    raise ReversalConflictError("request_id was already used for another reversal")


def _prior_outcome(request_id, *, field, original, actor, reason):
    """Exact replay returns history; a reused key or an already-reversed original raises.

    Called before writing and again after an IntegrityError, when a concurrent writer may
    have won the registry key or the once-only one-to-one on the original.
    """
    existing = _existing(request_id, field=field, original=original, actor=actor, reason=reason)
    if existing is not None:
        return existing
    if owned_by_other_command(request_id, "REVERSAL"):
        raise ReversalConflictError("request_id was already used by another command")
    if StockReversal.objects.filter(**{field: original}).exists():
        raise AlreadyReversedError("this original has already been reversed")
    return None


def _require_balance(lot, warehouse, quantity: Decimal):
    if get_stock_balance(lot=lot, warehouse=warehouse) < quantity:
        raise InsufficientStockError("balance is insufficient to reverse the whole transaction")


def reverse_receipt(*, receipt, actor, reason: str, request_id: UUID) -> StockReversal:
    """Post one negative entry offsetting the receipt; Quality state is irrelevant."""
    _validate(receipt, StockReceipt, actor, reason, request_id)
    with transaction.atomic():
        original = (
            StockReceipt.objects.select_related("ledger_entry__lot", "ledger_entry__warehouse")
            .filter(pk=receipt.pk)
            .first()
        )
        if original is None:
            raise ReversalValidationError("receipt must exist")
        entry = original.ledger_entry
        # Lot -> Item -> Warehouse -> Plant, then actor and grants: same order as receipts.
        try:
            lot = _lock_receipt_parents(entry.lot, entry.warehouse)
        except ReceiptValidationError as exc:
            raise ReversalValidationError(str(exc)) from exc
        saved_actor = _lock_authority(actor, [entry.warehouse_id])
        context = dict(field="receipt", original=original, actor=saved_actor, reason=reason)
        existing = _prior_outcome(request_id, **context)
        if existing is not None:
            return existing
        _require_balance(lot, entry.warehouse, entry.quantity_delta)
        try:
            with transaction.atomic():
                debit = StockLedgerEntry.objects.create(
                    lot=lot,
                    warehouse=entry.warehouse,
                    actor=saved_actor,
                    quantity_delta=entry.quantity_delta.copy_negate(),
                    reason=reason,
                )
                return StockReversal.objects.create(
                    request_id=request_id, receipt=original, debit_entry=debit
                )
        except IntegrityError:
            existing = _prior_outcome(request_id, **context)
            if existing is not None:
                return existing
            raise


def reverse_transfer(*, transfer, actor, reason: str, request_id: UUID) -> StockReversal:
    """Move the transferred quantity back; the original destination must be RELEASED and the
    Lot must not be REJECTED at any warehouse (M6.2)."""
    _validate(transfer, StockTransfer, actor, reason, request_id)
    with transaction.atomic():
        original = (
            StockTransfer.objects.select_related(
                "source_entry__warehouse", "destination_entry__lot", "destination_entry__warehouse"
            )
            .filter(pk=transfer.pk)
            .first()
        )
        if original is None:
            raise ReversalValidationError("transfer must exist")
        source, destination = original.source_entry, original.destination_entry
        # Goods leave the original destination and return to the original source.
        try:
            lot, leaving, returning = lock_transfer_scope(
                lot=destination.lot,
                source_warehouse=destination.warehouse,
                destination_warehouse=source.warehouse,
            )
        except TransferQualityValidationError as exc:
            raise ReversalValidationError(str(exc)) from exc
        saved_actor = _lock_authority(actor, [leaving.pk, returning.pk])
        context = dict(field="transfer", original=original, actor=saved_actor, reason=reason)
        existing = _prior_outcome(request_id, **context)
        if existing is not None:
            return existing
        if get_lot_disposition(lot=lot, warehouse=leaving) != LotDisposition.RELEASED:
            raise ReversalQualityError("the original destination must be RELEASED")
        require_lot_not_rejected(lot)  # M6.2: REJECTED at another warehouse; a reversal moves stock
        quantity = destination.quantity_delta
        _require_balance(lot, leaving, quantity)
        try:
            with transaction.atomic():
                payload = dict(lot=lot, actor=saved_actor, reason=reason)
                debit = StockLedgerEntry.objects.create(
                    **payload, warehouse=leaving, quantity_delta=quantity.copy_negate()
                )
                credit = StockLedgerEntry.objects.create(
                    **payload, warehouse=returning, quantity_delta=quantity
                )
                return StockReversal.objects.create(
                    request_id=request_id,
                    transfer=original,
                    debit_entry=debit,
                    credit_entry=credit,
                )
        except IntegrityError:
            existing = _prior_outcome(request_id, **context)
            if existing is not None:
                return existing
            raise
