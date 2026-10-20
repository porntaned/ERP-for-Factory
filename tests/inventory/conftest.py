from collections.abc import Callable
from typing import Any

import pytest
from django.apps import apps


@pytest.fixture
def inventory_model() -> Callable[[str], Any]:
    def resolve(name: str) -> Any:
        try:
            return apps.get_model("inventory", name)
        except LookupError:
            pytest.fail(
                f"inventory.{name} is not registered; expected RED until Issue #7 is implemented",
                pytrace=False,
            )

    return resolve


@pytest.fixture
def organization(db: None) -> Any:
    organization_model = apps.get_model("facilities", "Organization")
    return organization_model.objects.create(code="ACME", display_name="ACME")


@pytest.fixture
def each_uom(db: None) -> Any:
    uom_model = apps.get_model("catalog", "UnitOfMeasure")
    return uom_model.objects.create(code="EA", display_name="Each")


@pytest.fixture
def raw_item(organization: Any, each_uom: Any) -> Any:
    item_model = apps.get_model("catalog", "Item")
    return item_model.objects.create(
        organization=organization,
        code="LED-CHIP",
        display_name="LED chip",
        item_type="RAW",
        base_uom=each_uom,
    )

