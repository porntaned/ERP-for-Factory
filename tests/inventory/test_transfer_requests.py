"""UUID replay contract, legacy preservation, and real PostgreSQL request races."""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from access_control.models import WarehouseRoleAssignment
from inventory.models import StockLedgerEntry, StockTransfer
from inventory.transfers import (
    TransferAuthorizationError,
    TransferConflictError,
    TransferValidationError,
)

from .test_atomic_transfer import balances, change_quality, post
from .test_atomic_transfer import transfer_scope as transfer_scope
from .test_stock_receipt_concurrency import blocked_action
from .test_transfer_history import entries


@pytest.mark.django_db
def test_exact_replay_returns_original_rows_without_extra_movement(transfer_scope):
    scope, key = transfer_scope, uuid4()
    first = post(scope, request_id=key)
    history = StockTransfer.objects.get(request_id=key)
    replay = post(scope, request_id=key, quantity=Decimal("30.0000010"))
    assert tuple(e.pk for e in replay) == tuple(e.pk for e in first)
    assert StockTransfer.objects.get(request_id=key).created_at == history.created_at
    assert StockLedgerEntry.objects.count() == 3 and StockTransfer.objects.count() == 1
    assert balances(scope) == (Decimal("70"), Decimal("30.000001"))


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["quantity", "reason", "lot", "direction", "actor"])
def test_changed_payload_conflicts_even_if_quality_would_reject(transfer_scope, field):
    scope, key = transfer_scope, uuid4()
    post(scope, request_id=key)
    changes = dict(request_id=key)
    if field == "quantity":
        changes["quantity"] = Decimal("1")
    elif field == "reason":
        changes["reason"] = "Changed reason"
    elif field == "lot":
        changes["lot"] = scope["second"]
    elif field == "direction":
        changes.update(source_warehouse=scope["other"], destination_warehouse=scope["warehouse"])
    else:
        actor = get_user_model().objects.create(username="other-request-actor")
        for warehouse in (scope["warehouse"], scope["other"]):
            WarehouseRoleAssignment.objects.create(
                user=actor, warehouse=warehouse, role="WAREHOUSE"
            )
        changes["actor"] = actor
    with pytest.raises(TransferConflictError):
        post(scope, **changes)
    assert StockLedgerEntry.objects.count() == 3 and StockTransfer.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("key", [None, "uuid-text", 1, True])
def test_request_id_requires_uuid_object(transfer_scope, key):
    with pytest.raises(TransferValidationError, match="UUID"):
        post(transfer_scope, request_id=key)
    assert StockLedgerEntry.objects.count() == 1 and StockTransfer.objects.count() == 0


@pytest.mark.django_db
def test_replay_after_hold_and_exhausted_balance_returns_only_history(transfer_scope):
    scope, key = transfer_scope, uuid4()
    first = post(scope, request_id=key, quantity=Decimal("100.000001"))
    change_quality(scope, scope["warehouse"], "HOLD")
    replay = post(scope, request_id=key, quantity=Decimal("100.000001"))
    assert tuple(e.pk for e in replay) == tuple(e.pk for e in first)
    assert balances(scope) == (0, Decimal("100.000001"))
    assert StockTransfer.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("change", ["inactive", "source", "destination"])
def test_replay_still_requires_current_actor_and_both_grants(transfer_scope, change):
    scope, key = transfer_scope, uuid4()
    post(scope, request_id=key)
    if change == "inactive":
        type(scope["actor"]).objects.filter(pk=scope["actor"].pk).update(is_active=False)
    else:
        WarehouseRoleAssignment.objects.filter(
            user=scope["actor"],
            role="WAREHOUSE",
            warehouse=scope["warehouse" if change == "source" else "other"],
        ).delete()
    with pytest.raises(TransferAuthorizationError):
        post(scope, request_id=key)
    assert StockLedgerEntry.objects.count() == 3


@pytest.mark.django_db
def test_distinct_keys_are_distinct_transfers_and_keys_are_immutable(transfer_scope):
    scope = transfer_scope
    first, second = uuid4(), uuid4()
    post(scope, request_id=first)
    post(scope, request_id=second)
    with pytest.raises(IntegrityError, match="immutable"), transaction.atomic():
        StockTransfer.objects.filter(request_id=first).update(request_id=uuid4())
    assert StockTransfer.objects.count() == 2 and StockLedgerEntry.objects.count() == 5


@pytest.mark.django_db
def test_global_uuid_uniqueness_is_enforced_by_postgresql(transfer_scope):
    key = uuid4()
    post(transfer_scope, request_id=key)
    debit, credit = entries(transfer_scope)
    with pytest.raises(IntegrityError, match="request_id"), transaction.atomic():
        StockTransfer.objects.create(source_entry=debit, destination_entry=credit, request_id=key)


@pytest.mark.django_db
def test_outer_rollback_does_not_consume_request_id(transfer_scope):
    key = uuid4()
    with transaction.atomic():
        post(transfer_scope, request_id=key)
        transaction.set_rollback(True)
    assert not StockTransfer.objects.filter(request_id=key).exists()
    post(transfer_scope, request_id=key)
    assert StockTransfer.objects.count() == 1 and StockLedgerEntry.objects.count() == 3


@pytest.mark.django_db
def test_failed_history_insert_rolls_back_and_same_key_can_retry(transfer_scope):
    key = uuid4()
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE FUNCTION pg_temp.reject_request() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic request failure' USING ERRCODE='23514'; END; $$;
            CREATE TRIGGER test_reject_request BEFORE INSERT ON inventory_stocktransfer
            FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_request();
        """)
    try:
        with pytest.raises(IntegrityError, match="synthetic request failure"):
            post(transfer_scope, request_id=key)
        assert StockLedgerEntry.objects.count() == 1 and StockTransfer.objects.count() == 0
    finally:
        with connection.cursor() as cursor:
            cursor.execute("DROP TRIGGER test_reject_request ON inventory_stocktransfer")
            cursor.execute("DROP FUNCTION pg_temp.reject_request()")
    post(transfer_scope, request_id=key)
    assert StockLedgerEntry.objects.count() == 3


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("changed", [False, True])
def test_concurrent_same_key_has_one_post(transfer_scope, changed):
    scope, key = transfer_scope, uuid4()
    first, outcome = blocked_action(
        lambda: post(scope, request_id=key)[0],
        lambda: post(scope, request_id=key, **({"reason": "Changed"} if changed else {}))[0],
    )
    assert outcome[0] == ("TransferConflictError" if changed else "committed"), outcome
    if not changed:
        assert outcome[1] == first.pk
    assert StockTransfer.objects.count() == 1 and StockLedgerEntry.objects.count() == 3


@pytest.mark.django_db(transaction=True)
def test_cross_lot_uuid_race_rolls_back_all_losing_entries(transfer_scope):
    scope, key = transfer_scope, uuid4()
    other_actor = get_user_model().objects.create(username="parallel-request-actor")
    for warehouse in (scope["warehouse"], scope["other"]):
        WarehouseRoleAssignment.objects.create(
            user=other_actor, warehouse=warehouse, role="WAREHOUSE"
        )
    second = scope | dict(lot=scope["second"], actor=other_actor)
    StockLedgerEntry.objects.create(
        lot=second["lot"],
        warehouse=second["warehouse"],
        actor=other_actor,
        quantity_delta=Decimal("100"),
        reason="Synthetic second stock",
    )
    change_quality(scope | dict(lot=scope["second"]), scope["warehouse"], "RELEASED")
    _, outcome = blocked_action(
        lambda: post(scope, request_id=key)[0],
        lambda: post(second, request_id=key)[0],
    )
    assert outcome[0] == "TransferConflictError", outcome
    assert balances(second) == (100, 0)
    assert StockLedgerEntry.objects.count() == 4 and StockTransfer.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_upgrade_retains_null_legacy_ids_without_adopting_requests(transfer_scope):
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        executor = MigrationExecutor(connection)
        executor.migrate([("inventory", "0005_stock_transfer")])
        old_transfer = executor.loader.project_state(
            [("inventory", "0005_stock_transfer")]
        ).apps.get_model("inventory", "StockTransfer")
        legacy = []
        for _ in range(2):
            debit, credit = entries(transfer_scope)
            legacy.append(
                old_transfer.objects.create(
                    source_entry_id=debit.pk, destination_entry_id=credit.pk
                ).pk
            )
        MigrationExecutor(connection).migrate(latest)
        assert StockTransfer.objects.filter(pk__in=legacy, request_id__isnull=True).count() == 2
        post(transfer_scope, request_id=uuid4())
        assert StockTransfer.objects.count() == 3
        assert StockTransfer.objects.filter(pk__in=legacy, request_id__isnull=True).count() == 2
    finally:
        MigrationExecutor(connection).migrate(latest)
