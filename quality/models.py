from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models.functions import Now, Round

from facilities.models import Warehouse
from inventory.fields import ExactQuantityField
from inventory.models import Lot


class LotDisposition(models.TextChoices):
    HOLD = "HOLD", "Hold"
    RELEASED = "RELEASED", "Released"
    REJECTED = "REJECTED", "Rejected"


class InspectionKind(models.TextChoices):
    INCOMING = "INCOMING", "Incoming"
    FINAL = "FINAL", "Final"


class InspectionResult(models.TextChoices):
    PASS = "PASS", "Pass"
    FAIL = "FAIL", "Fail"


class LotInspection(models.Model):
    """M6.1 (Issue #96): one inspection of a Lot at a warehouse; append-only.

    Its disposition event (HOLD -> RELEASED on PASS, HOLD -> REJECTED on FAIL) links to it and
    carries the request key. PostgreSQL checks the kind against the Lot's origin and that every
    inspection is linked by exactly one event at commit.
    """

    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    kind = models.CharField(max_length=8, choices=InspectionKind.choices)
    result = models.CharField(max_length=4, choices=InspectionResult.choices)
    sample_quantity = ExactQuantityField(max_digits=20, decimal_places=6)
    note = models.TextField()
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(db_default=Now(), editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=InspectionKind.values), name="inspection_kind_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(result__in=InspectionResult.values),
                name="inspection_result_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(sample_quantity__gt=0)
                & models.Q(sample_quantity__lt=Decimal("100000000000000"))
                & models.Q(sample_quantity=Round("sample_quantity", precision=6)),
                name="inspection_sample_quantity_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(note__regex=r"\S"), name="inspection_note_nonblank"
            ),
        ]


class LotDispositionEvent(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    request_id = models.UUIDField(unique=True)
    from_disposition = models.CharField(max_length=8, choices=LotDisposition.choices)
    to_disposition = models.CharField(max_length=8, choices=LotDisposition.choices)
    reason = models.TextField()
    created_at = models.DateTimeField(db_default=Now(), editable=False)
    inspection = models.OneToOneField(
        LotInspection, null=True, on_delete=models.PROTECT, related_name="event"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(from_disposition__in=LotDisposition.values),
                name="lot_disposition_from_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(to_disposition__in=LotDisposition.values),
                name="lot_disposition_to_valid",
            ),
            models.CheckConstraint(
                condition=~models.Q(from_disposition=models.F("to_disposition")),
                name="lot_disposition_changes_state",
            ),
            models.CheckConstraint(
                condition=models.Q(reason__regex=r"\S"),
                name="lot_disposition_reason_nonblank",
            ),
        ]
