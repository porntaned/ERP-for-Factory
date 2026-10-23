"""Observed PostgreSQL lock waits, never timing-only race assertions."""

from importlib import import_module
from queue import Queue
from threading import Thread
from uuid import uuid4

import pytest
from django.apps import apps
from django.db import close_old_connections, connection, connections, transaction

from .test_stock_ledger_concurrency import wait_for_lock
from .test_stock_receipt import receipt_contract as receipt_contract
from .test_stock_receipt import receipt_scope as receipt_scope
from .test_stock_receipt import receipt_values


def receipt_worker(action, outcomes, pids):
    close_old_connections()
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout='8s'")
                cursor.execute("SELECT pg_backend_pid()")
                pids.put(cursor.fetchone()[0])
            result = action()
        outcomes.put(("committed", result.pk))
    except Exception as exc:
        outcomes.put((type(exc).__name__, str(exc)))
    finally:
        connections.close_all()


def blocked_action(first, second):
    outcomes, pids = Queue(), Queue()
    thread = Thread(target=receipt_worker, args=(second, outcomes, pids))
    try:
        with transaction.atomic():
            result = first()
            thread.start()
            wait_for_lock(pids.get(timeout=5))
    finally:
        if thread.ident:
            thread.join(timeout=12)
    assert not thread.is_alive()
    return result, outcomes.get(timeout=1)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("different_payload", [False, True])
def test_concurrent_same_key_posts_once(
    receipt_contract, receipt_scope, ledger_contract, different_payload
):
    values = receipt_values(receipt_scope)
    second = values | ({"reason": "Different delivery"} if different_payload else {})
    original, outcome = blocked_action(
        lambda: receipt_contract["receive"](**values),
        lambda: receipt_contract["receive"](**second),
    )
    if different_payload:
        assert outcome[0] == "ReceiptConflictError", outcome
    else:
        assert outcome == ("committed", original.pk)
    assert receipt_contract["model"].objects.count() == 1
    assert ledger_contract[0].objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_cross_lot_key_race_rolls_back_losing_ledger(
    receipt_contract, receipt_scope, ledger_contract
):
    values = receipt_values(receipt_scope)
    actor = type(receipt_scope["actor"]).objects.create(username="parallel-receiver")
    apps.get_model("access_control", "WarehouseRoleAssignment").objects.create(
        user=actor, warehouse=receipt_scope["warehouse"], role="WAREHOUSE"
    )
    _, outcome = blocked_action(
        lambda: receipt_contract["receive"](**values),
        lambda: receipt_contract["receive"](
            **(values | {"lot": receipt_scope["second"], "actor": actor})
        ),
    )
    assert outcome[0] == "ReceiptConflictError", outcome
    assert receipt_contract["model"].objects.count() == 1
    assert ledger_contract[0].objects.count() == 1
    assert (
        ledger_contract[1](lot=receipt_scope["second"], warehouse=receipt_scope["warehouse"]) == 0
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mutation", ["revoke", "deactivate"])
def test_waiting_receipt_observes_committed_authorization_loss(
    receipt_contract, receipt_scope, ledger_contract, mutation
):
    scope = receipt_scope

    def change():
        if mutation == "revoke":
            scope["grant"].delete()
        else:
            type(scope["actor"]).objects.filter(pk=scope["actor"].pk).update(is_active=False)

    _, outcome = blocked_action(
        change, lambda: receipt_contract["receive"](**receipt_values(scope))
    )
    assert outcome[0] == "ReceiptAuthorizationError", outcome
    assert receipt_contract["model"].objects.count() == 0
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mutation", ["revoke", "deactivate"])
def test_authorization_mutation_waits_for_receipt_commit(
    receipt_contract, receipt_scope, ledger_contract, mutation
):
    scope = receipt_scope

    def change():
        if mutation == "revoke":
            type(scope["grant"]).objects.filter(pk=scope["grant"].pk).delete()
        else:
            type(scope["actor"]).objects.filter(pk=scope["actor"].pk).update(is_active=False)
        return scope["lot"]

    _, outcome = blocked_action(
        lambda: receipt_contract["receive"](**receipt_values(scope)), change
    )
    assert outcome[0] == "committed", outcome
    assert receipt_contract["model"].objects.count() == 1
    assert ledger_contract[0].objects.count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("quality_first", [True, False])
def test_receipt_and_quality_share_lot_serialization(
    receipt_contract, receipt_scope, quality_first
):
    scope = receipt_scope
    # Separate actors ensure the observed wait is not their User row lock.
    quality_actor = type(scope["actor"]).objects.create(username="quality-concurrent")
    apps.get_model("access_control", "WarehouseRoleAssignment").objects.create(
        user=quality_actor, warehouse=scope["warehouse"], role="QUALITY"
    )
    quality = import_module("quality.services")

    def transition():
        return quality.transition_lot_disposition(
            lot=scope["lot"],
            warehouse=scope["warehouse"],
            actor=quality_actor,
            expected_disposition="HOLD",
            target_disposition="RELEASED",
            reason="Synthetic accepted",
            request_id=uuid4(),
        )

    def receive():
        return receipt_contract["receive"](**receipt_values(scope))

    _, outcome = blocked_action(
        transition if quality_first else receive, receive if quality_first else transition
    )
    assert outcome[0] == "committed", outcome
    assert receipt_contract["model"].objects.count() == 1
    assert apps.get_model("quality", "LotDispositionEvent").objects.count() == 1
    assert quality.get_lot_disposition(lot=scope["lot"], warehouse=scope["warehouse"]) == "RELEASED"
