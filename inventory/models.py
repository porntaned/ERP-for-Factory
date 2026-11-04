from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models.functions import Now, Round

from catalog.models import Item
from facilities.models import CODE_PATTERN, Warehouse

from .fields import ExactQuantityField


class Lot(models.Model):
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    code = models.CharField(max_length=32)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=CODE_PATTERN),
                name="lot_code_format",
            ),
            models.UniqueConstraint(
                fields=("item", "code"),
                name="lot_item_code_unique",
            ),
        ]


class StockLedgerEntry(models.Model):
    """Internal storage foundation; operational posting commands are separate."""

    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    quantity_delta = ExactQuantityField(max_digits=20, decimal_places=6)
    reason = models.TextField()
    created_at = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        indexes = [models.Index(fields=("lot", "warehouse"), name="stock_ledger_pair_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_delta__gt=Decimal("-100000000000000"))
                & models.Q(quantity_delta__lt=Decimal("100000000000000"))
                & ~models.Q(quantity_delta=0),
                name="stock_delta_finite_range_nonzero",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_delta=Round("quantity_delta", precision=6)),
                name="stock_delta_exact_precision",
            ),
            models.CheckConstraint(
                condition=models.Q(reason__regex=r"\S"), name="stock_reason_nonblank"
            ),
        ]


class StockReceipt(models.Model):
    """Typed receipt intent; immutable ledger entry retains payload and DB time."""

    request_id = models.UUIDField(unique=True)
    ledger_entry = models.OneToOneField(StockLedgerEntry, on_delete=models.PROTECT)


class StockTransfer(models.Model):
    """Immutable transfer identity; ledger rows own the authoritative payload."""

    source_entry = models.OneToOneField(
        StockLedgerEntry, on_delete=models.PROTECT, related_name="transfer_out"
    )
    destination_entry = models.OneToOneField(
        StockLedgerEntry, on_delete=models.PROTECT, related_name="transfer_in"
    )
    created_at = models.DateTimeField(db_default=Now(), editable=False)
    request_id = models.UUIDField(null=True, unique=True)


REQUEST_KEY_COMMANDS = (
    ("RECEIPT", "Receipt"),
    ("TRANSFER", "Transfer"),
    ("DISPOSITION", "Disposition"),
    ("REVERSAL", "Reversal"),
    ("BOM_DRAFT", "BOM draft"),
    ("BOM_APPROVE", "BOM approval"),
    ("ORDER_CREATE", "Production order"),
    ("ORDER_CANCEL", "Production order cancel"),
)


class RequestKey(models.Model):
    """Shared registry: one request UUID belongs to exactly one command type (M4.4.1)."""

    request_id = models.UUIDField(unique=True)
    command = models.CharField(max_length=12, choices=REQUEST_KEY_COMMANDS)
    created_at = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(command__in=[c for c, _ in REQUEST_KEY_COMMANDS]),
                name="request_key_command_valid",
            ),
        ]


class StockReversal(models.Model):
    """Compensating entries that reverse exactly one receipt or transfer (M4.5).

    The original stays untouched. Receipt reversal: one negative entry at the receipt's
    warehouse. Transfer reversal: a negative entry at the original destination and a
    positive entry at the original source. PostgreSQL validates the link, enforces
    once-only (one-to-one on the original) and immutability.
    """

    request_id = models.UUIDField(unique=True)
    receipt = models.OneToOneField(
        StockReceipt, null=True, on_delete=models.PROTECT, related_name="reversal"
    )
    transfer = models.OneToOneField(
        StockTransfer, null=True, on_delete=models.PROTECT, related_name="reversal"
    )
    debit_entry = models.OneToOneField(
        StockLedgerEntry, on_delete=models.PROTECT, related_name="reversal_debit"
    )
    credit_entry = models.OneToOneField(
        StockLedgerEntry, null=True, on_delete=models.PROTECT, related_name="reversal_credit"
    )
    created_at = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(receipt__isnull=False, transfer__isnull=True)
                    | models.Q(receipt__isnull=True, transfer__isnull=False)
                ),
                name="stock_reversal_one_original",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(transfer__isnull=True, credit_entry__isnull=True)
                    | models.Q(transfer__isnull=False, credit_entry__isnull=False)
                ),
                name="stock_reversal_credit_iff_transfer",
            ),
        ]
