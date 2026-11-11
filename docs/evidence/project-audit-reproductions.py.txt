"""Known-defect reproductions for the post-PR12 audit; this branch is not merge-ready."""

from typing import Any
from uuid import uuid4

import pytest

from access_control.policies import has_warehouse_role, warehouses_for_user

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("policy", ["has_role", "warehouse_query"])
def test_audit_persisted_deactivation_denies_cached_actor(
    quality_scope: dict[str, Any], quality_user: Any, grant_role: Any, policy: str
) -> None:
    warehouse = quality_scope["warehouse"]
    grant_role(quality_user, warehouse, "QUALITY")
    type(quality_user).objects.filter(pk=quality_user.pk).update(is_active=False)
    assert quality_user.is_active
    if policy == "has_role":
        assert not has_warehouse_role(quality_user, warehouse, {"QUALITY"})
    else:
        assert not warehouses_for_user(quality_user, {"QUALITY"}).exists()


@pytest.mark.parametrize("policy", ["has_role", "warehouse_query"])
def test_audit_unsaved_actor_with_existing_primary_key_is_denied(
    quality_scope: dict[str, Any], quality_user: Any, grant_role: Any, policy: str
) -> None:
    warehouse = quality_scope["warehouse"]
    grant_role(quality_user, warehouse, "QUALITY")
    unsaved = type(quality_user)(pk=quality_user.pk, username="synthetic-unsaved-collision")
    assert unsaved._state.adding
    if policy == "has_role":
        assert not has_warehouse_role(unsaved, warehouse, {"QUALITY"})
    else:
        assert not warehouses_for_user(unsaved, {"QUALITY"}).exists()


def test_audit_accepted_high_event_id_does_not_block_subsequent_hold(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    lot = quality_scope["lot"]
    warehouse = quality_scope["warehouse"]
    grant_role(quality_user, warehouse, "QUALITY")
    event_model = disposition_contract["event_model"]
    event_model.objects.create(
        id=1_000_000_000,
        lot=lot,
        warehouse=warehouse,
        actor=quality_user,
        request_id=uuid4(),
        from_disposition="HOLD",
        to_disposition="RELEASED",
        reason="Synthetic explicit high-ID audit reproduction",
    )
    assert disposition_contract["get_disposition"](lot=lot, warehouse=warehouse) == "RELEASED"
    event = disposition_contract["transition"](
        lot=lot,
        warehouse=warehouse,
        actor=quality_user,
        expected_disposition="RELEASED",
        target_disposition="HOLD",
        reason="Synthetic containment decision must remain possible",
        request_id=uuid4(),
    )
    assert event.to_disposition == "HOLD"
    assert disposition_contract["get_disposition"](lot=lot, warehouse=warehouse) == "HOLD"
