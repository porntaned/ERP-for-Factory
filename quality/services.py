from decimal import Decimal
from typing import Any
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from access_control.models import WarehouseRole, WarehouseRoleAssignment
from facilities.models import Warehouse
from inventory.models import Lot
from inventory.quantities import is_valid_quantity
from inventory.request_keys import owned_by_other_command

from .models import (
    InspectionKind,
    InspectionResult,
    LotDisposition,
    LotDispositionEvent,
    LotInspection,
)


class DispositionAuthorizationError(Exception):
    pass


class DispositionConflictError(Exception):
    pass


class DispositionValidationError(Exception):
    pass


def _validate_pair(lot: Any, warehouse: Any) -> None:
    if (
        not isinstance(lot, Lot)
        or lot.pk is None
        or not isinstance(warehouse, Warehouse)
        or warehouse.pk is None
    ):
        raise DispositionValidationError("lot and warehouse must be saved records")
    if lot.item.organization_id != warehouse.plant.organization_id:
        raise DispositionValidationError("lot and warehouse must belong to one organization")


def _event_matches_request(
    event: LotDispositionEvent,
    *,
    lot: Lot,
    warehouse: Warehouse,
    actor: Any,
    expected_disposition: str,
    target_disposition: str,
    reason: str,
) -> bool:
    return (
        event.lot_id == lot.pk
        and event.warehouse_id == warehouse.pk
        and event.actor_id == actor.pk
        and event.from_disposition == expected_disposition
        and event.to_disposition == target_disposition
        and event.reason == reason
    )


def _resolve_existing_request(
    request_id: UUID,
    *,
    lot: Lot,
    warehouse: Warehouse,
    actor: Any,
    expected_disposition: str,
    target_disposition: str,
    reason: str,
) -> LotDispositionEvent | None:
    event = LotDispositionEvent.objects.filter(request_id=request_id).first()
    if event is None:
        return None
    if _event_matches_request(
        event,
        lot=lot,
        warehouse=warehouse,
        actor=actor,
        expected_disposition=expected_disposition,
        target_disposition=target_disposition,
        reason=reason,
    ):
        return event
    raise DispositionConflictError("request_id was already used for another command")


def _lock_actor_with_role(actor: Any, warehouse: Warehouse, role: str) -> Any:
    """Lock the saved actor, then their grant; refuse unless both are active."""
    user_model = get_user_model()
    if not isinstance(actor, user_model) or actor.pk is None or actor._state.adding:
        raise DispositionAuthorizationError("actor must be a saved active user")
    saved_actor = user_model.objects.select_for_update().filter(pk=actor.pk).first()
    grant = (
        WarehouseRoleAssignment.objects.select_for_update()
        .filter(user_id=actor.pk, warehouse_id=warehouse.pk, role=role)
        .first()
    )
    if saved_actor is None or not saved_actor.is_active or grant is None:
        raise DispositionAuthorizationError(
            f"actor needs an active {role} grant for this warehouse"
        )
    return saved_actor


def _lock_quality_actor(actor: Any, warehouse: Warehouse) -> Any:
    return _lock_actor_with_role(actor, warehouse, WarehouseRole.QUALITY)


def get_lot_disposition(*, lot: Lot, warehouse: Warehouse) -> str:
    _validate_pair(lot, warehouse)
    latest = (
        LotDispositionEvent.objects.filter(lot=lot, warehouse=warehouse)
        .order_by("-id")
        .values_list("to_disposition", flat=True)
        .first()
    )
    return latest or LotDisposition.HOLD


def transition_lot_disposition(
    *,
    lot: Lot,
    warehouse: Warehouse,
    actor: Any,
    expected_disposition: str,
    target_disposition: str,
    reason: str,
    request_id: UUID,
) -> LotDispositionEvent:
    _validate_pair(lot, warehouse)
    if not isinstance(request_id, UUID):
        raise DispositionValidationError("request_id must be a UUID")
    with transaction.atomic():
        locked_lot = Lot.objects.select_for_update().get(pk=lot.pk)
        _validate_pair(locked_lot, warehouse)
        actor = _lock_quality_actor(actor, warehouse)

        existing = _resolve_existing_request(
            request_id,
            lot=locked_lot,
            warehouse=warehouse,
            actor=actor,
            expected_disposition=expected_disposition,
            target_disposition=target_disposition,
            reason=reason,
        )
        if existing is not None:
            return existing

        # M6.1 (Issue #96): only RELEASED -> HOLD stays here. Leaving HOLD takes an inspection,
        # and a REJECTED Lot returns to HOLD only through an APPROVER.
        if (expected_disposition, target_disposition) != (
            LotDisposition.RELEASED,
            LotDisposition.HOLD,
        ):
            raise DispositionValidationError(
                "this command only holds a RELEASED Lot; use record_inspection to leave HOLD "
                "and return_rejected_to_hold for a REJECTED Lot"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise DispositionValidationError("reason must be nonblank")

        if owned_by_other_command(request_id, "DISPOSITION"):
            raise DispositionConflictError("request_id was already used by another command")

        current_disposition = get_lot_disposition(lot=locked_lot, warehouse=warehouse)
        if current_disposition != expected_disposition:
            raise DispositionConflictError(
                f"expected {expected_disposition}, current state is {current_disposition}"
            )

        try:
            with transaction.atomic():
                return LotDispositionEvent.objects.create(
                    lot=locked_lot,
                    warehouse=warehouse,
                    actor=actor,
                    request_id=request_id,
                    from_disposition=expected_disposition,
                    to_disposition=target_disposition,
                    reason=reason,
                )
        except IntegrityError:
            existing = _resolve_existing_request(
                request_id,
                lot=locked_lot,
                warehouse=warehouse,
                actor=actor,
                expected_disposition=expected_disposition,
                target_disposition=target_disposition,
                reason=reason,
            )
            if existing is not None:
                return existing
            if owned_by_other_command(request_id, "DISPOSITION"):
                raise DispositionConflictError("request_id was already used by another command")
            raise


# ---------------------------------------------------------------- inspection (M6.1, Issue #96)
# Owner rulings 2026-11-06: QUALITY at the warehouse inspects and decides in one command;
# PASS -> RELEASED, FAIL -> REJECTED; kind comes from the Lot's origin; the sample may not exceed
# the balance at that warehouse; the note is required. The event carries the request key
# (registered as DISPOSITION) and links its inspection; PostgreSQL re-checks the rules.


class InspectionValidationError(DispositionValidationError):
    pass


class InspectionConflictError(DispositionConflictError):
    pass


_OUTCOME = {
    InspectionResult.PASS: LotDisposition.RELEASED,
    InspectionResult.FAIL: LotDisposition.REJECTED,
}


def inspection_kind(lot: Lot) -> str | None:
    """FINAL when the Lot has an OUTPUT posting, otherwise INCOMING when it has a receipt."""
    from inventory.models import ProductionPosting, StockReceipt

    if ProductionPosting.objects.filter(kind="OUTPUT", ledger_entry__lot_id=lot.pk).exists():
        return InspectionKind.FINAL
    if StockReceipt.objects.filter(ledger_entry__lot_id=lot.pk).exists():
        return InspectionKind.INCOMING
    return None


def _inspection_replay(request_id, *, lot, warehouse, actor, result, sample_quantity, note):
    event = (
        LotDispositionEvent.objects.select_related("inspection")
        .filter(request_id=request_id)
        .first()
    )
    if event is None:
        if owned_by_other_command(request_id, "DISPOSITION"):
            raise InspectionConflictError("request_id was already used by another command")
        return None
    found = event.inspection
    if (
        found is not None
        and found.lot_id == lot.pk
        and found.warehouse_id == warehouse.pk
        and found.inspector_id == actor.pk
        and found.result == result
        and found.sample_quantity == sample_quantity
        and found.note == note
    ):
        return found
    raise InspectionConflictError("request_id was already used for another command")


def record_inspection(
    *,
    lot: Lot,
    warehouse: Warehouse,
    result: str,
    sample_quantity: Decimal,
    note: str,
    actor: Any,
    request_id: UUID,
) -> LotInspection:
    """Inspect a HOLD Lot-Warehouse and move it to RELEASED (PASS) or REJECTED (FAIL)."""
    from inventory.services import get_stock_balance

    _validate_pair(lot, warehouse)
    if result not in InspectionResult.values:
        raise InspectionValidationError("result must be PASS or FAIL")
    if not is_valid_quantity(sample_quantity):
        raise InspectionValidationError(
            "sample_quantity must be a positive Decimal below 10^14 with at most six places"
        )
    if not isinstance(note, str) or not note.strip():
        raise InspectionValidationError("note must be nonblank")
    if not isinstance(request_id, UUID):
        raise InspectionValidationError("request_id must be a UUID")
    with transaction.atomic():
        locked_lot = Lot.objects.select_for_update().get(pk=lot.pk)
        saved_actor = _lock_quality_actor(actor, warehouse)
        replay = _inspection_replay(
            request_id,
            lot=locked_lot,
            warehouse=warehouse,
            actor=saved_actor,
            result=result,
            sample_quantity=sample_quantity,
            note=note,
        )
        if replay is not None:
            return replay
        kind = inspection_kind(locked_lot)
        if kind is None:
            raise InspectionValidationError(
                "the Lot has no origin (no receipt or output) to inspect"
            )
        current = get_lot_disposition(lot=locked_lot, warehouse=warehouse)
        if current != LotDisposition.HOLD:
            raise InspectionConflictError(
                f"only a HOLD Lot can be inspected; current state is {current}"
            )
        on_hand = get_stock_balance(lot=locked_lot, warehouse=warehouse)
        if sample_quantity > on_hand:
            raise InspectionValidationError(
                f"sample_quantity exceeds the balance at this warehouse ({on_hand.normalize():f})"
            )
        try:
            with transaction.atomic():
                inspection = LotInspection.objects.create(
                    lot=locked_lot,
                    warehouse=warehouse,
                    kind=kind,
                    result=result,
                    sample_quantity=sample_quantity,
                    note=note,
                    inspector=saved_actor,
                )
                LotDispositionEvent.objects.create(
                    lot=locked_lot,
                    warehouse=warehouse,
                    actor=saved_actor,
                    request_id=request_id,
                    from_disposition=LotDisposition.HOLD,
                    to_disposition=_OUTCOME[result],
                    reason=note,
                    inspection=inspection,
                )
        except IntegrityError:
            replay = _inspection_replay(
                request_id,
                lot=locked_lot,
                warehouse=warehouse,
                actor=saved_actor,
                result=result,
                sample_quantity=sample_quantity,
                note=note,
            )
            if replay is not None:
                return replay
            raise
        inspection.refresh_from_db()
        return inspection


def _rejecting_inspector_id(lot: Lot, warehouse: Warehouse) -> int | None:
    event = (
        LotDispositionEvent.objects.filter(
            lot=lot, warehouse=warehouse, to_disposition=LotDisposition.REJECTED
        )
        .order_by("-id")
        .select_related("inspection")
        .first()
    )
    return event.inspection.inspector_id if event and event.inspection else None


def return_rejected_to_hold(
    *, lot: Lot, warehouse: Warehouse, actor: Any, reason: str, request_id: UUID
) -> LotDispositionEvent:
    """An APPROVER who did not reject the Lot sends a REJECTED Lot-Warehouse back to HOLD."""
    _validate_pair(lot, warehouse)
    if not isinstance(reason, str) or not reason.strip():
        raise DispositionValidationError("reason must be nonblank")
    if not isinstance(request_id, UUID):
        raise DispositionValidationError("request_id must be a UUID")
    with transaction.atomic():
        locked_lot = Lot.objects.select_for_update().get(pk=lot.pk)
        saved_actor = _lock_actor_with_role(actor, warehouse, WarehouseRole.APPROVER)
        request = dict(
            lot=locked_lot,
            warehouse=warehouse,
            actor=saved_actor,
            expected_disposition=LotDisposition.REJECTED,
            target_disposition=LotDisposition.HOLD,
            reason=reason,
        )
        existing = _resolve_existing_request(request_id, **request)
        if existing is not None:
            return existing
        if owned_by_other_command(request_id, "DISPOSITION"):
            raise DispositionConflictError("request_id was already used by another command")
        current = get_lot_disposition(lot=locked_lot, warehouse=warehouse)
        if current != LotDisposition.REJECTED:
            raise DispositionConflictError(f"expected REJECTED, current state is {current}")
        if _rejecting_inspector_id(locked_lot, warehouse) == saved_actor.pk:
            raise DispositionAuthorizationError(
                "the inspector who rejected this Lot cannot return it to HOLD"
            )
        try:
            with transaction.atomic():
                return LotDispositionEvent.objects.create(
                    lot=locked_lot,
                    warehouse=warehouse,
                    actor=saved_actor,
                    request_id=request_id,
                    from_disposition=LotDisposition.REJECTED,
                    to_disposition=LotDisposition.HOLD,
                    reason=reason,
                )
        except IntegrityError:
            existing = _resolve_existing_request(request_id, **request)
            if existing is not None:
                return existing
            raise
