from collections.abc import Callable
from importlib import import_module
from typing import Any

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model

EXPECTED_RED = (
    "quality Lot disposition contract is absent; "
    "expected RED until Issue #11 is implemented"
)


@pytest.fixture
def disposition_contract() -> dict[str, Any]:
    try:
        event_model = apps.get_model("quality", "LotDispositionEvent")
        services = import_module("quality.services")
        return {
            "event_model": event_model,
            "get_disposition": getattr(services, "get_lot_disposition"),
            "transition": getattr(services, "transition_lot_disposition"),
            "authorization_error": getattr(
                services, "DispositionAuthorizationError"
            ),
            "conflict_error": getattr(services, "DispositionConflictError"),
            "validation_error": getattr(services, "DispositionValidationError"),
        }
    except (AttributeError, LookupError, ModuleNotFoundError):
        pytest.fail(EXPECTED_RED, pytrace=False)


@pytest.fixture
def quality_scope(db: None, disposition_contract: dict[str, Any]) -> dict[str, Any]:
    organization_model = apps.get_model("facilities", "Organization")
    plant_model = apps.get_model("facilities", "Plant")
    warehouse_model = apps.get_model("facilities", "Warehouse")
    uom_model = apps.get_model("catalog", "UnitOfMeasure")
    item_model = apps.get_model("catalog", "Item")
    lot_model = apps.get_model("inventory", "Lot")

    organization = organization_model.objects.create(code="ACME", display_name="ACME")
    plant = plant_model.objects.create(
        organization=organization,
        code="BKK",
        display_name="Bangkok",
    )
    warehouse = warehouse_model.objects.create(
        plant=plant,
        code="RM-A",
        display_name="Raw material A",
    )
    sibling_warehouse = warehouse_model.objects.create(
        plant=plant,
        code="RM-B",
        display_name="Raw material B",
    )
    uom = uom_model.objects.create(code="EA", display_name="Each")
    item = item_model.objects.create(
        organization=organization,
        code="LED-CHIP",
        display_name="LED chip",
        item_type="RAW",
        base_uom=uom,
    )
    lot = lot_model.objects.create(item=item, code="LOT-001")
    second_lot = lot_model.objects.create(item=item, code="LOT-002")

    other_organization = organization_model.objects.create(
        code="OTHER",
        display_name="Other organization",
    )
    other_plant = plant_model.objects.create(
        organization=other_organization,
        code="BKK",
        display_name="Other Bangkok",
    )
    other_warehouse = warehouse_model.objects.create(
        plant=other_plant,
        code="RM-A",
        display_name="Other raw material A",
    )

    return {
        "organization": organization,
        "warehouse": warehouse,
        "sibling_warehouse": sibling_warehouse,
        "lot": lot,
        "second_lot": second_lot,
        "other_warehouse": other_warehouse,
    }


@pytest.fixture
def quality_user(db: None, disposition_contract: dict[str, Any]) -> Any:
    user = get_user_model()(username="synthetic-quality-user")
    user.set_unusable_password()
    user.save()
    assert not user.has_usable_password()
    return user


@pytest.fixture
def other_user(db: None, disposition_contract: dict[str, Any]) -> Any:
    user = get_user_model()(username="synthetic-other-user")
    user.set_unusable_password()
    user.save()
    return user


@pytest.fixture
def grant_role() -> Callable[[Any, Any, str], Any]:
    assignment_model = apps.get_model("access_control", "WarehouseRoleAssignment")

    def grant(user: Any, warehouse: Any, role: str) -> Any:
        return assignment_model.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
        )

    return grant

