from queue import Queue
from threading import Barrier, Event, Thread
from time import monotonic
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
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.utils import timezone

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


@pytest.mark.django_db(transaction=True)
def test_history_identity_migration_reverses_and_reapplies() -> None:
    latest = [("quality", "0002_preserve_history_identity")]
    try:
        MigrationExecutor(connection).migrate([("quality", "0001_initial")])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT proname FROM pg_proc WHERE oid = ("
                "SELECT tgfoid FROM pg_trigger WHERE tgname = %s)",
                ["quality_lot_disposition_validate_insert"],
            )
            assert cursor.fetchone()[0] == "quality_validate_lot_disposition_insert"
    finally:
        MigrationExecutor(connection).migrate(latest)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT proname FROM pg_proc WHERE oid = ("
            "SELECT tgfoid FROM pg_trigger WHERE tgname = %s)",
            ["quality_lot_disposition_validate_insert"],
        )
        assert cursor.fetchone()[0] == "quality_validate_lot_disposition_insert_v2"


def test_created_at_is_required_and_direct_insert_supplies_aware_server_time(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    authorize_quality(grant_role, quality_user, quality_scope)
    event_model = disposition_contract["event_model"]
    assert event_model._meta.get_field("created_at").null is False
    before = timezone.now()

    event = event_model.objects.create(**direct_event_values(quality_scope, quality_user))
    event.refresh_from_db()
    after = timezone.now()

    assert timezone.is_aware(event.created_at)
    assert before <= event.created_at <= after


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


@pytest.mark.django_db(transaction=True)
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


def test_descending_event_id_is_rejected_without_hiding_the_next_decision(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
) -> None:
    event_model = disposition_contract["event_model"]
    released = event_model.objects.create(**direct_event_values(quality_scope, quality_user))
    hold_values = direct_event_values(
        quality_scope,
        quality_user,
        from_disposition="RELEASED",
        to_disposition="HOLD",
    )
    with pytest.raises(IntegrityError, match="event id must increase"), transaction.atomic():
        event_model.objects.create(id=released.pk - 1, **hold_values)
    assert (
        disposition_contract["get_disposition"](
            lot=quality_scope["lot"],
            warehouse=quality_scope["warehouse"],
        )
        == "RELEASED"
    )
    held = event_model.objects.create(**hold_values)
    assert held.pk > released.pk
    assert (
        disposition_contract["get_disposition"](
            lot=quality_scope["lot"],
            warehouse=quality_scope["warehouse"],
        )
        == "HOLD"
    )


def identity_update(scope: dict[str, Any], edge: str) -> tuple[Any, dict[str, int]]:
    lot = scope["lot"]
    warehouse = scope["warehouse"]
    if edge == "lot_item":
        item = lot.item
        replacement = type(item).objects.create(
            organization=item.organization,
            code="REPLACEMENT",
            display_name="Replacement item",
            item_type="RAW",
            base_uom=item.base_uom,
        )
        return lot, {"item_id": replacement.pk}
    organization_model = apps.get_model("facilities", "Organization")
    target_organization = organization_model.objects.create(
        code="REPARENT", display_name="Synthetic reassignment target"
    )
    if edge == "item_organization":
        return lot.item, {"organization_id": target_organization.pk}
    if edge == "warehouse_plant":
        target_plant = type(warehouse.plant).objects.create(
            organization=target_organization, code="TARGET", display_name="Target plant"
        )
        return warehouse, {"plant_id": target_plant.pk}
    return warehouse.plant, {"organization_id": target_organization.pk}


@pytest.mark.parametrize(
    "edge",
    ["lot_item", "item_organization", "warehouse_plant", "plant_organization"],
)
def test_recorded_history_prevents_identity_edge_reassignment(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    edge: str,
) -> None:
    record, changes = identity_update(quality_scope, edge)
    original = {field: getattr(record, field) for field in changes}
    disposition_contract["event_model"].objects.create(
        **direct_event_values(quality_scope, quality_user)
    )
    with (
        pytest.raises(IntegrityError, match="recorded disposition identity"),
        transaction.atomic(),
    ):
        type(record).objects.filter(pk=record.pk).update(**changes)
    record.refresh_from_db()
    assert {field: getattr(record, field) for field in changes} == original


@pytest.mark.parametrize(
    "edge",
    ["lot_item", "item_organization", "warehouse_plant", "plant_organization"],
)
def test_unreferenced_identity_edge_can_still_change(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    edge: str,
) -> None:
    record, changes = identity_update(quality_scope, edge)
    assert type(record).objects.filter(pk=record.pk).update(**changes) == 1
    record.refresh_from_db()
    assert {field: getattr(record, field) for field in changes} == changes


def test_history_allows_metadata_and_unchanged_identity_updates(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
) -> None:
    disposition_contract["event_model"].objects.create(
        **direct_event_values(quality_scope, quality_user)
    )
    lot = quality_scope["lot"]
    warehouse = quality_scope["warehouse"]
    records = [lot, lot.item, warehouse, warehouse.plant]
    for record in records:
        changes = {"code": record.code + "-EDIT"}
        if record is lot:
            changes["item_id"] = record.item_id
        elif record is warehouse:
            changes["plant_id"] = record.plant_id
        else:
            changes["organization_id"] = record.organization_id
        assert type(record).objects.filter(pk=record.pk).update(**changes) == 1


def wait_for_database_block(worker_pid: int) -> None:
    deadline = monotonic() + 10
    while monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid() = ANY(pg_blocking_pids(%s))", [worker_pid])
            if cursor.fetchone()[0]:
                return
        Event().wait(0.01)
    pytest.fail("worker did not reach the expected PostgreSQL row lock")


@pytest.mark.django_db(transaction=True)
def test_grant_revoked_while_waiting_for_lot_lock_denies_append(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
) -> None:
    assignment = authorize_quality(grant_role, quality_user, quality_scope)
    pids: Queue[int] = Queue()
    outcomes: Queue[str] = Queue()

    def transition() -> None:
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids.put(cursor.fetchone()[0])
            disposition_contract["transition"](
                lot=quality_scope["lot"],
                warehouse=quality_scope["warehouse"],
                actor=quality_user,
                expected_disposition="HOLD",
                target_disposition="RELEASED",
                reason="Revocation during wait",
                request_id=uuid4(),
            )
            outcomes.put("created")
        except disposition_contract["authorization_error"]:
            outcomes.put("denied")
        except Exception as error:
            outcomes.put(f"unexpected:{type(error).__name__}:{error}")
        finally:
            connections.close_all()

    worker = Thread(target=transition)
    try:
        with transaction.atomic():
            type(quality_scope["lot"]).objects.select_for_update().get(pk=quality_scope["lot"].pk)
            worker.start()
            wait_for_database_block(pids.get(timeout=10))
            assignment.delete()
    finally:
        if worker.ident is not None:
            worker.join(timeout=15)
    assert not worker.is_alive()
    assert outcomes.get(timeout=1) == "denied"
    assert disposition_contract["event_model"].objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "edge",
    ["lot_item", "item_organization", "warehouse_plant", "plant_organization"],
)
def test_identity_update_waits_for_new_history_then_rejects_reassignment(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    edge: str,
) -> None:
    record, changes = identity_update(quality_scope, edge)
    pids: Queue[int] = Queue()
    outcomes: Queue[str] = Queue()

    def reassign() -> None:
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids.put(cursor.fetchone()[0])
            type(record).objects.filter(pk=record.pk).update(**changes)
            outcomes.put("changed")
        except IntegrityError as error:
            outcomes.put(str(error))
        except Exception as error:
            outcomes.put(f"unexpected:{type(error).__name__}:{error}")
        finally:
            connections.close_all()

    worker = Thread(target=reassign)
    try:
        with transaction.atomic():
            disposition_contract["event_model"].objects.create(
                **direct_event_values(quality_scope, quality_user)
            )
            worker.start()
            wait_for_database_block(pids.get(timeout=10))
    finally:
        if worker.ident is not None:
            worker.join(timeout=15)
    assert not worker.is_alive()
    assert "recorded disposition identity" in outcomes.get(timeout=1)


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
    event = event_model.objects.create(**direct_event_values(quality_scope, quality_user))

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


@pytest.mark.django_db(transaction=True)
def test_concurrent_direct_inserts_serialize_one_transition(
    disposition_contract: dict[str, Any],
) -> None:
    objects = create_concurrency_scope(disposition_contract)
    barrier = Barrier(2)
    results: Queue[str] = Queue()

    def insert_event() -> None:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            with transaction.atomic():
                disposition_contract["event_model"].objects.create(
                    lot_id=objects["lot_id"],
                    warehouse_id=objects["warehouse_id"],
                    actor_id=objects["user_id"],
                    request_id=uuid4(),
                    from_disposition="HOLD",
                    to_disposition="RELEASED",
                    reason="Concurrent direct PostgreSQL insert",
                )
            results.put("created")
        except IntegrityError:
            results.put("integrity_error")
        except Exception as error:  # Surface harness and trigger failures.
            results.put(f"unexpected:{type(error).__name__}:{error}")
        finally:
            connections.close_all()

    workers = [Thread(target=insert_event), Thread(target=insert_event)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)

    assert not any(worker.is_alive() for worker in workers)
    outcomes = sorted(results.get(timeout=1) for _ in range(2))
    assert outcomes == ["created", "integrity_error"]
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
