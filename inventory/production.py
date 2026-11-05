"""M5.2b (Issue #75): Inventory's posting interface for manufacturing.

CONSUME and SCRAP debit a Lot at a line; OUTPUT credits a Lot at an output warehouse.
Authority: PRODUCTION for CONSUME and OUTPUT, APPROVER for SCRAP (owner decision, 2026-11-04).
Locks follow receipts: Lot -> Item -> Warehouse -> Plant, then actor and grant. An exact
repeat of the request UUID replays (with current authority); any other reuse is a conflict.
Only manufacturing.services calls this, inside its own transaction, and links the result to
an order in that transaction.
"""

from decimal import Decimal
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from access_control.models import WarehouseRole, WarehouseRoleAssignment

from .models import ProductionPosting, StockLedgerEntry
from .quantities import is_valid_quantity
from .request_keys import owned_by_other_command
from .services import ReceiptValidationError, _lock_receipt_parents, get_stock_balance
from .transfers import InsufficientStockError

__all__ = [
    "InsufficientStockError",
    "PostingAuthorizationError",
    "PostingConflictError",
    "PostingValidationError",
    "post_production_posting",
]

ROLE = {
    "CONSUME": WarehouseRole.PRODUCTION,
    "SCRAP": WarehouseRole.APPROVER,
    "OUTPUT": WarehouseRole.PRODUCTION,
}


class PostingValidationError(ValueError):
    pass


class PostingAuthorizationError(Exception):
    pass


class PostingConflictError(Exception):
    pass


def _existing(request_id, *, kind, lot, warehouse, actor, quantity, reason):
    posting = (
        ProductionPosting.objects.select_related("ledger_entry")
        .filter(request_id=request_id)
        .first()
    )
    if posting is None:
        return None
    entry = posting.ledger_entry
    if (
        posting.kind == kind
        and entry.lot_id == lot.pk
        and entry.warehouse_id == warehouse.pk
        and entry.actor_id == actor.pk
        and abs(entry.quantity_delta) == quantity
        and entry.reason == reason
    ):
        return posting
    raise PostingConflictError("request_id was already used for another posting")


def post_production_posting(
    *, kind: str, lot, warehouse, actor, quantity: Decimal, reason: str, request_id: UUID
) -> ProductionPosting:
    if kind not in ROLE:
        raise PostingValidationError("kind must be CONSUME, SCRAP or OUTPUT")
    if not is_valid_quantity(quantity):
        raise PostingValidationError("quantity must be a positive Decimal below 10^14, six places")
    if not isinstance(reason, str) or not reason.strip():
        raise PostingValidationError("reason must be nonblank")
    if not isinstance(request_id, UUID):
        raise PostingValidationError("request_id must be a UUID")
    user_model = get_user_model()
    if not isinstance(actor, user_model) or actor.pk is None or actor._state.adding:
        raise PostingAuthorizationError("actor must be a saved active user")
    with transaction.atomic():
        try:
            lot = _lock_receipt_parents(lot, warehouse)
        except ReceiptValidationError as exc:
            raise PostingValidationError(str(exc)) from exc
        saved_actor = user_model.objects.select_for_update().filter(pk=actor.pk).first()
        granted = (
            WarehouseRoleAssignment.objects.select_for_update()
            .filter(user_id=actor.pk, warehouse_id=warehouse.pk, role=ROLE[kind])
            .exists()
        )
        if saved_actor is None or not saved_actor.is_active or not granted:
            raise PostingAuthorizationError(
                f"active {ROLE[kind]} authority at the warehouse is required"
            )
        command = dict(
            kind=kind,
            lot=lot,
            warehouse=warehouse,
            actor=saved_actor,
            quantity=quantity,
            reason=reason,
        )
        existing = _existing(request_id, **command)
        if existing is not None:
            return existing
        if owned_by_other_command(request_id, kind):
            raise PostingConflictError("request_id was already used by another command")
        debit = kind != "OUTPUT"
        if debit and get_stock_balance(lot=lot, warehouse=warehouse) < quantity:
            raise InsufficientStockError("balance is insufficient")
        try:
            with transaction.atomic():
                entry = StockLedgerEntry.objects.create(
                    lot=lot,
                    warehouse=warehouse,
                    actor=saved_actor,
                    reason=reason,
                    quantity_delta=quantity.copy_negate() if debit else quantity,
                )
                return ProductionPosting.objects.create(
                    kind=kind, ledger_entry=entry, request_id=request_id
                )
        except IntegrityError:
            existing = _existing(request_id, **command)
            if existing is not None:
                return existing
            if owned_by_other_command(request_id, kind):
                raise PostingConflictError(
                    "request_id was already used by another command"
                ) from None
            raise
