from typing import Any

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def grant(
    assignment_model: Any,
    user: Any,
    warehouse: Any,
    role: str,
) -> Any:
    return assignment_model.objects.create(user=user, warehouse=warehouse, role=role)


def warehouse_ids(warehouses: Any) -> set[int]:
    return set(warehouses.values_list("pk", flat=True))


def test_matching_any_requested_role_allows_exact_warehouse(
    assignment_model: Any,
    has_warehouse_role: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    grant(assignment_model, synthetic_user, warehouse, "PRODUCTION")
    grant(assignment_model, synthetic_user, warehouse, "QUALITY")

    assert has_warehouse_role(synthetic_user, warehouse, {"PRODUCTION"}) is True
    assert has_warehouse_role(synthetic_user, warehouse, {"APPROVER", "QUALITY"}) is True


def test_deleting_assignment_revokes_warehouse_access(
    assignment_model: Any,
    has_warehouse_role: Any,
    warehouses_for_user: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    assignment = grant(assignment_model, synthetic_user, warehouse, "WAREHOUSE")

    assert has_warehouse_role(synthetic_user, warehouse, {"WAREHOUSE"}) is True
    assert warehouse_ids(warehouses_for_user(synthetic_user, {"WAREHOUSE"})) == {
        warehouse.pk
    }

    assignment.delete()

    assert has_warehouse_role(synthetic_user, warehouse, {"WAREHOUSE"}) is False
    assert warehouse_ids(warehouses_for_user(synthetic_user, {"WAREHOUSE"})) == set()


def test_assignment_does_not_leak_across_warehouse_plant_or_organization(
    assignment_model: Any,
    has_warehouse_role: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    grant(assignment_model, synthetic_user, warehouse_scope["target"], "WAREHOUSE")

    assert (
        has_warehouse_role(
            synthetic_user,
            warehouse_scope["target"],
            {"WAREHOUSE"},
        )
        is True
    )
    assert (
        has_warehouse_role(
            synthetic_user,
            warehouse_scope["sibling_warehouse"],
            {"WAREHOUSE"},
        )
        is False
    )
    assert (
        has_warehouse_role(
            synthetic_user,
            warehouse_scope["same_code_other_plant"],
            {"WAREHOUSE"},
        )
        is False
    )
    assert (
        has_warehouse_role(
            synthetic_user,
            warehouse_scope["same_code_other_organization"],
            {"WAREHOUSE"},
        )
        is False
    )


def test_authorized_warehouse_query_returns_exact_primary_keys_without_duplicates(
    assignment_model: Any,
    warehouses_for_user: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    target = warehouse_scope["target"]
    sibling = warehouse_scope["sibling_warehouse"]
    grant(assignment_model, synthetic_user, target, "PRODUCTION")
    grant(assignment_model, synthetic_user, target, "QUALITY")
    grant(assignment_model, synthetic_user, sibling, "QUALITY")
    grant(
        assignment_model,
        synthetic_user,
        warehouse_scope["same_code_other_plant"],
        "WAREHOUSE",
    )

    authorized = warehouses_for_user(synthetic_user, {"PRODUCTION", "QUALITY"})

    assert warehouse_ids(authorized) == {target.pk, sibling.pk}
    assert authorized.count() == 2


def test_authorized_warehouse_query_does_not_match_warehouse_codes(
    assignment_model: Any,
    warehouses_for_user: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    target = warehouse_scope["target"]
    grant(assignment_model, synthetic_user, target, "WAREHOUSE")

    assert warehouse_ids(warehouses_for_user(synthetic_user, {"WAREHOUSE"})) == {target.pk}
    assert warehouse_scope["same_code_other_plant"].pk != target.pk
    assert warehouse_scope["same_code_other_organization"].pk != target.pk


def test_multiple_warehouse_assignments_are_evaluated_independently(
    assignment_model: Any,
    has_warehouse_role: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    target = warehouse_scope["target"]
    sibling = warehouse_scope["sibling_warehouse"]
    grant(assignment_model, synthetic_user, target, "QUALITY")
    grant(assignment_model, synthetic_user, sibling, "WAREHOUSE")

    assert has_warehouse_role(synthetic_user, target, {"QUALITY"}) is True
    assert has_warehouse_role(synthetic_user, target, {"WAREHOUSE"}) is False
    assert has_warehouse_role(synthetic_user, sibling, {"WAREHOUSE"}) is True
    assert has_warehouse_role(synthetic_user, sibling, {"QUALITY"}) is False


def test_anonymous_user_is_denied(
    has_warehouse_role: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    from django.contrib.auth.models import AnonymousUser

    assert (
        has_warehouse_role(
            AnonymousUser(),
            warehouse_scope["target"],
            {"WAREHOUSE"},
        )
        is False
    )


def test_inactive_user_is_denied_even_with_matching_assignment(
    assignment_model: Any,
    has_warehouse_role: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    grant(assignment_model, synthetic_user, warehouse, "WAREHOUSE")
    synthetic_user.is_active = False
    synthetic_user.save(update_fields=["is_active"])

    assert has_warehouse_role(synthetic_user, warehouse, {"WAREHOUSE"}) is False


def test_unsaved_user_is_denied(
    has_warehouse_role: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    user = get_user_model()(username="synthetic-unsaved-user")
    user.set_unusable_password()

    assert user.pk is None
    assert not user.has_usable_password()
    assert has_warehouse_role(user, warehouse_scope["target"], {"WAREHOUSE"}) is False


def test_unassigned_user_is_denied(
    has_warehouse_role: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    assert (
        has_warehouse_role(
            synthetic_user,
            warehouse_scope["target"],
            {"WAREHOUSE"},
        )
        is False
    )


def test_matching_grant_does_not_authorize_another_active_saved_user(
    assignment_model: Any,
    has_warehouse_role: Any,
    warehouses_for_user: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    grant(assignment_model, synthetic_user, warehouse, "WAREHOUSE")
    other_user = get_user_model()(username="synthetic-unassigned-user")
    other_user.set_unusable_password()
    other_user.save()

    assert synthetic_user.is_active
    assert other_user.is_active
    assert not synthetic_user.has_usable_password()
    assert not other_user.has_usable_password()
    assert has_warehouse_role(synthetic_user, warehouse, {"WAREHOUSE"}) is True
    assert warehouse_ids(warehouses_for_user(synthetic_user, {"WAREHOUSE"})) == {
        warehouse.pk
    }
    assert has_warehouse_role(other_user, warehouse, {"WAREHOUSE"}) is False
    assert warehouse_ids(warehouses_for_user(other_user, {"WAREHOUSE"})) == set()


def test_wrong_role_is_denied(
    assignment_model: Any,
    has_warehouse_role: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    grant(assignment_model, synthetic_user, warehouse, "WAREHOUSE")

    assert has_warehouse_role(synthetic_user, warehouse, {"QUALITY"}) is False


@pytest.mark.parametrize(
    "requested_roles",
    [None, [], (), set(), "WAREHOUSE", ["UNKNOWN"], ["warehouse"], ["คลัง"]],
)
def test_empty_or_unsupported_requested_roles_fail_closed(
    assignment_model: Any,
    has_warehouse_role: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
    requested_roles: object,
) -> None:
    warehouse = warehouse_scope["target"]
    grant(assignment_model, synthetic_user, warehouse, "WAREHOUSE")

    assert has_warehouse_role(synthetic_user, warehouse, requested_roles) is False


@pytest.mark.parametrize(
    "requested_roles",
    [None, [], (), set(), "WAREHOUSE", ["UNKNOWN"], ["warehouse"], ["คลัง"]],
)
def test_authorized_warehouse_query_fails_closed_for_invalid_roles(
    assignment_model: Any,
    warehouses_for_user: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
    requested_roles: object,
) -> None:
    grant(assignment_model, synthetic_user, warehouse_scope["target"], "WAREHOUSE")

    assert warehouse_ids(warehouses_for_user(synthetic_user, requested_roles)) == set()


def test_mixed_supported_and_unsupported_requested_roles_fail_closed(
    assignment_model: Any,
    has_warehouse_role: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    grant(assignment_model, synthetic_user, warehouse, "WAREHOUSE")

    assert (
        has_warehouse_role(
            synthetic_user,
            warehouse,
            {"WAREHOUSE", "UNKNOWN"},
        )
        is False
    )


def test_authorized_warehouse_query_rejects_mixed_supported_and_unsupported_roles(
    assignment_model: Any,
    warehouses_for_user: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    grant(assignment_model, synthetic_user, warehouse_scope["target"], "WAREHOUSE")

    assert warehouse_ids(
        warehouses_for_user(synthetic_user, {"WAREHOUSE", "UNKNOWN"})
    ) == set()


def test_superuser_has_no_implicit_bypass(
    has_warehouse_role: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    user = get_user_model()(username="synthetic-superuser", is_superuser=True, is_staff=True)
    user.set_unusable_password()
    user.save()
    assert not user.has_usable_password()

    assert has_warehouse_role(user, warehouse_scope["target"], {"APPROVER"}) is False


def test_superuser_may_use_only_an_explicit_matching_assignment(
    assignment_model: Any,
    has_warehouse_role: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    user = get_user_model()(username="synthetic-assigned-superuser", is_superuser=True)
    user.set_unusable_password()
    user.save()
    warehouse = warehouse_scope["target"]
    grant(assignment_model, user, warehouse, "APPROVER")

    assert has_warehouse_role(user, warehouse, {"APPROVER"}) is True


@pytest.mark.parametrize("user_state", ["anonymous", "inactive", "unsaved"])
def test_authorized_warehouse_query_denies_non_operational_users(
    assignment_model: Any,
    warehouses_for_user: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
    user_state: str,
) -> None:
    warehouse = warehouse_scope["target"]
    grant(assignment_model, synthetic_user, warehouse, "WAREHOUSE")
    user = synthetic_user

    if user_state == "anonymous":
        from django.contrib.auth.models import AnonymousUser

        user = AnonymousUser()
    elif user_state == "inactive":
        synthetic_user.is_active = False
        synthetic_user.save(update_fields=["is_active"])
    else:
        user = get_user_model()(username="synthetic-unsaved-query-user")
        user.set_unusable_password()

    assert warehouse_ids(warehouses_for_user(user, {"WAREHOUSE"})) == set()


def test_superuser_has_no_implicit_authorized_warehouses(
    warehouses_for_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    user = get_user_model()(username="synthetic-query-superuser", is_superuser=True)
    user.set_unusable_password()
    user.save()

    assert warehouse_ids(warehouses_for_user(user, {"APPROVER"})) == set()
