from collections.abc import Callable
from typing import Any

import pytest
from django.db import DatabaseError, DataError, IntegrityError, transaction
from django.db.models.deletion import ProtectedError

pytestmark = pytest.mark.django_db


def create_coded_record(
    model: Callable[[str], Any],
    model_name: str,
    code: str,
) -> Any:
    organization_model = model("Organization")
    if model_name == "Organization":
        return organization_model.objects.create(code=code, display_name="Coded organization")

    organization = organization_model.objects.create(
        code="PARENT",
        display_name="Parent organization",
    )
    plant_model = model("Plant")
    if model_name == "Plant":
        return plant_model.objects.create(
            organization=organization,
            code=code,
            display_name="Coded plant",
        )

    if model_name == "Warehouse":
        plant = plant_model.objects.create(
            organization=organization,
            code="PLANT",
            display_name="Parent plant",
        )
        warehouse_model = model("Warehouse")
        return warehouse_model.objects.create(
            plant=plant,
            code=code,
            display_name="Coded warehouse",
        )

    raise AssertionError(f"Unsupported model under test: {model_name}")


def test_warehouse_can_be_created_under_existing_plant(
    model: Callable[[str], Any],
) -> None:
    organization_model = model("Organization")
    plant_model = model("Plant")
    warehouse_model = model("Warehouse")

    organization = organization_model.objects.create(code="ACME", display_name="บริษัท เอซีเอ็มอี")
    plant = plant_model.objects.create(
        organization=organization,
        code="BKK",
        display_name="โรงงานบางกอก",
    )
    warehouse = warehouse_model.objects.create(
        plant=plant,
        code="RM-A",
        display_name="คลังวัตถุดิบ เอ",
    )

    organization.refresh_from_db()
    plant.refresh_from_db()
    warehouse.refresh_from_db()
    assert warehouse.plant_id == plant.pk
    assert organization.display_name == "บริษัท เอซีเอ็มอี"
    assert plant.display_name == "โรงงานบางกอก"
    assert warehouse.display_name == "คลังวัตถุดิบ เอ"


def test_organization_code_is_globally_unique(model: Callable[[str], Any]) -> None:
    organization_model = model("Organization")
    organization_model.objects.create(code="ACME", display_name="First")

    with pytest.raises(IntegrityError), transaction.atomic():
        organization_model.objects.create(code="ACME", display_name="Second")


def test_plant_code_is_unique_within_organization(model: Callable[[str], Any]) -> None:
    organization_model = model("Organization")
    plant_model = model("Plant")
    first = organization_model.objects.create(code="FIRST", display_name="First")
    second = organization_model.objects.create(code="SECOND", display_name="Second")
    plant_model.objects.create(organization=first, code="BKK", display_name="First BKK")

    with pytest.raises(IntegrityError), transaction.atomic():
        plant_model.objects.create(organization=first, code="BKK", display_name="Duplicate")

    other = plant_model.objects.create(organization=second, code="BKK", display_name="Second BKK")
    assert other.pk is not None


def test_warehouse_code_is_unique_within_plant(model: Callable[[str], Any]) -> None:
    organization_model = model("Organization")
    plant_model = model("Plant")
    warehouse_model = model("Warehouse")
    organization = organization_model.objects.create(code="ACME", display_name="ACME")
    first = plant_model.objects.create(organization=organization, code="BKK", display_name="BKK")
    second = plant_model.objects.create(organization=organization, code="CNX", display_name="CNX")
    warehouse_model.objects.create(plant=first, code="RM-A", display_name="First RM-A")

    with pytest.raises(IntegrityError), transaction.atomic():
        warehouse_model.objects.create(plant=first, code="RM-A", display_name="Duplicate")

    other = warehouse_model.objects.create(plant=second, code="RM-A", display_name="Second RM-A")
    assert other.pk is not None


@pytest.mark.parametrize(
    ("invalid_code", "expected_error"),
    [
        ("", IntegrityError),
        ("lower", IntegrityError),
        ("1FIRST", IntegrityError),
        ("HAS SPACE", IntegrityError),
        ("HAS/SLASH", IntegrityError),
        ("คลัง", IntegrityError),
        ("A" * 33, DataError),
    ],
)
@pytest.mark.parametrize("model_name", ["Organization", "Plant", "Warehouse"])
def test_code_format_is_enforced_at_database_boundary(
    model: Callable[[str], Any],
    model_name: str,
    invalid_code: str,
    expected_error: type[DatabaseError],
) -> None:
    with pytest.raises(expected_error), transaction.atomic():
        create_coded_record(model, model_name, invalid_code)


@pytest.mark.parametrize("valid_code", ["A", "A" * 32, "RM-A", "RM_B2"])
@pytest.mark.parametrize("model_name", ["Organization", "Plant", "Warehouse"])
def test_valid_code_boundaries_are_accepted(
    model: Callable[[str], Any], model_name: str, valid_code: str
) -> None:
    record = create_coded_record(model, model_name, valid_code)
    assert record.pk is not None


def test_plant_deletion_is_protected_by_warehouse(
    hierarchy: tuple[Any, Any, Any],
) -> None:
    _organization, plant, _warehouse = hierarchy

    with pytest.raises(ProtectedError):
        plant.delete()


def test_organization_deletion_is_protected_by_plant(
    model: Callable[[str], Any],
) -> None:
    organization_model = model("Organization")
    plant_model = model("Plant")
    organization = organization_model.objects.create(code="ACME", display_name="ACME")
    plant_model.objects.create(
        organization=organization,
        code="BKK",
        display_name="BKK",
    )

    with pytest.raises(ProtectedError):
        organization.delete()
