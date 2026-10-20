from collections.abc import Callable
from typing import Any

import pytest
from django.apps import apps
from django.db import DatabaseError, DataError, IntegrityError, transaction
from django.db.models.deletion import ProtectedError

pytestmark = pytest.mark.django_db


def create_lot(
    inventory_model: Callable[[str], Any],
    raw_item: Any,
    **overrides: Any,
) -> Any:
    values = {"item": raw_item, "code": "LOT-2026_001"}
    values.update(overrides)
    return inventory_model("Lot").objects.create(**values)


def test_lot_keeps_its_item_and_internal_code(
    inventory_model: Callable[[str], Any], raw_item: Any
) -> None:
    lot = create_lot(inventory_model, raw_item)

    lot.refresh_from_db()
    assert lot.item_id == raw_item.pk
    assert lot.code == "LOT-2026_001"


def test_lot_has_only_the_locked_persistent_fields(
    inventory_model: Callable[[str], Any],
) -> None:
    concrete_fields = {
        field.name for field in inventory_model("Lot")._meta.get_fields() if field.concrete
    }

    assert concrete_fields == {"id", "item", "code"}


@pytest.mark.parametrize("valid_code", ["A", "A" * 32, "LOT-2026_001"])
def test_valid_lot_code_boundaries_are_accepted(
    inventory_model: Callable[[str], Any], raw_item: Any, valid_code: str
) -> None:
    lot = create_lot(inventory_model, raw_item, code=valid_code)

    assert lot.pk is not None


@pytest.mark.parametrize(
    ("invalid_code", "expected_error"),
    [
        ("", IntegrityError),
        ("lower", IntegrityError),
        ("1FIRST", IntegrityError),
        ("HAS SPACE", IntegrityError),
        ("HAS/SLASH", IntegrityError),
        ("ล็อต", IntegrityError),
        ("A" * 33, DataError),
    ],
)
def test_lot_code_format_is_enforced_at_database_boundary(
    inventory_model: Callable[[str], Any],
    raw_item: Any,
    invalid_code: str,
    expected_error: type[DatabaseError],
) -> None:
    with pytest.raises(expected_error), transaction.atomic():
        create_lot(inventory_model, raw_item, code=invalid_code)


def test_lot_code_is_unique_within_item(
    inventory_model: Callable[[str], Any], raw_item: Any
) -> None:
    create_lot(inventory_model, raw_item)

    with pytest.raises(IntegrityError), transaction.atomic():
        create_lot(inventory_model, raw_item)


def test_same_lot_code_is_allowed_for_different_items(
    inventory_model: Callable[[str], Any],
    organization: Any,
    each_uom: Any,
    raw_item: Any,
) -> None:
    item_model = apps.get_model("catalog", "Item")
    second_item = item_model.objects.create(
        organization=organization,
        code="LED-DRIVER",
        display_name="LED driver",
        item_type="RAW",
        base_uom=each_uom,
    )

    first_lot = create_lot(inventory_model, raw_item)
    second_lot = create_lot(inventory_model, second_item)

    assert first_lot.code == second_lot.code
    assert first_lot.item_id != second_lot.item_id


def test_item_deletion_is_protected_by_lot(
    inventory_model: Callable[[str], Any], raw_item: Any
) -> None:
    create_lot(inventory_model, raw_item)

    with pytest.raises(ProtectedError):
        raw_item.delete()

