"""Cross-command and rollback races observed on real PostgreSQL connections."""

from decimal import Decimal
from queue import Queue
from threading import Thread
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction

from access_control.models import WarehouseRoleAssignment
from inventory.models import StockLedgerEntry, StockReceipt, StockTransfer
from inventory.services import receive_stock
from quality.models import LotDispositionEvent

from .test_atomic_transfer import balances, change_quality, post
from .test_atomic_transfer import transfer_scope as transfer_scope
from .test_stock_ledger_concurrency import wait_for_lock
from .test_stock_receipt_concurrency import blocked_action, receipt_worker


def contend(first, second, *, rollback_first):
    """Release a witnessed lock wait by commit or rollback, without timing guesses."""
    outcomes, pids = Queue(), Queue()
    thread = Thread(target=receipt_worker, args=(second, outcomes, pids))
    try:
        with transaction.atomic():
            result = first()
            thread.start()
            wait_for_lock(pids.get(timeout=5))
            if rollback_first:
                transaction.set_rollback(True)
    finally:
        if thread.ident:
            thread.join(timeout=12)
    assert not thread.is_alive()
    return result, outcomes.get(timeout=1)


def another_actor(scope):
    actor = get_user_model().objects.create(username="parallel-stock-command")
    for warehouse in (scope["warehouse"], scope["other"]):
        WarehouseRoleAssignment.objects.create(user=actor, warehouse=warehouse, role="WAREHOUSE")
    return actor


def receive(scope, key, *, warehouse=None, reason="Synthetic concurrent receipt"):
    return receive_stock(
        lot=scope["lot"],
        warehouse=warehouse or scope["warehouse"],
        actor=scope["actor"],
        quantity=Decimal("20"),
        reason=reason,
        request_id=key,
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("receipt_first", [False, True])
@pytest.mark.parametrize("rollback_first", [False, True])
def test_receipt_and_transfer_share_committed_stock_not_request_namespace(
    transfer_scope, receipt_first, rollback_first
):
    scope, key = transfer_scope, uuid4()
    parallel_actor = another_actor(scope)
    quality_before = list(LotDispositionEvent.objects.order_by("id").values())

    def receipt():
        return receive(scope, key)

    def transfer():
        return post(
            scope,
            actor=parallel_actor,
            request_id=key,
            quantity=Decimal("110" if receipt_first else "70"),
        )[0]

    _, outcome = contend(
        receipt if receipt_first else transfer,
        transfer if receipt_first else receipt,
        rollback_first=rollback_first,
    )
    if receipt_first and rollback_first:
        assert outcome[0] == "InsufficientStockError", outcome
        assert balances(scope) == (Decimal("100.000001"), 0)
        assert StockReceipt.objects.count() == StockTransfer.objects.count() == 0
        assert StockLedgerEntry.objects.count() == 1
    else:
        assert outcome[0] == "committed", outcome
        moved = Decimal("110" if receipt_first else "0" if rollback_first else "70")
        assert balances(scope) == (Decimal("120.000001") - moved, moved)
        assert StockReceipt.objects.get(request_id=key).ledger_entry.quantity_delta == 20
        assert StockTransfer.objects.count() == (0 if rollback_first else 1)
        assert StockLedgerEntry.objects.count() == (2 if rollback_first else 4)
        if not rollback_first:
            history = StockTransfer.objects.get(request_id=key)
            assert history.destination_entry.quantity_delta == moved
            assert history.source_entry.quantity_delta == -moved
    assert list(LotDispositionEvent.objects.order_by("id").values()) == quality_before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("reverse_first", [False, True])
def test_opposing_transfers_serialize_without_losing_stock(transfer_scope, reverse_first):
    scope = transfer_scope
    parallel_actor = another_actor(scope)
    receive(scope, uuid4(), warehouse=scope["other"])
    change_quality(scope, scope["other"], "RELEASED")
    quality_before = list(LotDispositionEvent.objects.order_by("id").values())
    forward_key, backward_key = uuid4(), uuid4()

    def forward():
        return post(scope, quantity=Decimal("70"), request_id=forward_key)[0]

    def backward():
        return post(
            scope,
            actor=parallel_actor,
            source_warehouse=scope["other"],
            destination_warehouse=scope["warehouse"],
            quantity=Decimal("15"),
            request_id=backward_key,
        )[0]

    _, outcome = blocked_action(
        backward if reverse_first else forward, forward if reverse_first else backward
    )
    assert outcome[0] == "committed", outcome
    assert balances(scope) == (Decimal("45.000001"), Decimal("75"))
    assert StockLedgerEntry.objects.count() == 6 and StockTransfer.objects.count() == 2
    assert set(StockTransfer.objects.values_list("request_id", flat=True)) == {
        forward_key,
        backward_key,
    }
    assert list(LotDispositionEvent.objects.order_by("id").values()) == quality_before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("command", ["receipt", "transfer"])
@pytest.mark.parametrize("changed_payload", [False, True])
def test_waiting_request_can_post_after_same_uuid_rolls_back(
    transfer_scope, command, changed_payload
):
    scope, key = transfer_scope, uuid4()

    def request(reason):
        if command == "receipt":
            return receive(scope, key, reason=reason)
        return post(scope, request_id=key, reason=reason)[0]

    reason = "Changed after rollback" if changed_payload else "Original request"
    original, outcome = contend(
        lambda: request("Original request"), lambda: request(reason), rollback_first=True
    )
    assert outcome[0] == "committed" and outcome[1] != original.pk, outcome
    if command == "receipt":
        history = StockReceipt.objects.get(request_id=key)
        assert history.pk == outcome[1] and history.ledger_entry.reason == reason
        assert balances(scope) == (Decimal("120.000001"), 0)
        assert StockLedgerEntry.objects.count() == 2 and StockTransfer.objects.count() == 0
    else:
        history = StockTransfer.objects.get(request_id=key)
        assert history.source_entry_id == outcome[1] and history.source_entry.reason == reason
        assert history.destination_entry.reason == reason
        assert balances(scope) == (Decimal("70"), Decimal("30.000001"))
        assert StockLedgerEntry.objects.count() == 3 and StockReceipt.objects.count() == 0
