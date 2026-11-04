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
from django.db.models import Case, DecimalField, F, Max, Sum, When
from django.db.models.functions import Now

from access_control.models import WarehouseRole, WarehouseRoleAssignment
from catalog.models import Item, ItemType
from facilities.models import Warehouse
from inventory.models import Lot, StockTransfer
from inventory.quantities import is_valid_quantity
from inventory.request_keys import owned_by_other_command
from inventory.transfer_policy import TransferQualityError, TransferQualityValidationError
from inventory.transfers import (
    InsufficientStockError,
    TransferAuthorizationError,
    TransferConflictError,
    TransferValidationError,
    post_production_transfer,
)

from .models import (
    BillOfMaterials,
    BomLine,
    BomStatus,
    MovementKind,
    OrderStatus,
    ProductionMaterialMovement,
    ProductionOrder,
)

__all__ = [
    "BomAuthorizationError",
    "BomConflictError",
    "BomValidationError",
    "OrderAuthorizationError",
    "OrderConflictError",
    "OrderValidationError",
    "MaterialAuthorizationError",
    "MaterialConflictError",
    "MaterialLimitError",
    "MaterialQualityError",
    "MaterialValidationError",
    "approve_bom",
    "issue_material",
    "return_material",
    "cancel_production_order",
    "create_bom_draft",
    "create_production_order",
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
        # of=("self",): lock only BOM rows; the joined item row stays free for stock commands.
        versions = list(
            BillOfMaterials.objects.select_for_update(of=("self",))
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
        if not target.lines.exists():
            raise BomValidationError("a BOM needs at least one line before approval")
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


# ---------------------------------------------------------------- production orders


class OrderValidationError(ValueError):
    pass


class OrderAuthorizationError(Exception):
    pass


class OrderConflictError(Exception):
    pass


def _require_production_at(actor: Any, warehouse_ids: set[int]) -> None:
    granted = {
        grant.warehouse_id
        for grant in WarehouseRoleAssignment.objects.select_for_update()
        .filter(user_id=actor.pk, warehouse_id__in=warehouse_ids, role=WarehouseRole.PRODUCTION)
        .order_by("warehouse_id")
    }
    if granted != warehouse_ids:
        raise OrderAuthorizationError("PRODUCTION at the line and output warehouses is required")


def _order_replay(request_id: UUID, *, bom, quantity, line, output, actor) -> Any:
    prior = ProductionOrder.objects.filter(request_id=request_id).first()
    if prior is None:
        if owned_by_other_command(request_id, "ORDER_CREATE"):
            raise OrderConflictError("request_id was already used by another command")
        return None
    if (
        prior.bom_id == bom.pk
        and prior.quantity == quantity
        and prior.line_warehouse_id == line.pk
        and prior.output_warehouse_id == output.pk
        and prior.created_by_id == actor.pk
    ):
        return prior
    raise OrderConflictError("request_id was already used for another production order")


def create_production_order(
    *,
    bom: BillOfMaterials,
    quantity: Decimal,
    line_warehouse: Warehouse,
    output_warehouse: Warehouse,
    actor: Any,
    request_id: UUID,
) -> ProductionOrder:
    """Open an order for `quantity` units of the BOM item on its ACTIVE version."""
    if not _saved(bom, BillOfMaterials):
        raise OrderValidationError("bom must be a saved BillOfMaterials")
    if not is_valid_quantity(quantity):
        raise OrderValidationError(
            "quantity must be a positive Decimal below 10^14 with at most six places"
        )
    if not _saved(line_warehouse, Warehouse) or not _saved(output_warehouse, Warehouse):
        raise OrderValidationError("line and output warehouses must be saved Warehouses")
    if line_warehouse.pk == output_warehouse.pk:
        raise OrderValidationError("line and output warehouses must differ")
    if not isinstance(request_id, UUID):
        raise OrderValidationError("request_id must be a UUID")
    with transaction.atomic():
        # FOR UPDATE on the BOM row queues this order behind (or ahead of) an approval.
        locked = (
            BillOfMaterials.objects.select_for_update(of=("self",))
            .select_related("item")
            .filter(pk=bom.pk)
            .first()
        )
        if locked is None:
            raise OrderValidationError("bom must exist")
        plants = Warehouse.objects.filter(
            pk__in=(line_warehouse.pk, output_warehouse.pk)
        ).values_list("plant_id", "plant__organization_id")
        if len(set(plants)) != 1 or next(iter(plants))[1] != locked.item.organization_id:
            raise OrderValidationError("warehouses must share one plant of the item organization")
        saved_actor = _lock_actor(actor, OrderAuthorizationError)
        _require_production_at(saved_actor, {line_warehouse.pk, output_warehouse.pk})
        replay = _order_replay(
            request_id,
            bom=locked,
            quantity=quantity,
            line=line_warehouse,
            output=output_warehouse,
            actor=saved_actor,
        )
        if replay is not None:
            return replay
        if locked.status != BomStatus.ACTIVE:
            raise OrderValidationError("a production order needs an ACTIVE BOM")
        try:
            with transaction.atomic():
                return ProductionOrder.objects.create(
                    bom=locked,
                    quantity=quantity,
                    line_warehouse=line_warehouse,
                    output_warehouse=output_warehouse,
                    created_by=saved_actor,
                    request_id=request_id,
                )
        except IntegrityError:
            replay = _order_replay(
                request_id,
                bom=locked,
                quantity=quantity,
                line=line_warehouse,
                output=output_warehouse,
                actor=saved_actor,
            )
            if replay is not None:
                return replay
            raise OrderConflictError("request_id was already used") from None


def _cancel_replay(request_id: UUID, order: ProductionOrder, actor: Any, reason: str) -> Any:
    prior = ProductionOrder.objects.filter(cancel_request_id=request_id).first()
    if prior is None:
        if owned_by_other_command(request_id, "ORDER_CANCEL"):
            raise OrderConflictError("request_id was already used by another command")
        return None
    if prior.pk == order.pk and prior.cancelled_by_id == actor.pk and prior.cancel_reason == reason:
        return prior
    raise OrderConflictError("request_id was already used for another cancellation")


def cancel_production_order(
    *, order: ProductionOrder, actor: Any, reason: str, request_id: UUID
) -> ProductionOrder:
    """Cancel an OPEN order; the record and its BOM link stay."""
    if not _saved(order, ProductionOrder):
        raise OrderValidationError("order must be a saved ProductionOrder")
    if not isinstance(reason, str) or not reason.strip():
        raise OrderValidationError("reason must be nonblank")
    if not isinstance(request_id, UUID):
        raise OrderValidationError("request_id must be a UUID")
    with transaction.atomic():
        locked = ProductionOrder.objects.select_for_update().filter(pk=order.pk).first()
        if locked is None:
            raise OrderValidationError("order must exist")
        saved_actor = _lock_actor(actor, OrderAuthorizationError)
        _require_production_at(saved_actor, {locked.line_warehouse_id, locked.output_warehouse_id})
        replay = _cancel_replay(request_id, locked, saved_actor, reason)
        if replay is not None:
            return replay
        if locked.status != OrderStatus.OPEN:
            raise OrderValidationError("only an OPEN order can be cancelled")
        if any(_order_holdings(locked).values()):
            raise OrderValidationError("return the material on the line before cancelling")
        try:
            with transaction.atomic():
                ProductionOrder.objects.filter(pk=locked.pk).update(
                    status=OrderStatus.CANCELLED,
                    cancelled_by=saved_actor,
                    cancelled_at=Now(),
                    cancel_reason=reason,
                    cancel_request_id=request_id,
                )
        except IntegrityError:
            replay = _cancel_replay(request_id, locked, saved_actor, reason)
            if replay is not None:
                return replay
            raise OrderConflictError("request_id was already used") from None
        locked.refresh_from_db()
        return locked


# ---------------------------------------------------------------- material issue and return
# M5.2a (Issue #72). Owner rules: net issue (issued - returned) per component never exceeds
# order quantity x quantity_per; the issue source must be RELEASED. Inventory posts the
# transfer (post_production_transfer); this module links it to the order. Lock order: the
# order row, then Inventory's Lot -> Item -> Warehouses -> Plant -> actor -> grants.


class MaterialValidationError(ValueError):
    pass


class MaterialAuthorizationError(Exception):
    pass


class MaterialConflictError(Exception):
    pass


class MaterialLimitError(Exception):
    pass


class MaterialQualityError(Exception):
    pass


_SIGNED = Case(
    When(kind=MovementKind.ISSUE, then=F("transfer__destination_entry__quantity_delta")),
    default=-F("transfer__destination_entry__quantity_delta"),
    output_field=DecimalField(),
)


def _order_holdings(order: ProductionOrder) -> dict[int, Decimal]:
    """Net quantity per Lot the order holds on its line."""
    rows = (
        ProductionMaterialMovement.objects.filter(order=order)
        .values("transfer__destination_entry__lot_id")
        .annotate(net=Sum(_SIGNED))
    )
    return {row["transfer__destination_entry__lot_id"]: row["net"] for row in rows}


def _net_issued(order: ProductionOrder, item_id: int) -> Decimal:
    total = ProductionMaterialMovement.objects.filter(
        order=order, transfer__destination_entry__lot__item_id=item_id
    ).aggregate(net=Sum(_SIGNED))["net"]
    return total or Decimal("0")


def _material_replay(request_id: UUID, order: ProductionOrder, kind: str) -> Any:
    transfer = StockTransfer.objects.filter(request_id=request_id).first()
    if transfer is None:
        return None
    movement = ProductionMaterialMovement.objects.filter(transfer=transfer).first()
    if movement is None or movement.order_id != order.pk or movement.kind != kind:
        raise MaterialConflictError("request_id was already used for another movement")
    return movement


def _move_material(*, kind, order, lot, other_warehouse, quantity, actor, reason, request_id):
    if not _saved(order, ProductionOrder) or not _saved(lot, Lot):
        raise MaterialValidationError("order and lot must be saved records")
    if not _saved(other_warehouse, Warehouse):
        raise MaterialValidationError("warehouse must be a saved Warehouse")
    if not is_valid_quantity(quantity):
        raise MaterialValidationError(
            "quantity must be a positive Decimal below 10^14 with at most six places"
        )
    if not isinstance(request_id, UUID):
        raise MaterialValidationError("request_id must be a UUID")
    with transaction.atomic():
        locked = ProductionOrder.objects.select_for_update().filter(pk=order.pk).first()
        if locked is None:
            raise MaterialValidationError("order must exist")
        line = locked.line_warehouse
        if other_warehouse.pk == line.pk:
            raise MaterialValidationError("the other warehouse must not be the order line")
        source, destination = (
            (other_warehouse, line) if kind == MovementKind.ISSUE else (line, other_warehouse)
        )
        prior = _material_replay(request_id, locked, kind)
        if prior is None:
            # Unlocked read for an early, informative refusal; Inventory locks and re-checks.
            if (
                not WarehouseRoleAssignment.objects.filter(
                    user_id=getattr(actor, "pk", None),
                    warehouse_id__in=(source.pk, destination.pk),
                    role=WarehouseRole.PRODUCTION,
                    user__is_active=True,
                ).count()
                == 2
            ):
                raise MaterialAuthorizationError("PRODUCTION at both warehouses is required")
            if locked.status != OrderStatus.OPEN:
                raise MaterialValidationError("material moves only for an OPEN order")
            per = (
                BomLine.objects.filter(bom_id=locked.bom_id, component_id=lot.item_id)
                .values_list("quantity_per", flat=True)
                .first()
            )
            if per is None:
                raise MaterialValidationError("the Lot item is not a component of the order BOM")
            if kind == MovementKind.ISSUE:
                if _net_issued(locked, lot.item_id) + quantity > locked.quantity * per:
                    raise MaterialLimitError("net issue would exceed the BOM requirement")
            elif _order_holdings(locked).get(lot.pk, Decimal("0")) < quantity:
                raise MaterialLimitError("the order holds less of this Lot on its line")
        try:
            debit, _ = post_production_transfer(
                lot=lot,
                source_warehouse=source,
                destination_warehouse=destination,
                actor=actor,
                quantity=quantity,
                reason=reason,
                request_id=request_id,
                quality_at_source=kind == MovementKind.ISSUE,
            )
        except TransferAuthorizationError as exc:
            raise MaterialAuthorizationError(str(exc)) from exc
        except TransferQualityError as exc:
            raise MaterialQualityError(str(exc)) from exc
        except TransferConflictError as exc:
            raise MaterialConflictError(str(exc)) from exc
        except InsufficientStockError as exc:
            raise MaterialLimitError(str(exc)) from exc
        except (TransferValidationError, TransferQualityValidationError) as exc:
            raise MaterialValidationError(str(exc)) from exc
        if prior is not None:
            return prior
        return ProductionMaterialMovement.objects.create(
            order=locked, kind=kind, transfer=debit.transfer_out
        )


def issue_material(
    *,
    order: ProductionOrder,
    lot: Lot,
    source_warehouse: Warehouse,
    quantity: Decimal,
    actor: Any,
    reason: str,
    request_id: UUID,
) -> ProductionMaterialMovement:
    """Move a component Lot from a stock warehouse onto the order's line."""
    return _move_material(
        kind=MovementKind.ISSUE,
        order=order,
        lot=lot,
        other_warehouse=source_warehouse,
        quantity=quantity,
        actor=actor,
        reason=reason,
        request_id=request_id,
    )


def return_material(
    *,
    order: ProductionOrder,
    lot: Lot,
    destination_warehouse: Warehouse,
    quantity: Decimal,
    actor: Any,
    reason: str,
    request_id: UUID,
) -> ProductionMaterialMovement:
    """Move material the order holds on its line back to a warehouse where the Lot is RELEASED."""
    return _move_material(
        kind=MovementKind.RETURN,
        order=order,
        lot=lot,
        other_warehouse=destination_warehouse,
        quantity=quantity,
        actor=actor,
        reason=reason,
        request_id=request_id,
    )
