from typing import Any

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


@pytest.fixture
def authorized_user(
    assignment_model: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> Any:
    assignment_model.objects.create(
        user=synthetic_user, warehouse=warehouse_scope["target"], role="QUALITY"
    )
    # Exercise an ordinary ORM-loaded instance as well as the saved fixture.
    assert synthetic_user._state.adding is False
    return get_user_model().objects.get(pk=synthetic_user.pk)


@pytest.fixture(params=["matching", "nonmatching", "absent"])
def unsaved_user(request: Any, authorized_user: Any) -> Any:
    pk = {
        "matching": authorized_user.pk,
        "nonmatching": authorized_user.pk + 1_000_000,
        "absent": None,
    }[request.param]
    if request.param == "nonmatching":
        assert not get_user_model().objects.filter(pk=pk).exists()
    user = get_user_model()(pk=pk, username="synthetic-unsaved-collision")
    user.set_unusable_password()
    assert user._state.adding is True
    assert user.is_authenticated and user.is_active
    assert not user.has_usable_password()
    return user


def test_role_check_denies_unsaved_user_despite_supplied_pk(
    has_warehouse_role: Any,
    authorized_user: Any,
    unsaved_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    assert authorized_user._state.adding is False
    assert has_warehouse_role(authorized_user, warehouse, {"QUALITY"}) is True

    assert has_warehouse_role(unsaved_user, warehouse, {"QUALITY"}) is False


def test_warehouse_query_denies_unsaved_user_despite_supplied_pk(
    warehouses_for_user: Any,
    authorized_user: Any,
    unsaved_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    assert authorized_user._state.adding is False
    assert list(warehouses_for_user(authorized_user, {"QUALITY"})) == [warehouse]

    assert list(warehouses_for_user(unsaved_user, {"QUALITY"})) == []
