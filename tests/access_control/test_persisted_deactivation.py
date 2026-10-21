from typing import Any

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def test_role_check_denies_user_deactivated_after_instance_was_loaded(
    assignment_model: Any,
    has_warehouse_role: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    assignment_model.objects.create(
        user=synthetic_user, warehouse=warehouse, role="WAREHOUSE"
    )
    assert has_warehouse_role(synthetic_user, warehouse, {"WAREHOUSE"}) is True

    assert (
        get_user_model().objects.filter(pk=synthetic_user.pk).update(is_active=False) == 1
    )
    assert synthetic_user.is_active is True

    assert has_warehouse_role(synthetic_user, warehouse, {"WAREHOUSE"}) is False


def test_warehouse_query_denies_user_deactivated_after_instance_was_loaded(
    assignment_model: Any,
    warehouses_for_user: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    assignment_model.objects.create(
        user=synthetic_user, warehouse=warehouse, role="WAREHOUSE"
    )
    assert list(warehouses_for_user(synthetic_user, {"WAREHOUSE"})) == [warehouse]

    assert (
        get_user_model().objects.filter(pk=synthetic_user.pk).update(is_active=False) == 1
    )
    assert synthetic_user.is_active is True

    assert list(warehouses_for_user(synthetic_user, {"WAREHOUSE"})) == []


def test_unevaluated_warehouse_query_observes_later_deactivation(
    assignment_model: Any,
    warehouses_for_user: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
    django_assert_num_queries: Any,
) -> None:
    warehouse = warehouse_scope["target"]
    assignment_model.objects.create(
        user=synthetic_user, warehouse=warehouse, role="WAREHOUSE"
    )
    assert list(warehouses_for_user(synthetic_user, {"WAREHOUSE"})) == [warehouse]

    with django_assert_num_queries(0):
        authorized = warehouses_for_user(synthetic_user, {"WAREHOUSE"})

    assert (
        get_user_model().objects.filter(pk=synthetic_user.pk).update(is_active=False) == 1
    )
    assert synthetic_user.is_active is True

    assert list(authorized) == []
