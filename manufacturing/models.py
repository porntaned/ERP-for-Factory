"""M5.1 (Issue #69): versioned bills of materials and production orders.

Column rules live here; cross-table and lifecycle rules are PostgreSQL triggers in the
migrations. Records are written only by the commands in manufacturing.services. No stock moves.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now, Round

from catalog.models import Item
from facilities.models import Warehouse
from inventory.fields import ExactQuantityField
from inventory.models import StockTransfer

QUANTITY_LIMIT = Decimal("100000000000000")


def _quantity_checks(field, prefix):
    return [
        models.CheckConstraint(
            condition=Q(**{f"{field}__gt": 0}) & Q(**{f"{field}__lt": QUANTITY_LIMIT}),
            name=f"{prefix}_positive",
        ),
        models.CheckConstraint(
            condition=Q(**{field: Round(field, precision=6)}),
            name=f"{prefix}_six_places",
        ),
    ]


class BomStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    RETIRED = "RETIRED", "Retired"


class OrderStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    CANCELLED = "CANCELLED", "Cancelled"


class BillOfMaterials(models.Model):
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="boms")
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=8, choices=BomStatus, default=BomStatus.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(db_default=Now(), editable=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    approved_at = models.DateTimeField(null=True)
    request_id = models.UUIDField(unique=True)
    approval_request_id = models.UUIDField(null=True, unique=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(version__gte=1), name="bom_version_positive"),
            models.CheckConstraint(
                condition=Q(status__in=BomStatus.values), name="bom_status_valid"
            ),
            models.UniqueConstraint(fields=("item", "version"), name="bom_item_version_unique"),
            models.UniqueConstraint(
                fields=("item",), condition=Q(status="ACTIVE"), name="bom_one_active_per_item"
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="DRAFT",
                        approved_by__isnull=True,
                        approved_at__isnull=True,
                        approval_request_id__isnull=True,
                    )
                    | (
                        Q(status__in=("ACTIVE", "RETIRED"))
                        & Q(approved_by__isnull=False)
                        & Q(approved_at__isnull=False)
                        & Q(approval_request_id__isnull=False)
                    )
                ),
                name="bom_approval_matches_status",
            ),
            models.CheckConstraint(
                condition=Q(approved_by__isnull=True) | ~Q(approved_by=models.F("created_by")),
                name="bom_approver_not_creator",
            ),
        ]


class BomLine(models.Model):
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.PROTECT, related_name="lines")
    component = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="+")
    quantity_per = ExactQuantityField(max_digits=20, decimal_places=6)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("bom", "component"), name="bom_line_component_unique"),
            *_quantity_checks("quantity_per", "bom_line_quantity"),
        ]


class ProductionOrder(models.Model):
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.PROTECT, related_name="orders")
    quantity = ExactQuantityField(max_digits=20, decimal_places=6)
    line_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="+")
    output_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=9, choices=OrderStatus, default=OrderStatus.OPEN)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(db_default=Now(), editable=False)
    request_id = models.UUIDField(unique=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    cancelled_at = models.DateTimeField(null=True)
    cancel_reason = models.TextField(null=True)
    cancel_request_id = models.UUIDField(null=True, unique=True)

    class Meta:
        constraints = [
            *_quantity_checks("quantity", "order_quantity"),
            models.CheckConstraint(
                condition=Q(status__in=OrderStatus.values), name="order_status_valid"
            ),
            models.CheckConstraint(
                condition=~Q(line_warehouse=models.F("output_warehouse")),
                name="order_warehouses_differ",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="OPEN",
                        cancelled_by__isnull=True,
                        cancelled_at__isnull=True,
                        cancel_reason__isnull=True,
                        cancel_request_id__isnull=True,
                    )
                    | Q(
                        status="CANCELLED",
                        cancelled_by__isnull=False,
                        cancelled_at__isnull=False,
                        cancel_reason__isnull=False,
                        cancel_request_id__isnull=False,
                    )
                ),
                name="order_cancel_matches_status",
            ),
        ]


class MovementKind(models.TextChoices):
    ISSUE = "ISSUE", "Issue to line"
    RETURN = "RETURN", "Return from line"


class ProductionMaterialMovement(models.Model):
    """M5.2a (Issue #72): links one Inventory transfer to the order it issued or returned for.

    Lot, quantity, warehouses and actor live on the transfer's ledger entries (Inventory owns
    them); PostgreSQL checks direction, BOM membership and the net-issue cap on insert.
    """

    order = models.ForeignKey(ProductionOrder, on_delete=models.PROTECT, related_name="materials")
    kind = models.CharField(max_length=6, choices=MovementKind)
    transfer = models.OneToOneField(
        StockTransfer, on_delete=models.PROTECT, related_name="production_movement"
    )
    created_at = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=MovementKind.values), name="material_movement_kind_valid"
            ),
        ]

    @property
    def lot(self):
        return self.transfer.source_entry.lot

    @property
    def quantity(self):
        return self.transfer.destination_entry.quantity_delta
