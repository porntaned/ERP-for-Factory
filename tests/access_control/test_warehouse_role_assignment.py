from typing import Any

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

pytestmark = pytest.mark.django_db

SUPPORTED_ROLES = {"WAREHOUSE", "PRODUCTION", "QUALITY", "APPROVER"}


def create_assignment(
    assignment_model: Any,
    synthetic_user: Any,
    warehouse: Any,
    role: str = "WAREHOUSE",
) -> Any:
    return assignment_model.objects.create(
        user=synthetic_user,
        warehouse=warehouse,
        role=role,
    )


def test_default_django_user_is_the_identity_model(assignment_model: Any) -> None:
    assert apps.is_installed("django.contrib.contenttypes")
    assert apps.is_installed("django.contrib.auth")
    assert get_user_model()._meta.label == "auth.User"


def test_assignment_has_only_the_locked_persistent_fields(assignment_model: Any) -> None:
    concrete_fields = {
        field.name for field in assignment_model._meta.get_fields() if field.concrete
    }

    assert concrete_fields == {"id", "user", "warehouse", "role"}


def test_assignment_exposes_exact_supported_roles(assignment_model: Any) -> None:
    role_field = assignment_model._meta.get_field("role")
    persisted_choices = {value for value, _label in role_field.choices}

    assert persisted_choices == SUPPORTED_ROLES


@pytest.mark.parametrize("role", sorted(SUPPORTED_ROLES))
def test_each_supported_role_can_be_persisted(
    assignment_model: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
    role: str,
) -> None:
    assignment = create_assignment(
        assignment_model,
        synthetic_user,
        warehouse_scope["target"],
        role,
    )

    assignment.refresh_from_db()
    assert assignment.role == role


@pytest.mark.parametrize("role", ["", "MANAGER", "warehouse", "คลัง"])
def test_unsupported_role_is_rejected_at_database_boundary(
    assignment_model: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
    role: str,
) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        create_assignment(
            assignment_model,
            synthetic_user,
            warehouse_scope["target"],
            role,
        )


@pytest.mark.parametrize("null_field", ["user_id", "warehouse_id", "role"])
def test_required_fields_reject_null_at_database_boundary(
    assignment_model: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
    null_field: str,
) -> None:
    values = {
        "user_id": synthetic_user.pk,
        "warehouse_id": warehouse_scope["target"].pk,
        "role": "WAREHOUSE",
    }
    values[null_field] = None

    with pytest.raises(IntegrityError), transaction.atomic():
        assignment_model.objects.create(**values)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("invalid_field", ["user_id", "warehouse_id"])
def test_invalid_reference_fails_at_database_boundary(
    assignment_model: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
    invalid_field: str,
) -> None:
    values = {
        "user_id": synthetic_user.pk,
        "warehouse_id": warehouse_scope["target"].pk,
        "role": "WAREHOUSE",
    }
    values[invalid_field] = 2_147_483_647

    with pytest.raises(IntegrityError), transaction.atomic():
        assignment_model.objects.create(**values)


def test_exact_tuple_is_unique_but_multiple_roles_and_warehouses_coexist(
    assignment_model: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    target = warehouse_scope["target"]
    sibling = warehouse_scope["sibling_warehouse"]
    create_assignment(assignment_model, synthetic_user, target, "WAREHOUSE")

    with pytest.raises(IntegrityError), transaction.atomic():
        create_assignment(assignment_model, synthetic_user, target, "WAREHOUSE")

    second_role = create_assignment(assignment_model, synthetic_user, target, "QUALITY")
    second_warehouse = create_assignment(
        assignment_model,
        synthetic_user,
        sibling,
        "WAREHOUSE",
    )

    assert second_role.pk is not None
    assert second_warehouse.pk is not None
    assert assignment_model.objects.filter(user=synthetic_user).count() == 3


def test_assigned_user_deletion_is_protected(
    assignment_model: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    create_assignment(assignment_model, synthetic_user, warehouse_scope["target"])

    with pytest.raises(ProtectedError):
        synthetic_user.delete()


def test_assigned_warehouse_deletion_is_protected(
    assignment_model: Any,
    synthetic_user: Any,
    warehouse_scope: dict[str, Any],
) -> None:
    warehouse = warehouse_scope["target"]
    create_assignment(assignment_model, synthetic_user, warehouse)

    with pytest.raises(ProtectedError):
        warehouse.delete()


def test_synthetic_users_have_no_usable_password(synthetic_user: Any) -> None:
    synthetic_user.refresh_from_db()

    assert not synthetic_user.has_usable_password()
