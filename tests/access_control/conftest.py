from collections.abc import Callable
from importlib import import_module
from typing import Any

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model

EXPECTED_RED = (
    "access_control Warehouse role contract is absent; "
    "expected RED until Issue #9 is implemented"
)


@pytest.fixture
def assignment_model() -> Any:
    try:
        return apps.get_model("access_control", "WarehouseRoleAssignment")
    except LookupError:
        pytest.fail(EXPECTED_RED, pytrace=False)


@pytest.fixture
def policy_module(assignment_model: Any) -> Any:
    try:
        return import_module("access_control.policies")
    except ModuleNotFoundError:
        pytest.fail(EXPECTED_RED, pytrace=False)


@pytest.fixture
def has_warehouse_role(policy_module: Any) -> Callable[[Any, Any, object], bool]:
    try:
        return getattr(policy_module, "has_warehouse_role")
    except AttributeError:
        pytest.fail(EXPECTED_RED, pytrace=False)


@pytest.fixture
def warehouses_for_user(policy_module: Any) -> Callable[[Any, object], Any]:
    try:
        return getattr(policy_module, "warehouses_for_user")
    except AttributeError:
        pytest.fail(EXPECTED_RED, pytrace=False)


@pytest.fixture
def synthetic_user(db: None, assignment_model: Any) -> Any:
    user_model = get_user_model()
    user = user_model(username="synthetic-warehouse-user")
    user.set_unusable_password()
    user.save()
    assert not user.has_usable_password()
    return user


@pytest.fixture
def warehouse_scope(db: None, assignment_model: Any) -> dict[str, Any]:
    organization_model = apps.get_model("facilities", "Organization")
    plant_model = apps.get_model("facilities", "Plant")
    warehouse_model = apps.get_model("facilities", "Warehouse")

    organization = organization_model.objects.create(code="ACME", display_name="ACME")
    plant = plant_model.objects.create(
        organization=organization,
        code="BKK",
        display_name="Bangkok",
    )
    target = warehouse_model.objects.create(
        plant=plant,
        code="RM-A",
        display_name="Target raw material warehouse",
    )
    sibling_warehouse = warehouse_model.objects.create(
        plant=plant,
        code="FG-A",
        display_name="Sibling finished goods warehouse",
    )

    other_plant = plant_model.objects.create(
        organization=organization,
        code="CNX",
        display_name="Chiang Mai",
    )
    same_code_other_plant = warehouse_model.objects.create(
        plant=other_plant,
        code="RM-A",
        display_name="Same code in another plant",
    )

    other_organization = organization_model.objects.create(
        code="OTHER",
        display_name="Other organization",
    )
    other_organization_plant = plant_model.objects.create(
        organization=other_organization,
        code="BKK",
        display_name="Same plant code in another organization",
    )
    same_code_other_organization = warehouse_model.objects.create(
        plant=other_organization_plant,
        code="RM-A",
        display_name="Same code in another organization",
    )

    return {
        "target": target,
        "sibling_warehouse": sibling_warehouse,
        "same_code_other_plant": same_code_other_plant,
        "same_code_other_organization": same_code_other_organization,
    }
