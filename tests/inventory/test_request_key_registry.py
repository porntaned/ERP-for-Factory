"""M4.4.1: one request UUID belongs to exactly one command type across the system.

Same-command exact replay is covered elsewhere and must keep working. These tests cover
a UUID first used by one command and then offered to a different command.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction

from inventory.models import StockLedgerEntry, StockReceipt, StockTransfer
from inventory.services import ReceiptConflictError, receive_stock
from inventory.transfers import TransferConflictError
from quality.services import DispositionConflictError, transition_lot_disposition

from .test_atomic_transfer import post
from .test_atomic_transfer import transfer_scope as transfer_scope  # noqa: F401
from .test_stock_receipt_concurrency import blocked_action


def receive(scope, key, quantity=Decimal("5")):
    return receive_stock(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=scope["actor"],
        quantity=quantity,
        reason="Synthetic receipt — ทดสอบ",
        request_id=key,
    )


def release(scope, key):
    return transition_lot_disposition(
        lot=scope["lot"],
        warehouse=scope["other"],
        actor=scope["actor"],
        expected_disposition="HOLD",
        target_disposition="RELEASED",
        reason="Synthetic Quality",
        request_id=key,
    )


@pytest.mark.django_db
def test_receipt_key_cannot_be_reused_by_transfer(transfer_scope):
    scope, key = transfer_scope, uuid4()
    receive(scope, key)
    before = StockTransfer.objects.count()
    with pytest.raises(TransferConflictError):
        post(scope, request_id=key)
    assert StockTransfer.objects.count() == before


@pytest.mark.django_db
def test_transfer_key_cannot_be_reused_by_receipt(transfer_scope):
    scope, key = transfer_scope, uuid4()
    post(scope, request_id=key)
    before = StockReceipt.objects.count()
    with pytest.raises(ReceiptConflictError):
        receive(scope, key)
    assert StockReceipt.objects.count() == before


@pytest.mark.django_db
def test_transfer_key_cannot_be_reused_by_quality_and_quality_key_by_transfer(transfer_scope):
    scope, key = transfer_scope, uuid4()
    post(scope, request_id=key)
    with pytest.raises(DispositionConflictError):
        release(scope, key)
    other = uuid4()
    release(scope, other)
    with pytest.raises(TransferConflictError):
        post(scope, request_id=other)


@pytest.mark.django_db
def test_receipt_key_cannot_be_reused_by_quality(transfer_scope):
    scope, key = transfer_scope, uuid4()
    receive(scope, key)
    with pytest.raises(DispositionConflictError):
        release(scope, key)


@pytest.mark.django_db
def test_database_rejects_cross_command_insert_bypassing_services(transfer_scope):
    """The registry is enforced by PostgreSQL triggers, not only by service code."""
    scope, key = transfer_scope, uuid4()
    post(scope, request_id=key)
    entry = scope["lot"].stockledgerentry_set.first()
    with pytest.raises(IntegrityError, match="request"), transaction.atomic():
        StockReceipt.objects.create(request_id=key, ledger_entry=entry)


@pytest.mark.django_db
def test_failed_cross_command_attempt_leaves_no_ledger_rows(transfer_scope):
    scope, key = transfer_scope, uuid4()
    receive(scope, key)
    ledger_before = scope["lot"].stockledgerentry_set.count()
    with pytest.raises(TransferConflictError):
        post(scope, request_id=key)
    assert scope["lot"].stockledgerentry_set.count() == ledger_before


@pytest.mark.django_db(transaction=True)
def test_cross_command_race_on_registry_leaves_only_the_winner(transfer_scope):
    scope, key = transfer_scope, uuid4()
    receipt, outcome = blocked_action(
        lambda: receive(scope, key),
        lambda: post(scope, request_id=key)[0],
    )
    assert outcome[0] == "TransferConflictError", outcome
    assert StockReceipt.objects.filter(request_id=key).count() == 1
    assert StockTransfer.objects.filter(request_id=key).count() == 0
    assert receipt.pk is not None
    assert StockLedgerEntry.objects.filter(warehouse=scope["other"]).count() == 0
