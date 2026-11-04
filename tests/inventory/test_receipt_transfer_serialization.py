"""M4.4: command-level serialization of receipt and transfer on one Lot-Warehouse pair.

Existing suites cover receipt vs Quality, transfer vs Quality/authorization and competing
transfers. These tests close the remaining pair: a transfer that depends on stock being
received concurrently must observe the committed (or rolled back) receipt, never a stale
balance. Waits are observed in PostgreSQL via pg_blocking_pids, not inferred from timing.
"""

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

from .test_atomic_transfer import balances, post
from .test_atomic_transfer import transfer_scope as transfer_scope
from .test_stock_ledger_concurrency import wait_for_lock
from .test_stock_receipt_concurrency import blocked_action, receipt_worker

# transfer_scope starts with 100.000001 in the source warehouse. 150 exceeds that
# balance on its own, so it can only succeed after the concurrent receipt commits.
START = Decimal("100.000001")
RECEIVED = Decimal("60")
TRANSFERRED = Decimal("150")


@pytest.fixture
def race_scope(transfer_scope):
    """Receipt and transfer use DIFFERENT actors.

    One actor would already serialize on its own User/grant rows (both commands lock
    them FOR UPDATE), which would hide whether the Lot-level lock does its job.
    """
    receiver = get_user_model().objects.create(username="synthetic-receiver")
    receiver.set_unusable_password()
    receiver.save()
    WarehouseRoleAssignment.objects.create(
        user=receiver, warehouse=transfer_scope["warehouse"], role="WAREHOUSE"
    )
    return transfer_scope | {"receiver": receiver}


def receive(scope, quantity=RECEIVED):
    return receive_stock(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=scope["receiver"],
        quantity=quantity,
        reason="Synthetic concurrent delivery — ทดสอบ",
        request_id=uuid4(),
    )


@pytest.mark.django_db(transaction=True)
def test_waiting_transfer_observes_committed_receipt(race_scope):
    scope = race_scope
    receipt, outcome = blocked_action(
        lambda: receive(scope),
        lambda: post(scope, quantity=TRANSFERRED)[0],
    )
    assert outcome[0] == "committed", outcome
    assert balances(scope) == (START + RECEIVED - TRANSFERRED, TRANSFERRED)
    assert StockReceipt.objects.filter(pk=receipt.pk).count() == 1
    assert StockTransfer.objects.count() == 1
    # starting stock + receipt + debit + credit
    assert StockLedgerEntry.objects.count() == 4


@pytest.mark.django_db(transaction=True)
def test_waiting_transfer_observes_receipt_rollback(race_scope):
    scope = race_scope
    outcomes, pids = Queue(), Queue()
    thread = Thread(
        target=receipt_worker,
        args=(lambda: post(scope, quantity=TRANSFERRED)[0], outcomes, pids),
    )
    try:
        with transaction.atomic():
            receive(scope)
            thread.start()
            wait_for_lock(pids.get(timeout=5))
            transaction.set_rollback(True)
    finally:
        if thread.ident:
            thread.join(timeout=12)
    assert not thread.is_alive()
    outcome = outcomes.get(timeout=1)
    assert outcome[0] == "InsufficientStockError", outcome
    assert balances(scope) == (START, 0)
    assert StockReceipt.objects.count() == 0
    assert StockTransfer.objects.count() == 0
    assert StockLedgerEntry.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_waiting_receipt_does_not_change_transfer_that_committed_first(race_scope):
    scope = race_scope
    transferred = Decimal("30.000001")
    first, outcome = blocked_action(
        lambda: post(scope, quantity=transferred)[0],
        lambda: receive(scope),
    )
    assert outcome[0] == "committed", outcome
    assert balances(scope) == (START - transferred + RECEIVED, transferred)
    assert StockTransfer.objects.count() == 1
    assert StockReceipt.objects.count() == 1
    assert StockLedgerEntry.objects.count() == 4
    assert first.quantity_delta == -transferred
