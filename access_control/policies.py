from collections.abc import Collection, Mapping
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from facilities.models import Warehouse

from .models import WarehouseRole, WarehouseRoleAssignment


def _validated_roles(allowed_roles: object) -> frozenset[str] | None:
    if isinstance(allowed_roles, (str, bytes, Mapping)) or not isinstance(
        allowed_roles, Collection
    ):
        return None

    if not allowed_roles or not all(isinstance(role, str) for role in allowed_roles):
        return None
    roles = frozenset(allowed_roles)
    if not roles.issubset(WarehouseRole.values):
        return None
    return roles


def _is_operational_user(user: Any) -> bool:
    return (
        isinstance(user, get_user_model())
        and user.pk is not None
        and user.is_authenticated
        and user.is_active
    )


def has_warehouse_role(
    user: Any,
    warehouse: Warehouse,
    allowed_roles: object,
) -> bool:
    roles = _validated_roles(allowed_roles)
    if (
        roles is None
        or not _is_operational_user(user)
        or not isinstance(warehouse, Warehouse)
        or warehouse.pk is None
    ):
        return False

    return WarehouseRoleAssignment.objects.filter(
        user_id=user.pk,
        warehouse_id=warehouse.pk,
        role__in=roles,
    ).exists()


def warehouses_for_user(user: Any, allowed_roles: object) -> QuerySet[Warehouse]:
    roles = _validated_roles(allowed_roles)
    if roles is None or not _is_operational_user(user):
        return Warehouse.objects.none()

    return Warehouse.objects.filter(
        role_assignments__user_id=user.pk,
        role_assignments__role__in=roles,
    ).distinct()
