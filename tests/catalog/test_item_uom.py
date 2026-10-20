from collections.abc import Callable
from typing import Any

import pytest
from django.apps import apps
from django.db import DatabaseError, DataError, IntegrityError, transaction
from django.db.models.deletion import ProtectedError

pytestmark = pytest.mark.django_db


def create_item(
    catalog_model: Callable[[str], Any],
    organization: Any,
    each_uom: Any,
    **overrides: Any,
) -> Any:
    values = {
        "organization": organization,
        "code": "LED-PANEL",
        "display_name": "แผงไฟ LED",
        "item_type": "FINISHED",
        "base_uom": each_uom,
    }
    values.update(overrides)
    return catalog_model("Item").objects.create(**values)


def test_unicode_uom_and_item_can_be_stored(
    catalog_model: Callable[[str], Any], organization: Any, each_uom: Any
) -> None:
    item = create_item(catalog_model, organization, each_uom)

    each_uom.refresh_from_db()
    item.refresh_from_db()
    assert each_uom.display_name == "ชิ้น"
    assert item.display_name == "แผงไฟ LED"
    assert item.organization_id == organization.pk
    assert item.base_uom_id == each_uom.pk


def test_uom_code_is_globally_unique(catalog_model: Callable[[str], Any]) -> None:
    uom_model = catalog_model("UnitOfMeasure")
    uom_model.objects.create(code="EA", display_name="Each")

    with pytest.raises(IntegrityError), transaction.atomic():
        uom_model.objects.create(code="EA", display_name="Duplicate")


def test_item_code_is_unique_within_organization(
    catalog_model: Callable[[str], Any], organization: Any, each_uom: Any
) -> None:
    organization_model = apps.get_model("facilities", "Organization")
    second_organization = organization_model.objects.create(code="SECOND", display_name="Second")
    create_item(catalog_model, organization, each_uom)

    with pytest.raises(IntegrityError), transaction.atomic():
        create_item(catalog_model, organization, each_uom, display_name="Duplicate")

    other = create_item(catalog_model, second_organization, each_uom)
    assert other.pk is not None


@pytest.mark.parametrize(
    ("invalid_code", "expected_error"),
    [
        ("", IntegrityError),
        ("lower", IntegrityError),
        ("1FIRST", IntegrityError),
        ("HAS SPACE", IntegrityError),
        ("HAS/SLASH", IntegrityError),
        ("หน่วย", IntegrityError),
        ("A" * 33, DataError),
    ],
)
@pytest.mark.parametrize("model_name", ["UnitOfMeasure", "Item"])
def test_code_format_is_enforced_at_database_boundary(
    catalog_model: Callable[[str], Any],
    organization: Any,
    each_uom: Any,
    model_name: str,
    invalid_code: str,
    expected_error: type[DatabaseError],
) -> None:
    with pytest.raises(expected_error), transaction.atomic():
        if model_name == "UnitOfMeasure":
            catalog_model(model_name).objects.create(code=invalid_code, display_name="Invalid")
        else:
            create_item(catalog_model, organization, each_uom, code=invalid_code)


@pytest.mark.parametrize("valid_code", ["A", "A" * 32, "RM-A", "RM_B2"])
@pytest.mark.parametrize("model_name", ["UnitOfMeasure", "Item"])
def test_valid_code_boundaries_are_accepted(
    catalog_model: Callable[[str], Any],
    organization: Any,
    each_uom: Any,
    model_name: str,
    valid_code: str,
) -> None:
    if model_name == "UnitOfMeasure":
        record = catalog_model(model_name).objects.create(
            code=valid_code,
            display_name="Valid",
        )
    else:
        record = create_item(catalog_model, organization, each_uom, code=valid_code)
    assert record.pk is not None


@pytest.mark.parametrize("item_type", ["RAW", "WIP", "FINISHED"])
def test_supported_item_types_are_accepted(
    catalog_model: Callable[[str], Any], organization: Any, each_uom: Any, item_type: str
) -> None:
    item = create_item(catalog_model, organization, each_uom, item_type=item_type)
    assert item.item_type == item_type


@pytest.mark.parametrize("item_type", ["", "SERVICE", "raw"])
def test_unsupported_item_type_is_rejected_at_database_boundary(
    catalog_model: Callable[[str], Any], organization: Any, each_uom: Any, item_type: str
) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        create_item(catalog_model, organization, each_uom, item_type=item_type)


def test_organization_deletion_is_protected_by_item(
    catalog_model: Callable[[str], Any], organization: Any, each_uom: Any
) -> None:
    create_item(catalog_model, organization, each_uom)

    with pytest.raises(ProtectedError):
        organization.delete()


def test_base_uom_deletion_is_protected_by_item(
    catalog_model: Callable[[str], Any], organization: Any, each_uom: Any
) -> None:
    create_item(catalog_model, organization, each_uom)

    with pytest.raises(ProtectedError):
        each_uom.delete()
