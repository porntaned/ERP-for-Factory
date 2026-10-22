from queue import Queue
from threading import Thread
from time import monotonic, sleep

import pytest
from django.db import IntegrityError, close_old_connections, connection, connections, transaction

from .test_stock_ledger import raw_append


def worker(action, outcomes, pid_queue):
    close_old_connections()
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout='8s'")
                cursor.execute("SELECT pg_backend_pid()")
                pid_queue.put(cursor.fetchone()[0])
            action()
        outcomes.put("committed")
    except IntegrityError:
        outcomes.put("rejected")
    except Exception as exc:
        outcomes.put(f"unexpected:{type(exc).__name__}:{exc}")
    finally:
        connections.close_all()


def wait_for_lock(pid):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute("SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s", [pid])
            row = cursor.fetchone()
        if row and row[0] == "Lock":
            return
        sleep(0.01)
    pytest.fail("concurrent writer did not reach an observed PostgreSQL lock wait")


@pytest.mark.django_db(transaction=True)
def test_competing_debits_observe_committed_balance(ledger_contract, ledger_scope):
    model, balance = ledger_contract
    raw_append(ledger_scope, "10")
    outcomes, pids = Queue(), Queue()
    thread = Thread(target=worker, args=(lambda: raw_append(ledger_scope, "-7"), outcomes, pids))
    try:
        with transaction.atomic():
            raw_append(ledger_scope, "-7")
            thread.start()
            wait_for_lock(pids.get(timeout=5))
    finally:
        if thread.ident:
            thread.join(timeout=12)
    assert not thread.is_alive()
    assert outcomes.get(timeout=1) == "rejected"
    assert model.objects.count() == 2
    assert balance(lot=ledger_scope["lot"], warehouse=ledger_scope["warehouse"]) == 3


@pytest.mark.django_db(transaction=True)
def test_waiting_debit_observes_credit_rollback(ledger_contract, ledger_scope):
    outcomes, pids = Queue(), Queue()
    thread = Thread(target=worker, args=(lambda: raw_append(ledger_scope, "-1"), outcomes, pids))
    try:
        with transaction.atomic():
            raw_append(ledger_scope, "1")
            thread.start()
            wait_for_lock(pids.get(timeout=5))
            transaction.set_rollback(True)
    finally:
        if thread.ident:
            thread.join(timeout=12)
    assert not thread.is_alive()
    assert outcomes.get(timeout=1) == "rejected"
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mutation_first", [False, True])
def test_base_uom_mutation_and_first_entry_serialize(ledger_contract, ledger_scope, mutation_first):
    item = ledger_scope["item"]
    alternate = type(ledger_scope["uom"]).objects.create(code="EA", display_name="Each")
    mutate = lambda: type(item).objects.filter(pk=item.pk).update(base_uom=alternate)  # noqa: E731
    append = lambda: raw_append(ledger_scope, "1")  # noqa: E731
    first, second = (mutate, append) if mutation_first else (append, mutate)
    outcomes, pids = Queue(), Queue()
    thread = Thread(target=worker, args=(second, outcomes, pids))
    try:
        with transaction.atomic():
            first()
            thread.start()
            wait_for_lock(pids.get(timeout=5))
    finally:
        if thread.ident:
            thread.join(timeout=12)
    assert not thread.is_alive()
    assert outcomes.get(timeout=1) == ("committed" if mutation_first else "rejected")
    assert ledger_contract[0].objects.count() == 1
    item.refresh_from_db()
    assert item.base_uom_id == (alternate.pk if mutation_first else ledger_scope["uom"].pk)


@pytest.mark.django_db(transaction=True)
def test_quality_and_ledger_share_lot_lock(ledger_contract, ledger_scope):
    from quality.models import LotDispositionEvent

    outcomes, pids = Queue(), Queue()
    from uuid import uuid4

    def disposition():
        LotDispositionEvent.objects.create(
            lot=ledger_scope["lot"],
            warehouse=ledger_scope["warehouse"],
            actor=ledger_scope["actor"],
            request_id=uuid4(),
            from_disposition="HOLD",
            to_disposition="RELEASED",
            reason="Synthetic seam",
        )

    thread = Thread(target=worker, args=(disposition, outcomes, pids))
    try:
        with transaction.atomic():
            raw_append(ledger_scope, "1")
            thread.start()
            wait_for_lock(pids.get(timeout=5))
    finally:
        if thread.ident:
            thread.join(timeout=12)
    assert not thread.is_alive()
    assert outcomes.get(timeout=1) == "committed"
    assert LotDispositionEvent.objects.count() == 1
