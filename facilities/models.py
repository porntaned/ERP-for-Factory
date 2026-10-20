from django.db import models

CODE_PATTERN = r"\A[ABCDEFGHIJKLMNOPQRSTUVWXYZ][ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-]{0,31}\Z"


class Organization(models.Model):
    code = models.CharField(max_length=32, unique=True)
    display_name = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=CODE_PATTERN),
                name="organization_code_format",
            ),
        ]


class Plant(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    code = models.CharField(max_length=32)
    display_name = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=CODE_PATTERN),
                name="plant_code_format",
            ),
            models.UniqueConstraint(
                fields=("organization", "code"),
                name="plant_organization_code_unique",
            ),
        ]


class Warehouse(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT)
    code = models.CharField(max_length=32)
    display_name = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=CODE_PATTERN),
                name="warehouse_code_format",
            ),
            models.UniqueConstraint(
                fields=("plant", "code"),
                name="warehouse_plant_code_unique",
            ),
        ]
