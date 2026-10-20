from django.db import models

from facilities.models import CODE_PATTERN, Organization


class ItemType(models.TextChoices):
    RAW = "RAW", "Raw material"
    WIP = "WIP", "Work in progress"
    FINISHED = "FINISHED", "Finished good"


class UnitOfMeasure(models.Model):
    code = models.CharField(max_length=32, unique=True)
    display_name = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=CODE_PATTERN),
                name="unit_of_measure_code_format",
            ),
        ]


class Item(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    code = models.CharField(max_length=32)
    display_name = models.TextField()
    item_type = models.CharField(max_length=8, choices=ItemType)
    base_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=CODE_PATTERN),
                name="item_code_format",
            ),
            models.CheckConstraint(
                condition=models.Q(item_type__in=ItemType.values),
                name="item_type_valid",
            ),
            models.UniqueConstraint(
                fields=("organization", "code"),
                name="item_organization_code_unique",
            ),
        ]
