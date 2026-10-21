from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

pytestmark = pytest.mark.django_db


def transition_values(
    quality_scope: dict[str, Any],
    quality_user: Any,
    **overrides: Any,
) -> dict[str, Any]:
    values = {
        "lot": quality_scope["lot"],
        "warehouse": quality_scope["warehouse"],
        "actor": quality_user,
        "expected_disposition": "HOLD",
        "target_disposition": "RELEASED",
        "reason": "Incoming inspection accepted",
        "request_id": uuid4(),
    }
    values.update(overrides)
    return values


def authorize_quality(
    grant_role: Any,
    quality_user: Any,
    quality_scope: dict[str, Any],
) -> Any:
    return grant_role(quality_user, quality_scope["warehouse"], "QUALITY")


def test_missing_history_is_hold_for_exact_lot_and_warehouse(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
) -> None:
    get_disposition = disposition_contract["get_disposition"]

    assert (
        get_disposition(
            lot=quality_scope["lot"],
            warehouse=quality_scope["warehouse"],
        )
        == "HOLD"
    )
    assert disposition_contract["event_model"].objects.count() == 0


def test_disposition_is_independent_for_each_lot_warehouse_pair(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    event = disposition_contract["transition"](
        **transition_values(quality_scope, quality_user)
    )

    assert event.pk is not None
    assert (
        disposition_contract["get_disposition"](
            lot=quality_scope["lot"],
            warehouse=quality_scope["warehouse"],
        )
        == "RELEASED"
    )
    assert (
        disposition_contract["get_disposition"](
            lot=quality_scope["lot"],
            warehouse=quality_scope["sibling_warehouse"],
        )
        == "HOLD"
    )
    assert (
        disposition_contract["get_disposition"](
            lot=quality_scope["second_lot"],
            warehouse=quality_scope["warehouse"],
        )
        == "HOLD"
    )


def test_release_then_hold_records_an_exact_attributed_chain(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    transition = disposition_contract["transition"]
    release_request = uuid4()
    before = timezone.now()

    released = transition(
        **transition_values(
            quality_scope,
            quality_user,
            request_id=release_request,
        )
    )
    held = transition(
        **transition_values(
            quality_scope,
            quality_user,
            expected_disposition="RELEASED",
            target_disposition="HOLD",
            reason="Packaging damage requires review",
        )
    )
    after = timezone.now()

    assert released.lot_id == quality_scope["lot"].pk
    assert released.warehouse_id == quality_scope["warehouse"].pk
    assert released.actor_id == quality_user.pk
    assert released.request_id == release_request
    assert released.from_disposition == "HOLD"
    assert released.to_disposition == "RELEASED"
    assert released.reason == "Incoming inspection accepted"
    assert isinstance(released.created_at, datetime)
    assert timezone.is_aware(released.created_at)
    assert before <= released.created_at <= after
    assert held.from_disposition == "RELEASED"
    assert held.to_disposition == "HOLD"
    assert held.pk > released.pk
    assert (
        disposition_contract["get_disposition"](
            lot=quality_scope["lot"],
            warehouse=quality_scope["warehouse"],
        )
        == "HOLD"
    )


def test_event_has_only_the_locked_persistent_fields(
    disposition_contract: dict[str, Any],
) -> None:
    concrete_fields = {
        field.name
        for field in disposition_contract["event_model"]._meta.get_fields()
        if field.concrete
    }

    assert concrete_fields == {
        "id",
        "lot",
        "warehouse",
        "actor",
        "request_id",
        "from_disposition",
        "to_disposition",
        "reason",
        "created_at",
    }


@pytest.mark.parametrize("role", ["WAREHOUSE", "PRODUCTION", "APPROVER"])
def test_non_quality_roles_cannot_record_a_decision(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    role: str,
) -> None:
    grant_role(quality_user, quality_scope["warehouse"], role)

    with pytest.raises(disposition_contract["authorization_error"]):
        disposition_contract["transition"](
            **transition_values(quality_scope, quality_user)
        )

    assert disposition_contract["event_model"].objects.count() == 0


def test_quality_grant_for_another_warehouse_does_not_authorize_target(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    grant_role(quality_user, quality_scope["sibling_warehouse"], "QUALITY")

    with pytest.raises(disposition_contract["authorization_error"]):
        disposition_contract["transition"](
            **transition_values(quality_scope, quality_user)
        )

    assert disposition_contract["event_model"].objects.count() == 0


@pytest.mark.parametrize("actor_kind", ["anonymous", "inactive", "unsaved"])
def test_non_operational_actor_cannot_record_a_decision(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    actor_kind: str,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    if actor_kind == "anonymous":
        actor = AnonymousUser()
    elif actor_kind == "inactive":
        quality_user.is_active = False
        quality_user.save(update_fields=["is_active"])
        actor = quality_user
    else:
        actor = type(quality_user)(username="synthetic-unsaved-quality-user")
        actor.set_unusable_password()

    with pytest.raises(disposition_contract["authorization_error"]):
        disposition_contract["transition"](
            **transition_values(quality_scope, quality_user, actor=actor)
        )

    assert disposition_contract["event_model"].objects.count() == 0


def test_superuser_has_no_implicit_quality_bypass(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
) -> None:
    quality_user.is_superuser = True
    quality_user.save(update_fields=["is_superuser"])

    with pytest.raises(disposition_contract["authorization_error"]):
        disposition_contract["transition"](
            **transition_values(quality_scope, quality_user)
        )

    assert disposition_contract["event_model"].objects.count() == 0


def test_revoked_quality_grant_cannot_record_a_decision(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    assignment = authorize_quality(grant_role, quality_user, quality_scope)
    assignment.delete()

    with pytest.raises(disposition_contract["authorization_error"]):
        disposition_contract["transition"](
            **transition_values(quality_scope, quality_user)
        )

    assert disposition_contract["event_model"].objects.count() == 0


def test_stale_active_actor_cannot_bypass_persisted_deactivation(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    type(quality_user).objects.filter(pk=quality_user.pk).update(is_active=False)
    assert quality_user.is_active  # Caller holds a stale in-memory user.

    with pytest.raises(disposition_contract["authorization_error"]):
        disposition_contract["transition"](**transition_values(quality_scope, quality_user))
    assert disposition_contract["event_model"].objects.count() == 0


def test_lot_and_warehouse_must_belong_to_same_organization(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    grant_role(quality_user, quality_scope["other_warehouse"], "QUALITY")

    with pytest.raises(disposition_contract["validation_error"]):
        disposition_contract["transition"](
            **transition_values(
                quality_scope,
                quality_user,
                warehouse=quality_scope["other_warehouse"],
            )
        )

    assert disposition_contract["event_model"].objects.count() == 0


def test_query_rejects_a_cross_organization_pair(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
) -> None:
    with pytest.raises(disposition_contract["validation_error"]):
        disposition_contract["get_disposition"](
            lot=quality_scope["lot"],
            warehouse=quality_scope["other_warehouse"],
        )

    assert disposition_contract["event_model"].objects.count() == 0


@pytest.mark.parametrize(
    ("expected", "target"),
    [
        ("HOLD", "HOLD"),
        ("RELEASED", "RELEASED"),
        ("INVALID", "RELEASED"),
        ("HOLD", "INVALID"),
        ("hold", "RELEASED"),
        ("HOLD", "released"),
        ("", "RELEASED"),
        ("HOLD", "ปล่อย"),
    ],
)
def test_invalid_or_noop_transition_adds_no_history(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    expected: str,
    target: str,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)

    with pytest.raises(disposition_contract["validation_error"]):
        disposition_contract["transition"](
            **transition_values(
                quality_scope,
                quality_user,
                expected_disposition=expected,
                target_disposition=target,
            )
        )

    assert disposition_contract["event_model"].objects.count() == 0


def test_stale_expected_state_conflicts_without_adding_history(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    transition = disposition_contract["transition"]
    transition(**transition_values(quality_scope, quality_user))

    with pytest.raises(disposition_contract["conflict_error"]):
        transition(
            **transition_values(
                quality_scope,
                quality_user,
                expected_disposition="HOLD",
                target_disposition="RELEASED",
            )
        )

    assert disposition_contract["event_model"].objects.count() == 1


@pytest.mark.parametrize("reason", [None, "", " ", "\t\r\n"])
def test_reason_must_be_nonblank(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    reason: str | None,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)

    with pytest.raises(disposition_contract["validation_error"]):
        disposition_contract["transition"](
            **transition_values(quality_scope, quality_user, reason=reason)
        )

    assert disposition_contract["event_model"].objects.count() == 0


@pytest.mark.parametrize("request_id", [None, "", "not-a-uuid", 123])
def test_request_key_must_be_a_uuid(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    request_id: object,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)

    with pytest.raises(disposition_contract["validation_error"]):
        disposition_contract["transition"](
            **transition_values(
                quality_scope,
                quality_user,
                request_id=request_id,
            )
        )

    assert disposition_contract["event_model"].objects.count() == 0


def test_exact_retry_returns_the_original_event_without_duplicate_history(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    values = transition_values(quality_scope, quality_user)

    first = disposition_contract["transition"](**values)
    retried = disposition_contract["transition"](**values)

    assert retried.pk == first.pk
    assert disposition_contract["event_model"].objects.count() == 1


@pytest.mark.parametrize(
    "changed_field",
    [
        "lot",
        "warehouse",
        "actor",
        "expected_disposition",
        "target_disposition",
        "reason",
    ],
)
def test_reused_request_key_with_different_payload_conflicts(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    other_user: Any,
    grant_role: Any,
    changed_field: str,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    grant_role(quality_user, quality_scope["sibling_warehouse"], "QUALITY")
    grant_role(other_user, quality_scope["warehouse"], "QUALITY")
    values = transition_values(quality_scope, quality_user)
    original = disposition_contract["transition"](**values)
    changed = dict(values)
    replacements = {
        "lot": quality_scope["second_lot"],
        "warehouse": quality_scope["sibling_warehouse"],
        "actor": other_user,
        "expected_disposition": "RELEASED",
        "target_disposition": "HOLD",
        "reason": "Different decision reason",
    }
    changed[changed_field] = replacements[changed_field]

    with pytest.raises(disposition_contract["conflict_error"]):
        disposition_contract["transition"](**changed)

    assert disposition_contract["event_model"].objects.count() == 1
    original.refresh_from_db()
    assert original.to_disposition == "RELEASED"


def test_request_id_is_stored_as_uuid(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)

    event = disposition_contract["transition"](
        **transition_values(quality_scope, quality_user)
    )

    event.refresh_from_db()
    assert isinstance(event.request_id, UUID)

