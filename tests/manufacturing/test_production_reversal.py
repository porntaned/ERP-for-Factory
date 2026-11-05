"""M5.2c (Issue #81): reverse production postings; shortfall reason; holding messages.

Owner rules (2026-11-05): APPROVER at the posting's warehouse reverses a whole posting once,
with an opposite entry referencing the untouched original; only while the order is OPEN; an
OUTPUT only while every entry of its Lot is an OUTPUT posting or the reversal of one.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction

from inventory.models import (
    ProductionPosting,
    ProductionPostingReversal,
    RequestKey,
    StockLedgerEntry,
    StockReceipt,
)
from inventory.production import (
    AlreadyReversedError,
    OutputLotUsedError,
    PostingAuthorizationError,
    PostingConflictError,
    reverse_production_posting,
)
from inventory.transfers import transfer_stock
from quality.services import transition_lot_disposition

from .test_material_movements import balance, give_back, issue, order, plant, stock  # noqa: F401
from .test_production_postings import consume, line, output, scrap  # noqa: F401

D = Decimal


def reverse_posting(mf, link, *, actor="approver2", reason="Recorded in error", key=None):
    return reverse_production_posting(
        posting=link.posting,
        actor=mf.users[actor],
        reason=reason,
        request_id=key or uuid4(),
    )


def release(mf, lot, warehouse="FG"):
    transition_lot_disposition(
        lot=lot,
        warehouse=mf.wh[warehouse],
        actor=mf.qc,
        expected_disposition="HOLD",
        target_disposition="RELEASED",
        reason="Synthetic release",
        request_id=uuid4(),
    )


def move(mf, lot, source, destination, quantity):
    return transfer_stock(
        lot=lot,
        source_warehouse=mf.wh[source],
        destination_warehouse=mf.wh[destination],
        actor=mf.staff,
        quantity=D(quantity),
        reason="Synthetic move",
        request_id=uuid4(),
    )


def rejected(action):
    with pytest.raises(IntegrityError), transaction.atomic():
        action()


# ---------------------------------------------------------------- Inventory command


@pytest.mark.django_db
def test_inventory_reverses_each_kind_with_one_opposite_entry(line):
    used = consume(line, "30")
    reversal = reverse_posting(line, used)
    entry = reversal.ledger_entry
    assert (entry.lot, entry.warehouse.code, entry.quantity_delta) == (line.lot, "LINE-1", D("30"))
    assert (entry.actor, entry.reason) == (line.users["approver2"], "Recorded in error")
    used.posting.ledger_entry.refresh_from_db()
    assert used.posting.ledger_entry.quantity_delta == D("-30")
    assert ProductionPosting.objects.get(pk=used.posting.pk).reversal == reversal
    assert balance(line, "LINE-1") == D("40")

    made = output(line, "5")
    lamp = made.posting.ledger_entry.lot
    reversal = reverse_posting(line, made)
    assert (reversal.ledger_entry.warehouse.code, reversal.ledger_entry.quantity_delta) == (
        "FG",
        D("-5"),
    )
    assert balance(line, "FG", lot=lamp) == D("0")


@pytest.mark.django_db
def test_inventory_reversal_needs_approver_at_the_posting_warehouse(line):
    used = consume(line, "1")
    for actor in ("production", "approver"):  # PRODUCTION only / APPROVER elsewhere
        with pytest.raises(PostingAuthorizationError):
            reverse_posting(line, used, actor=actor)
    assert not ProductionPostingReversal.objects.exists()


@pytest.mark.django_db
def test_inventory_reversal_replay_conflict_and_once_only(line):
    used, other = consume(line, "1"), consume(line, "2")
    key = uuid4()
    first = reverse_posting(line, used, key=key)
    assert reverse_posting(line, used, key=key) == first
    with pytest.raises(PostingConflictError):
        reverse_posting(line, used, key=key, reason="Another reason")
    with pytest.raises(PostingConflictError):
        reverse_posting(line, other, key=key)
    with pytest.raises(AlreadyReversedError):
        reverse_posting(line, used)
    consume_key = uuid4()
    consume(line, "1", key=consume_key)
    with pytest.raises(PostingConflictError):
        reverse_posting(line, other, key=consume_key)
    assert RequestKey.objects.get(request_id=key).command == "POSTING_REV"
    assert ProductionPostingReversal.objects.count() == 1


@pytest.mark.django_db
def test_output_reversal_refused_after_the_lot_moved(line):
    made = output(line, "5")
    lamp = made.posting.ledger_entry.lot
    release(line, lamp)
    move(line, lamp, "FG", "RM-A", "1")
    release(line, lamp, "RM-A")
    move(line, lamp, "RM-A", "FG", "1")  # back again: history still blocks
    assert balance(line, "FG", lot=lamp) == D("5")
    with pytest.raises(OutputLotUsedError):
        reverse_posting(line, made)


@pytest.mark.django_db
def test_output_reversal_allowed_after_release(line):
    made = output(line, "5")
    release(line, made.posting.ledger_entry.lot)
    assert reverse_posting(line, made).ledger_entry.quantity_delta == D("-5")


# ---------------------------------------------------------------- Inventory database rules


def raw_reversal(link, *, quantity=None, lot=None, warehouse=None, entry=None):
    original = link.posting.ledger_entry
    if entry is None:
        entry = StockLedgerEntry.objects.create(
            lot=lot or original.lot,
            warehouse=warehouse or original.warehouse,
            actor=original.actor,
            reason="Raw reversal",
            quantity_delta=-original.quantity_delta if quantity is None else quantity,
        )
    return ProductionPostingReversal.objects.create(
        posting=link.posting, ledger_entry=entry, request_id=uuid4()
    )


@pytest.mark.django_db
def test_database_checks_reversal_links(line):
    used = consume(line, "3")
    other_lot = stock(line, "L7", D("5"))
    receipt_entry = StockReceipt.objects.first().ledger_entry
    rejected(lambda: raw_reversal(used, quantity=D("2")))
    rejected(lambda: raw_reversal(used, lot=other_lot))
    rejected(lambda: raw_reversal(used, warehouse=line.wh["RM-A"]))
    rejected(lambda: raw_reversal(used, entry=receipt_entry))
    rejected(lambda: raw_reversal(used, entry=consume(line, "3").posting.ledger_entry))

    reversal = raw_reversal(used)
    rejected(
        lambda: ProductionPostingReversal.objects.filter(pk=reversal.pk).update(request_id=uuid4())
    )
    rejected(lambda: ProductionPostingReversal.objects.filter(pk=reversal.pk).delete())
    entry = reversal.ledger_entry
    rejected(lambda: StockReceipt.objects.create(ledger_entry=entry, request_id=uuid4()))
    rejected(
        lambda: ProductionPosting.objects.create(
            kind="CONSUME", ledger_entry=entry, request_id=uuid4()
        )
    )
    rejected(lambda: raw_reversal(used))  # once only
    assert RequestKey.objects.get(request_id=reversal.request_id).command == "POSTING_REV"


@pytest.mark.django_db
def test_database_refuses_output_reversal_of_a_used_lot(line):
    made = output(line, "5")
    lamp = made.posting.ledger_entry.lot
    release(line, lamp)
    move(line, lamp, "FG", "RM-A", "1")
    rejected(lambda: raw_reversal(made, quantity=D("-5")))
