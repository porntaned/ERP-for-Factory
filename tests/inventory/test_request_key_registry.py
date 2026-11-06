"""M4.4.1: one request UUID belongs to exactly one command type across the system.

Same-command exact replay is covered elsewhere and must keep working. These tests cover
a UUID first used by one command and then offered to a different command.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from access_control.models import WarehouseRoleAssignment
from inventory.models import StockLedgerEntry, StockReceipt, StockTransfer
from inventory.services import ReceiptConflictError, get_stock_balance, receive_stock
from inventory.transfers import TransferConflictError
from quality.services import DispositionConflictError, record_inspection
from tests.quality.helpers import raw_inspection

from .test_atomic_transfer import change_quality, post
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
    """The Quality command under test is the inspection (M6.1): it carries a DISPOSITION key.
    An inspection needs stock at the pair, so an empty destination first receives 1."""
    if get_stock_balance(lot=scope["lot"], warehouse=scope["other"]) == 0:
        receive_stock(
            lot=scope["lot"],
            warehouse=scope["other"],
            actor=scope["actor"],
            quantity=Decimal("1"),
            reason="Synthetic stock to inspect",
            request_id=uuid4(),
        )
    return record_inspection(
        lot=scope["lot"],
        warehouse=scope["other"],
        result="PASS",
        sample_quantity=Decimal("1"),
        note="Synthetic Quality",
        actor=scope["actor"],
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
    entry = scope["lot"].stockledgerentry_set.order_by("id").first()
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


@pytest.mark.django_db
def test_quality_key_cannot_be_reused_by_receipt(transfer_scope):
    scope, key = transfer_scope, uuid4()
    release(scope, key)
    with pytest.raises(ReceiptConflictError):
        receive(scope, key)


@pytest.mark.django_db
def test_database_rejects_raw_disposition_insert_with_key_owned_by_receipt(transfer_scope):
    from quality.models import LotDispositionEvent

    scope, key = transfer_scope, uuid4()
    receive(scope, key)
    with pytest.raises(IntegrityError, match="request"), transaction.atomic():
        # M6.1: a valid event out of HOLD carries its inspection, so only the key is wrong.
        LotDispositionEvent.objects.create(
            lot=scope["lot"],
            warehouse=scope["other"],
            actor=scope["actor"],
            request_id=key,
            from_disposition="HOLD",
            to_disposition="RELEASED",
            reason="Synthetic raw insert",
            inspection=raw_inspection(scope["lot"], scope["other"], scope["actor"]),
        )


@pytest.mark.django_db
def test_new_transfer_without_request_id_is_rejected_by_postgresql(transfer_scope):
    """Legacy NULL keys stay as history; a NEW transfer row must carry a key (M4.4.2)."""
    from .test_transfer_history import entries

    debit, credit = entries(transfer_scope)
    with pytest.raises(IntegrityError, match="request_id"), transaction.atomic():
        StockTransfer.objects.create(source_entry=debit, destination_entry=credit)


def other_lot_scope(scope):
    """Second command on a DIFFERENT Lot by a DIFFERENT actor.

    Same Lot or same actor would make the second command wait on the Lot or User/grant
    lock and then fail at the service pre-check, never reaching the registry trigger.
    Here the only shared row is the registry key, so the race is decided by the trigger's
    unique-index wait and the services' IntegrityError branch.
    """
    actor = get_user_model().objects.create(username="registry-race-actor")
    for warehouse in (scope["warehouse"], scope["other"]):
        for role in ("WAREHOUSE", "QUALITY"):
            WarehouseRoleAssignment.objects.create(user=actor, warehouse=warehouse, role=role)
    second = scope | {"lot": scope["second"], "actor": actor}
    StockLedgerEntry.objects.create(
        lot=second["lot"],
        warehouse=second["warehouse"],
        actor=actor,
        quantity_delta=Decimal("100"),
        reason="Synthetic second-lot stock",
    )
    change_quality(second, second["warehouse"], "RELEASED")
    return second


COMMANDS = {
    "receipt": (lambda s, k: receive(s, k), "ReceiptConflictError"),
    "transfer": (lambda s, k: post(s, request_id=k)[0], "TransferConflictError"),
    "disposition": (lambda s, k: release(s, k), "InspectionConflictError"),
}


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "first,second",
    [
        ("receipt", "transfer"),
        ("transfer", "receipt"),
        ("disposition", "transfer"),
        ("receipt", "disposition"),
    ],
)
def test_cross_command_race_is_decided_at_the_registry(transfer_scope, first, second):
    scope, key = transfer_scope, uuid4()
    other = other_lot_scope(scope)
    ledger_other_before = StockLedgerEntry.objects.filter(lot=other["lot"]).count()
    run_first, _ = COMMANDS[first]
    run_second, expected = COMMANDS[second]
    _, outcome = blocked_action(lambda: run_first(scope, key), lambda: run_second(other, key))
    assert outcome[0] == expected, outcome
    # the losing command rolled back every row it wrote on its own Lot
    assert StockLedgerEntry.objects.filter(lot=other["lot"]).count() == ledger_other_before
    assert StockReceipt.objects.filter(request_id=key).count() == (first == "receipt")
    assert StockTransfer.objects.filter(request_id=key).count() == (first == "transfer")
