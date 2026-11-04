"""M5.1 (Issue #69): the only writers of BOMs and production orders.

Owner rules (2026-11-04): PRODUCTION drafts a BOM; an APPROVER who is not the creator activates
it, which retires the previous ACTIVE version; an ACTIVE version is locked. Every command takes
a request UUID: an exact repeat replays the stored record, any other reuse is a conflict, and
keys share inventory's registry. PostgreSQL re-checks every rule (migration 0002).

Lock order, shared by every command so they queue instead of deadlocking:
BOM rows of the item (by id) -> actor -> role grants.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.db.models.functions import Now

from access_control.models import WarehouseRole, WarehouseRoleAssignment
from catalog.models import Item, ItemType
from inventory.quantities import is_valid_quantity
from inventory.request_keys import owned_by_other_command

from .models import BillOfMaterials, BomLine, BomStatus

__all__ = [
    "BomAuthorizationError",
    "BomConflictError",
    "BomValidationError",
    "approve_bom",
    "create_bom_draft",
]


class BomValidationError(ValueError):
    pass


class BomAuthorizationError(Exception):
    pass


class BomConflictError(Exception):
    pass


def _saved(value: Any, model: type) -> bool:
    return isinstance(value, model) and value.pk is not None and not value._state.adding


def _lock_actor(actor: Any, error: type[Exception]) -> Any:
    if not _saved(actor, get_user_model()):
        raise error("actor must be a saved active user")
    saved = get_user_model().objects.select_for_update().filter(pk=actor.pk).first()
    if saved is None or not saved.is_active:
        raise error("actor must be a saved active user")
    return saved


def _holds_role_in_organization(actor: Any, organization_id: int, role: str) -> bool:
    return (
        WarehouseRoleAssignment.objects.select_for_update(of=("self",))
        .filter(user_id=actor.pk, role=role, warehouse__plant__organization_id=organization_id)
        .order_by("id")
        .exists()
    )


# ---------------------------------------------------------------- drafts


def _validate_draft(item: Any, lines: Any, request_id: Any) -> dict[int, tuple[Item, Decimal]]:
    if not _saved(item, Item):
        raise BomValidationError("item must be a saved Item")
    if item.item_type not in (ItemType.FINISHED, ItemType.WIP):
        raise BomValidationError("a BOM is for a FINISHED or WIP item")
    if not isinstance(request_id, UUID):
        raise BomValidationError("request_id must be a UUID")
    if not isinstance(lines, (list, tuple)) or not lines:
        raise BomValidationError("a BOM needs at least one line")
    by_component: dict[int, tuple[Item, Decimal]] = {}
    for line in lines:
        if not isinstance(line, (list, tuple)) or len(line) != 2:
            raise BomValidationError("each line is a (component, quantity) pair")
        component, quantity = line
        if not _saved(component, Item):
            raise BomValidationError("component must be a saved Item")
        if component.item_type not in (ItemType.RAW, ItemType.WIP):
            raise BomValidationError("a BOM component is a RAW or WIP item")
        if component.organization_id != item.organization_id:
            raise BomValidationError("a BOM component belongs to the item's organization")
        if component.pk == item.pk:
            raise BomValidationError("a BOM item cannot be its own component")
        if component.pk in by_component:
            raise BomValidationError("each component appears once")
        if not is_valid_quantity(quantity):
            raise BomValidationError(
                "quantity_per must be a positive Decimal below 10^14 with at most six places"
            )
        by_component[component.pk] = (component, quantity)
    return by_component


def _draft_replay(request_id: UUID, item: Item, actor: Any, by_component: dict) -> Any:
    bom = BillOfMaterials.objects.filter(request_id=request_id).first()
    if bom is None:
        if owned_by_other_command(request_id, "BOM_DRAFT"):
            raise BomConflictError("request_id was already used by another command")
        return None
    stored = dict(bom.lines.values_list("component_id", "quantity_per"))
    wanted = {pk: quantity for pk, (_, quantity) in by_component.items()}
    if bom.item_id == item.pk and bom.created_by_id == actor.pk and stored == wanted:
        return bom
    raise BomConflictError("request_id was already used for another BOM draft")


def create_bom_draft(
    *, item: Item, lines: Sequence[tuple[Item, Decimal]], actor: Any, request_id: UUID
) -> BillOfMaterials:
    """Create the item's next BOM version as DRAFT with its lines."""
    by_component = _validate_draft(item, lines, request_id)
    with transaction.atomic():
        # NO KEY UPDATE serializes drafts of one item without blocking FK checks on the item.
        locked = Item.objects.select_for_update(no_key=True).filter(pk=item.pk).first()
        if locked is None:
            raise BomValidationError("item must exist")
        saved_actor = _lock_actor(actor, BomAuthorizationError)
        # Authority first: even an exact replay needs current authority (as M4.3.6).
        if not _holds_role_in_organization(
            saved_actor, locked.organization_id, WarehouseRole.PRODUCTION
        ):
            raise BomAuthorizationError("PRODUCTION in the item's organization is required")
        replay = _draft_replay(request_id, locked, saved_actor, by_component)
        if replay is not None:
            return replay
        version = (locked.boms.aggregate(top=Max("version"))["top"] or 0) + 1
        try:
            with transaction.atomic():
                bom = BillOfMaterials.objects.create(
                    item=locked, version=version, created_by=saved_actor, request_id=request_id
                )
                BomLine.objects.bulk_create(
                    BomLine(bom=bom, component_id=pk, quantity_per=quantity)
                    for pk, (_, quantity) in by_component.items()
                )
        except IntegrityError:
            # A concurrent writer took the key first; replay it or report the conflict.
            replay = _draft_replay(request_id, locked, saved_actor, by_component)
            if replay is not None:
                return replay
            raise BomConflictError("request_id was already used") from None
        return bom


# ---------------------------------------------------------------- approval


def _approval_replay(request_id: UUID, bom: BillOfMaterials, actor: Any) -> Any:
    prior = BillOfMaterials.objects.filter(approval_request_id=request_id).first()
    if prior is not None:
        if prior.pk == bom.pk and prior.approved_by_id == actor.pk:
            return prior
        raise BomConflictError("request_id was already used for another approval")
    if owned_by_other_command(request_id, "BOM_APPROVE"):
        raise BomConflictError("request_id was already used by another command")
    return None


def approve_bom(*, bom: BillOfMaterials, actor: Any, request_id: UUID) -> BillOfMaterials:
    """Activate a DRAFT version and retire the item's previous ACTIVE version, atomically."""
    if not _saved(bom, BillOfMaterials):
        raise BomValidationError("bom must be a saved BillOfMaterials")
    if not isinstance(request_id, UUID):
        raise BomValidationError("request_id must be a UUID")
    with transaction.atomic():
        versions = list(
            BillOfMaterials.objects.select_for_update()
            .filter(item_id=bom.item_id)
            .select_related("item")
            .order_by("id")
        )
        target = next((v for v in versions if v.pk == bom.pk), None)
        if target is None:
            raise BomValidationError("bom must exist")
        saved_actor = _lock_actor(actor, BomAuthorizationError)
        if not _holds_role_in_organization(
            saved_actor, target.item.organization_id, WarehouseRole.APPROVER
        ):
            raise BomAuthorizationError("APPROVER in the item's organization is required")
        # Replay before the status check: a stored approval may since have been retired.
        replay = _approval_replay(request_id, target, saved_actor)
        if replay is not None:
            return replay
        if target.status != BomStatus.DRAFT:
            raise BomValidationError("only a DRAFT can be approved")
        if saved_actor.pk == target.created_by_id:
            raise BomAuthorizationError("the approver must not be the creator")
        try:
            with transaction.atomic():
                # Retire first: the one-ACTIVE index is checked per statement.
                BillOfMaterials.objects.filter(
                    item_id=target.item_id, status=BomStatus.ACTIVE
                ).update(status=BomStatus.RETIRED)
                BillOfMaterials.objects.filter(pk=target.pk).update(
                    status=BomStatus.ACTIVE,
                    approved_by=saved_actor,
                    approved_at=Now(),
                    approval_request_id=request_id,
                )
        except IntegrityError:
            replay = _approval_replay(request_id, target, saved_actor)
            if replay is not None:
                return replay
            raise BomConflictError("request_id was already used") from None
        target.refresh_from_db()
        return target
