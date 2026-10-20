from queue import Queue
from threading import Barrier, Thread
from typing import Any
from uuid import uuid4

import pytest
from django.apps import apps
from django.db import (
    DatabaseError,
    IntegrityError,
    close_old_connections,
    connection,
    connections,
    transaction,
)
from django.db.models.deletion import ProtectedError

pytestmark = pytest.mark.django_db


def direct_event_values(
    quality_scope: dict[str, Any],
    quality_user: Any,
    **overrides: Any,
) -> dict[str, Any]:
    values = {
        "lot": quality_scope["lot"],
        "warehouse": quality_scope["warehouse"],
        "actor": quality_user,
        "request_id": uuid4(),
        "from_disposition": "HOLD",
        "to_disposition": "RELEASED",
        "reason": "Direct PostgreSQL boundary test",
    }
    values.update(overrides)
    return values


def authorize_quality(
    grant_role: Any,
    quality_user: Any,
    quality_scope: dict[str, Any],
) -> Any:
    return grant_role(quality_user, quality_scope["warehouse"], "QUALITY")


def test_quality_suite_uses_postgresql(disposition_contract: dict[str, Any]) -> None:
    assert connection.vendor == "postgresql"


@pytest.mark.parametrize(
    "null_field",
    [
        "lot_id",
        "warehouse_id",
        "actor_id",
        "request_id",
        "from_disposition",
        "to_disposition",
        "reason",
    ],
)
def test_required_event_fields_reject_null_at_database_boundary(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    null_field: str,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    values = direct_event_values(quality_scope, quality_user)
    values[null_field] = None

    with pytest.raises(IntegrityError), transaction.atomic():
        disposition_contract["event_model"].objects.create(**values)


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"from_disposition": "INVALID"}, IntegrityError),
        ({"to_disposition": "INVALID"}, IntegrityError),
        ({"from_disposition": "hold"}, IntegrityError),
        ({"to_disposition": "ปล่อย"}, IntegrityError),
        ({"to_disposition": "HOLD"}, IntegrityError),
        ({"reason": ""}, IntegrityError),
        ({"reason": " \t\r\n"}, IntegrityError),
    ],
)
def test_state_and_reason_constraints_reject_direct_invalid_writes(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    overrides: dict[str, Any],
    error: type[DatabaseError],
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)

    with pytest.raises(error), transaction.atomic():
        disposition_contract["event_model"].objects.create(
            **direct_event_values(quality_scope, quality_user, **overrides)
        )


@pytest.mark.parametrize("invalid_field", ["lot_id", "warehouse_id", "actor_id"])
def test_invalid_references_fail_at_database_boundary(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    invalid_field: str,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    values = direct_event_values(quality_scope, quality_user)
    values[invalid_field] = 2_147_483_647

    with pytest.raises(IntegrityError), transaction.atomic():
        disposition_contract["event_model"].objects.create(**values)


def test_request_id_is_unique_at_database_boundary(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    event_model = disposition_contract["event_model"]
    request_id = uuid4()
    event_model.objects.create(
        **direct_event_values(quality_scope, quality_user, request_id=request_id)
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        event_model.objects.create(
            **direct_event_values(
                quality_scope,
                quality_user,
                request_id=request_id,
                from_disposition="RELEASED",
                to_disposition="HOLD",
            )
        )

    assert event_model.objects.count() == 1


def test_direct_write_cannot_forge_the_event_chain(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    event_model = disposition_contract["event_model"]
    event_model.objects.create(**direct_event_values(quality_scope, quality_user))

    with pytest.raises(IntegrityError), transaction.atomic():
        event_model.objects.create(
            **direct_event_values(
                quality_scope,
                quality_user,
                from_disposition="HOLD",
                to_disposition="RELEASED",
            )
        )

    assert event_model.objects.count() == 1


def test_direct_write_rejects_cross_organization_pair(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    grant_role(quality_user, quality_scope["other_warehouse"], "QUALITY")

    with pytest.raises(IntegrityError), transaction.atomic():
        disposition_contract["event_model"].objects.create(
            **direct_event_values(
                quality_scope,
                quality_user,
                warehouse=quality_scope["other_warehouse"],
            )
        )


def test_recorded_event_cannot_be_updated_or_deleted(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    event_model = disposition_contract["event_model"]
    event = event_model.objects.create(
        **direct_event_values(quality_scope, quality_user)
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        event_model.objects.filter(pk=event.pk).update(reason="Rewritten reason")
    with pytest.raises(IntegrityError), transaction.atomic():
        event_model.objects.filter(pk=event.pk).delete()

    event.refresh_from_db()
    assert event.reason == "Direct PostgreSQL boundary test"
    assert event_model.objects.filter(pk=event.pk).count() == 1


@pytest.mark.parametrize("protected_name", ["lot", "warehouse", "actor"])
def test_recorded_event_protects_referenced_records(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    protected_name: str,
) -> None:
    assignment = authorize_quality(grant_role, quality_user, quality_scope)
    disposition_contract["event_model"].objects.create(
        **direct_event_values(quality_scope, quality_user)
    )
    protected = {
        "lot": quality_scope["lot"],
        "warehouse": quality_scope["warehouse"],
        "actor": quality_user,
    }[protected_name]
    if protected_name in {"warehouse", "actor"}:
        assignment.delete()

    with pytest.raises(ProtectedError):
        protected.delete()


def test_service_failure_rolls_back_without_partial_history(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    event_model = disposition_contract["event_model"]
    event_model.objects.create(**direct_event_values(quality_scope, quality_user))

    with pytest.raises(disposition_contract["conflict_error"]):
        disposition_contract["transition"](
            lot=quality_scope["lot"],
            warehouse=quality_scope["warehouse"],
            actor=quality_user,
            expected_disposition="HOLD",
            target_disposition="RELEASED",
            reason="Stale command must roll back",
            request_id=uuid4(),
        )

    assert event_model.objects.count() == 1
    assert (
        disposition_contract["get_disposition"](
            lot=quality_scope["lot"],
            warehouse=quality_scope["warehouse"],
        )
        == "RELEASED"
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_exact_retries_converge_on_one_event(
    disposition_contract: dict[str, Any],
) -> None:
    objects = create_concurrency_scope(disposition_contract)
    request_id = uuid4()
    barrier = Barrier(2)
    results: Queue[tuple[str, int | str]] = Queue()

    def transition() -> None:
        close_old_connections()
        try:
            lot = apps.get_model("inventory", "Lot").objects.get(pk=objects["lot_id"])
            warehouse = apps.get_model("facilities", "Warehouse").objects.get(
                pk=objects["warehouse_id"]
            )
            actor = apps.get_model("auth", "User").objects.get(pk=objects["user_id"])
            barrier.wait(timeout=10)
            event = disposition_contract["transition"](
                lot=lot,
                warehouse=warehouse,
                actor=actor,
                expected_disposition="HOLD",
                target_disposition="RELEASED",
                reason="Concurrent exact retry",
                request_id=request_id,
            )
            results.put(("event", event.pk))
        except Exception as error:  # Surface harness and contract failures.
            results.put(("error", f"{type(error).__name__}:{error}"))
        finally:
            connections.close_all()

    workers = [Thread(target=transition), Thread(target=transition)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)

    assert not any(worker.is_alive() for worker in workers)
    outcomes = [results.get(timeout=1) for _ in range(2)]
    assert [kind for kind, _ in outcomes] == ["event", "event"]
    assert len({value for _, value in outcomes}) == 1
    assert disposition_contract["event_model"].objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_distinct_commands_allow_one_authoritative_transition(
    disposition_contract: dict[str, Any],
) -> None:
    objects = create_concurrency_scope(disposition_contract)
    barrier = Barrier(2)
    results: Queue[str] = Queue()

    def transition() -> None:
        close_old_connections()
        try:
            lot = apps.get_model("inventory", "Lot").objects.get(pk=objects["lot_id"])
            warehouse = apps.get_model("facilities", "Warehouse").objects.get(
                pk=objects["warehouse_id"]
            )
            actor = apps.get_model("auth", "User").objects.get(pk=objects["user_id"])
            barrier.wait(timeout=10)
            disposition_contract["transition"](
                lot=lot,
                warehouse=warehouse,
                actor=actor,
                expected_disposition="HOLD",
                target_disposition="RELEASED",
                reason="Concurrent distinct command",
                request_id=uuid4(),
            )
            results.put("created")
        except disposition_contract["conflict_error"]:
            results.put("conflict")
        except Exception as error:  # Surface harness and contract failures.
            results.put(f"unexpected:{type(error).__name__}:{error}")
        finally:
            connections.close_all()

    workers = [Thread(target=transition), Thread(target=transition)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)

    assert not any(worker.is_alive() for worker in workers)
    outcomes = sorted(results.get(timeout=1) for _ in range(2))
    assert outcomes == ["conflict", "created"]
    assert disposition_contract["event_model"].objects.count() == 1


def create_concurrency_scope(disposition_contract: dict[str, Any]) -> dict[str, int]:
    organization_model = apps.get_model("facilities", "Organization")
    plant_model = apps.get_model("facilities", "Plant")
    warehouse_model = apps.get_model("facilities", "Warehouse")
    uom_model = apps.get_model("catalog", "UnitOfMeasure")
    item_model = apps.get_model("catalog", "Item")
    lot_model = apps.get_model("inventory", "Lot")
    user_model = apps.get_model("auth", "User")
    assignment_model = apps.get_model("access_control", "WarehouseRoleAssignment")

    organization = organization_model.objects.create(code="RACE", display_name="Race")
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
    uom = uom_model.objects.create(code="RACE-EA", display_name="Race each")
    item = item_model.objects.create(
        organization=organization,
        code="RACE-ITEM",
        display_name="Race item",
        item_type="RAW",
        base_uom=uom,
    )
    lot = lot_model.objects.create(item=item, code="RACE-LOT")
    user = user_model(username="synthetic-race-quality-user")
    user.set_unusable_password()
    user.save()
    assignment_model.objects.create(user=user, warehouse=warehouse, role="QUALITY")

    return {"lot_id": lot.pk, "warehouse_id": warehouse.pk, "user_id": user.pk}
