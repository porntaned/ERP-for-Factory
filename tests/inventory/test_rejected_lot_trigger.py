# ruff: noqa: F811, F401 (fixtures imported from sibling test modules)
"""M6.2 (Issue #103): PostgreSQL refuses stock entries for a REJECTED Lot, checked at commit.

Direct writes, not the commands. While a Lot is REJECTED at any warehouse, a new ledger entry is
accepted only as a debit linked as a SCRAP, the debit of a receipt reversal, or the entry of an
OUTPUT reversal. The check is deferred because the entry is inserted before the row that links it;
the setup here writes history first (earlier transactions), then rejects, then writes the entries
under test in one transaction that commits.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from access_control.models import WarehouseRoleAssignment
from inventory.lot_gate import LotRejectedError
from inventory.models import (
    Lot,
    ProductionPosting,
    ProductionPostingReversal,
    StockLedgerEntry,
    StockReceipt,
    StockReversal,
    StockTransfer,
)
from inventory.transfers import transfer_stock
from quality.models import LotDispositionEvent
from quality.services import get_rejected_warehouses, record_inspection
from tests.manufacturing.conftest import mf  # noqa: F401
from tests.manufacturing.test_material_movements import order, plant, stock  # noqa: F401
from tests.manufacturing.test_production_postings import consume, line, output, scrap  # noqa: F401
from tests.quality.helpers import force_reject, give_origin

D = Decimal


def entry(mf, lot, code, delta):
    return StockLedgerEntry.objects.create(
        lot=lot,
        warehouse=mf.wh[code],
        actor=mf.qc,
        quantity_delta=D(delta),
        reason="Synthetic trigger entry",
    )


# `line` is the M5.2 production line: Lot L1 has 60 at RM-A (RELEASED) and 40 on LINE-1, and its
# history is committed before a test rejects the Lot. Each case returns (lot, act); `act` writes
# the entries under test inside ONE transaction. Cases in ALLOWED must pass while the Lot is
# REJECTED. Reversal cases get their original through the real commands, then write the
# reversal rows directly, so PostgreSQL's older rules (open order, exact offset) still apply.

CASES = {}
ALLOWED = set()


def case(name, allowed=False):
    def register(fn):
        CASES[name] = fn
        if allowed:
            ALLOWED.add(name)
        return fn

    return register


def atomic(write):
    def act():
        with transaction.atomic():
            write()

    return act


def posted(kind, mf, code, delta):
    return lambda: ProductionPosting.objects.create(
        kind=kind, ledger_entry=entry(mf, mf.lot, code, delta), request_id=uuid4()
    )


def raw_transfer(mf, source, destination):
    def write():
        debit = entry(mf, mf.lot, source, "-1")
        credit = entry(mf, mf.lot, destination, "1")
        StockTransfer.objects.create(
            source_entry=debit, destination_entry=credit, request_id=uuid4()
        )

    return atomic(write)


def raw_posting_reversal(mf, link):
    original = link.posting
    offset = original.ledger_entry

    def write():
        ProductionPostingReversal.objects.create(
            posting=original,
            ledger_entry=entry(mf, offset.lot, offset.warehouse.code, -offset.quantity_delta),
            request_id=uuid4(),
        )

    return atomic(write)


@case("credit with no link")
def _credit(mf):
    return mf.lot, atomic(lambda: entry(mf, mf.lot, "RM-A", "1"))


@case("debit with no link")
def _debit(mf):
    return mf.lot, atomic(lambda: entry(mf, mf.lot, "RM-A", "-1"))


@case("receipt")
def _receipt(mf):
    return mf.lot, atomic(
        lambda: StockReceipt.objects.create(
            request_id=uuid4(), ledger_entry=entry(mf, mf.lot, "RM-A", "1")
        )
    )


@case("transfer")
def _transfer(mf):
    return mf.lot, raw_transfer(mf, "RM-A", "FG")


@case("issue")
def _issue(mf):
    return mf.lot, raw_transfer(mf, "RM-A", "LINE-1")


@case("return")
def _return(mf):
    return mf.lot, raw_transfer(mf, "LINE-1", "RM-A")


@case("CONSUME")
def _consume(mf):
    return mf.lot, atomic(posted("CONSUME", mf, "LINE-1", "-1"))


@case("OUTPUT")
def _output(mf):
    return mf.lot, atomic(posted("OUTPUT", mf, "FG", "1"))


@case("reversal of a CONSUME")
def _reverse_consume(mf):
    return mf.lot, raw_posting_reversal(mf, consume(mf, "5"))


@case("reversal of a SCRAP")
def _reverse_scrap(mf):
    return mf.lot, raw_posting_reversal(mf, scrap(mf, "2"))


@case("reversal of a transfer")
def _reverse_transfer(mf):
    with transaction.atomic():
        original = StockTransfer.objects.create(
            source_entry=entry(mf, mf.lot, "RM-A", "-4"),
            destination_entry=entry(mf, mf.lot, "FG", "4"),
            request_id=uuid4(),
        )

    def write():
        StockReversal.objects.create(
            request_id=uuid4(),
            transfer=original,
            debit_entry=entry(mf, mf.lot, "FG", "-4"),
            credit_entry=entry(mf, mf.lot, "RM-A", "4"),
        )

    return mf.lot, atomic(write)


@case("SCRAP", allowed=True)
def _scrap(mf):
    return mf.lot, atomic(posted("SCRAP", mf, "LINE-1", "-1"))


@case("reversal of a receipt", allowed=True)
def _reverse_receipt(mf):
    with transaction.atomic():
        original = StockReceipt.objects.create(
            request_id=uuid4(), ledger_entry=entry(mf, mf.lot, "RM-A", "5")
        )
    return mf.lot, atomic(
        lambda: StockReversal.objects.create(
            request_id=uuid4(), receipt=original, debit_entry=entry(mf, mf.lot, "RM-A", "-5")
        )
    )


@case("reversal of an OUTPUT", allowed=True)
def _reverse_output(mf):
    link = output(mf, "3")
    mf.lot = link.posting.ledger_entry.lot  # the Lot that is rejected is the output Lot
    return mf.lot, raw_posting_reversal(mf, link)


def reject(mf, lot):
    """REJECT the Lot at FG; that pair has no event yet, so it is HOLD."""
    force_reject(lot, mf.wh["FG"], mf.qc)
    assert [w.code for w in get_rejected_warehouses(lot=lot)] == ["FG"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("name", [n for n in CASES if n not in ALLOWED])
def test_entries_for_a_rejected_lot_fail_at_commit(line, name):
    lot, act = CASES[name](line)
    reject(line, lot)
    before = StockLedgerEntry.objects.count()
    with pytest.raises(IntegrityError, match="REJECTED"):
        act()
    assert StockLedgerEntry.objects.count() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("name", sorted(ALLOWED))
def test_debits_that_only_take_stock_out_pass_while_rejected(line, name):
    lot, act = CASES[name](line)
    reject(line, lot)
    before = StockLedgerEntry.objects.count()
    act()
    assert StockLedgerEntry.objects.count() > before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("name", list(CASES))
def test_the_same_entries_pass_when_the_lot_is_not_rejected(line, name):
    lot, act = CASES[name](line)
    before = StockLedgerEntry.objects.count()
    act()
    assert StockLedgerEntry.objects.count() > before


@pytest.mark.django_db(transaction=True)
def test_a_lot_returned_to_hold_accepts_entries_again(line):
    from quality.services import return_rejected_to_hold

    lot, act = CASES["credit with no link"](line)
    reject(line, lot)
    return_rejected_to_hold(
        lot=lot,
        warehouse=line.wh["FG"],
        actor=line.users["approver2"],
        reason="Re-test",
        request_id=uuid4(),
    )
    act()


@pytest.mark.django_db(transaction=True)
def test_an_unlinked_entry_cannot_commit_on_its_own(line):
    """The link must be in the same transaction: in autocommit no link can follow."""
    lot, _ = CASES["debit with no link"](line)
    reject(line, lot)
    with pytest.raises(IntegrityError, match="REJECTED"):
        entry(line, lot, "LINE-1", "-1")


# ---------------------------------------------------------------- two connections


@pytest.fixture
def race(line):
    """10 of L1 moved to FG first: that pair is HOLD with stock, so it can be inspected there."""
    transfer_stock(
        lot=line.lot,
        source_warehouse=line.wh["RM-A"],
        destination_warehouse=line.wh["FG"],
        actor=line.staff,
        quantity=D("10"),
        reason="Synthetic move to FG",
        request_id=uuid4(),
    )
    return line


def inspection_fail(line, lot):
    return record_inspection(
        lot=lot,
        warehouse=line.wh["FG"],
        result="FAIL",
        sample_quantity=D("1"),
        note="Synthetic race inspection",
        actor=line.qc,
        request_id=uuid4(),
    )


def move_out(line, lot):
    return transfer_stock(
        lot=lot,
        source_warehouse=line.wh["RM-A"],
        destination_warehouse=line.wh["LINE-1"],
        actor=line.staff,
        quantity=D("1"),
        reason="Synthetic race move",
        request_id=uuid4(),
    )


@pytest.mark.django_db(transaction=True)
def test_movement_that_holds_the_lot_lock_first_commits_and_the_rejection_follows(race):
    line = race
    from tests.inventory.test_stock_receipt_concurrency import blocked_action

    lot = line.lot
    before = StockTransfer.objects.count()
    moved, outcome = blocked_action(
        lambda: move_out(line, lot)[0], lambda: inspection_fail(line, lot)
    )
    assert outcome[0] == "committed", outcome
    assert [w.code for w in get_rejected_warehouses(lot=lot)] == ["FG"]
    # one outcome: the movement committed first, then the rejection; the reverse order is the
    # next test, where the movement is refused
    assert StockTransfer.objects.count() == before + 1


@pytest.mark.django_db(transaction=True)
def test_rejection_that_holds_the_lot_lock_first_refuses_the_waiting_movement(race):
    line = race
    from tests.inventory.test_stock_receipt_concurrency import blocked_action

    lot = line.lot
    before = StockLedgerEntry.objects.count()
    _, outcome = blocked_action(lambda: inspection_fail(line, lot), lambda: move_out(line, lot)[0])
    assert outcome[0] == "LotRejectedError", outcome
    assert StockLedgerEntry.objects.count() == before


@pytest.mark.django_db(transaction=True)
def test_direct_insert_waiting_on_a_rejection_fails_at_its_commit(race):
    line = race
    from tests.inventory.test_stock_receipt_concurrency import blocked_action

    lot = line.lot
    before = StockLedgerEntry.objects.count()
    _, outcome = blocked_action(
        lambda: inspection_fail(line, lot), lambda: entry(line, lot, "RM-A", "-1")
    )
    assert outcome[0] == "IntegrityError" and "REJECTED" in outcome[1], outcome
    assert StockLedgerEntry.objects.count() == before


# ---------------------------------------------------------------- migration


def trigger_names():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT tgname FROM pg_trigger WHERE tgrelid = 'inventory_stockledgerentry'::regclass"
        )
        return {row[0] for row in cursor.fetchall()}


@pytest.mark.django_db(transaction=True)
def test_migration_unapplies_and_reapplies():
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    assert "inventory_ledger_rejected_lot_guard" in trigger_names()
    try:
        MigrationExecutor(connection).migrate(
            [("inventory", "0014_production_posting_reversal_rules")]
        )
        assert "inventory_ledger_rejected_lot_guard" not in trigger_names()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_proc WHERE proname = 'inventory_guard_rejected_lot'")
            assert cursor.fetchone() is None
    finally:
        MigrationExecutor(connection).migrate(latest)
    assert "inventory_ledger_rejected_lot_guard" in trigger_names()
