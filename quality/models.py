from django.conf import settings
from django.db import models
from django.db.models.functions import Now

from facilities.models import Warehouse
from inventory.models import Lot


class LotDisposition(models.TextChoices):
    HOLD = "HOLD", "Hold"
    RELEASED = "RELEASED", "Released"


class LotDispositionEvent(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    request_id = models.UUIDField(unique=True)
    from_disposition = models.CharField(max_length=8, choices=LotDisposition.choices)
    to_disposition = models.CharField(max_length=8, choices=LotDisposition.choices)
    reason = models.TextField()
    created_at = models.DateTimeField(db_default=Now(), editable=False)

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
