from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction

from access_control.policies import has_warehouse_role
from facilities.models import Warehouse
from inventory.models import Lot

from .models import LotDisposition, LotDispositionEvent


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
    if not has_warehouse_role(actor, warehouse, {"QUALITY"}):
        raise DispositionAuthorizationError(
            "actor needs an active QUALITY grant for this warehouse"
        )

    with transaction.atomic():
        locked_lot = Lot.objects.select_for_update().get(pk=lot.pk)
        _validate_pair(locked_lot, warehouse)

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

        if (
            expected_disposition not in LotDisposition.values
            or target_disposition not in LotDisposition.values
            or expected_disposition == target_disposition
        ):
            raise DispositionValidationError(
                "transition must change between HOLD and RELEASED"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise DispositionValidationError("reason must be nonblank")

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
            raise
