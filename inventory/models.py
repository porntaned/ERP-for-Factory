from django.db import models

from catalog.models import Item
from facilities.models import CODE_PATTERN


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
