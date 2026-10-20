from django.conf import settings
from django.db import models

from facilities.models import Warehouse


class WarehouseRole(models.TextChoices):
    WAREHOUSE = "WAREHOUSE", "Warehouse"
    PRODUCTION = "PRODUCTION", "Production"
    QUALITY = "QUALITY", "Quality"
    APPROVER = "APPROVER", "Approver"


class WarehouseRoleAssignment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="warehouse_role_assignments",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    role = models.CharField(max_length=10, choices=WarehouseRole.choices)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=WarehouseRole.values),
                name="warehouse_role_assignment_role_valid",
            ),
            models.UniqueConstraint(
                fields=("user", "warehouse", "role"),
                name="warehouse_role_assignment_unique",
            ),
        ]
