"""Inventory's Quality gate; callers still need authorization and atomic posting."""

from dataclasses import dataclass

from django.db import connection

from facilities.models import Warehouse
from quality.models import LotDisposition
from quality.services import get_lot_disposition

from .models import Lot


class TransferQualityValidationError(ValueError):
    pass


class TransferQualityError(Exception):
    pass


@dataclass(frozen=True)
class TransferQualityState:
    source_disposition: str
    destination_disposition: str


def lock_transfer_scope(*, lot, source_warehouse, destination_warehouse):
    """Validate persisted pairs and hold their identity locks until outer commit.

    Requires a caller-owned atomic READ COMMITTED transaction. The eventual transfer
    must check permissions and post both ledger entries in that SAME transaction.
    This gate writes nothing, does not reserve quantity, and never releases stock.
    """
    if not connection.in_atomic_block:
        raise TransferQualityValidationError("caller must open an atomic transaction")
    if connection.vendor != "postgresql":
        raise TransferQualityValidationError("PostgreSQL is required")
    for value, model in (
        (lot, Lot),
        (source_warehouse, Warehouse),
        (destination_warehouse, Warehouse),
    ):
        if not isinstance(value, model) or value.pk is None or value._state.adding:
            raise TransferQualityValidationError("lot and warehouses must be saved records")
    if source_warehouse.pk == destination_warehouse.pk:
        raise TransferQualityValidationError("warehouses must be distinct")

    with connection.cursor() as cursor:
        cursor.execute("SHOW transaction_isolation")
        if cursor.fetchone()[0] != "read committed":
            raise TransferQualityValidationError("READ COMMITTED is required")
    # Same leading lock as Quality transitions and existing Inventory posting.
    locked_lot = Lot.objects.select_for_update().filter(pk=lot.pk).first()
    if locked_lot is None:
        raise TransferQualityValidationError("lot must exist")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT organization_id FROM catalog_item WHERE id = %s FOR SHARE",
            [locked_lot.item_id],
        )
        item = cursor.fetchone()
        cursor.execute(
            "SELECT id, plant_id FROM facilities_warehouse "
            "WHERE id IN (%s, %s) ORDER BY id FOR SHARE",
            [source_warehouse.pk, destination_warehouse.pk],
        )
        warehouses = dict(cursor.fetchall())
        if item is None or len(warehouses) != 2:
            raise TransferQualityValidationError("transfer parents must exist")
        if len(set(warehouses.values())) != 1:
            raise TransferQualityValidationError("warehouses must share one Plant")
        cursor.execute(
            "SELECT organization_id FROM facilities_plant WHERE id = %s FOR SHARE",
            [warehouses[source_warehouse.pk]],
        )
        plant = cursor.fetchone()
    if plant is None or item[0] != plant[0]:
        raise TransferQualityValidationError("lot and warehouses must share one organization")

    # Refetch under the held locks: caller relation caches are not authoritative.
    source = Warehouse.objects.select_related("plant").get(pk=source_warehouse.pk)
    destination = Warehouse.objects.select_related("plant").get(pk=destination_warehouse.pk)
    return locked_lot, source, destination


def require_transfer_quality(*, lot, source_warehouse, destination_warehouse):
    """Require RELEASED source inside the caller transaction, retaining identity locks."""
    locked_lot, source, destination = lock_transfer_scope(
        lot=lot, source_warehouse=source_warehouse, destination_warehouse=destination_warehouse
    )
    state = TransferQualityState(
        source_disposition=get_lot_disposition(lot=locked_lot, warehouse=source),
        destination_disposition=get_lot_disposition(lot=locked_lot, warehouse=destination),
    )
    if state.source_disposition != LotDisposition.RELEASED:
        raise TransferQualityError("source Lot-Warehouse must be RELEASED")
    return state
