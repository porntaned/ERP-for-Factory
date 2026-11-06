# ruff: noqa: F811, F401 (fixtures imported from sibling test modules)
"""M6.2 (Issue #103): a REJECTED Lot is unusable at every warehouse; it may still be scrapped.

Owner rulings (2026-11-06): while a Lot is REJECTED at ANY warehouse, transfer (either side), issue,
return, CONSUME, receipt, OUTPUT and the reversal of a transfer, CONSUME or SCRAP are refused;
SCRAP and the reversal of a receipt or an OUTPUT, which only take stock out, stay allowed. An exact
replay of an earlier command still returns its history. Fixtures are the M5.2 production line.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from inventory.lot_gate import LotRejectedError
from inventory.models import StockLedgerEntry
from inventory.production import (
    post_production_posting,
    reverse_production_posting,
)
from inventory.reversals import reverse_receipt, reverse_transfer
from inventory.services import receive_stock
from inventory.transfer_policy import TransferQualityError
from inventory.transfers import post_production_transfer, transfer_stock
from manufacturing.services import (
    MaterialQualityError,
    close_production_order,
    consume_material,
)
from quality.services import (
    get_lot_disposition,
    return_rejected_to_hold,
    transition_lot_disposition,
)
from tests.manufacturing.conftest import mf  # noqa: F401
from tests.manufacturing.test_material_movements import (
    balance,
    give_back,
    issue,
    order,
    plant,
    stock,
)  # noqa: F401
from tests.manufacturing.test_production_postings import SHORT, close, consume, line, output, scrap  # noqa: F401
from tests.manufacturing.test_production_reversal import release as release_pair
from tests.manufacturing.test_production_reversal import reverse
from tests.quality.helpers import force_reject
from tests.quality.helpers import release as inspect_release

D = Decimal


def reject(mf, code, lot=None):
    """Make the Lot REJECTED at one warehouse (a RELEASED pair first goes back to HOLD)."""
    lot = lot or mf.lot
    warehouse = mf.wh[code]
    if get_lot_disposition(lot=lot, warehouse=warehouse) == "RELEASED":
        transition_lot_disposition(
            lot=lot,
            warehouse=warehouse,
            actor=mf.qc,
            expected_disposition="RELEASED",
            target_disposition="HOLD",
            reason="Synthetic hold before rejection",
            request_id=uuid4(),
        )
    force_reject(lot, warehouse, mf.qc)


def unreject(mf, code, lot=None):
    return_rejected_to_hold(
        lot=lot or mf.lot,
        warehouse=mf.wh[code],
        actor=mf.users["approver" if code == "RM-A" else "approver2"],
        reason="Synthetic re-test",
        request_id=uuid4(),
    )


def entries():
    return StockLedgerEntry.objects.count()


def move(mf, source, destination, quantity="10", *, key=None, lot=None):
    return transfer_stock(
        lot=lot or mf.lot,
        source_warehouse=mf.wh[source],
        destination_warehouse=mf.wh[destination],
        actor=mf.staff,
        quantity=D(quantity),
        reason="Synthetic move",
        request_id=key or uuid4(),
    )


def receive(mf, quantity="5", *, key=None):
    return receive_stock(
        lot=mf.lot,
        warehouse=mf.wh["RM-A"],
        actor=mf.staff,
        quantity=D(quantity),
        reason="Synthetic receipt",
        request_id=key or uuid4(),
    )


# ---------------------------------------------------------------- transfer, three positions


@pytest.mark.django_db
@pytest.mark.parametrize(
    "where",
    [
        # At the source the per-warehouse RELEASED gate (unchanged by M6.2) refuses first.
        ("source", "RM-A", TransferQualityError),
        ("destination", "FG", LotRejectedError),
        ("other", "LINE-1", LotRejectedError),
    ],
    ids=lambda w: w[0],
)
def test_transfer_refused_when_the_lot_is_rejected_anywhere(line, where):
    reject(line, where[1])
    before = entries()
    with pytest.raises(where[2]):
        move(line, "RM-A", "FG")
    assert entries() == before


# ---------------------------------------------------------------- one case per command

REFUSED = {}
ALLOWED = {}


def refused(name):
    def register(fn):
        REFUSED[name] = fn
        return fn

    return register


def allowed(name):
    def register(fn):
        ALLOWED[name] = fn
        return fn

    return register


# Each case prepares what the command needs, then returns (exception, action, rejecting warehouse).
# The Lot is rejected AFTER the preparation, so only the command under test sees the rejection.


@refused("issue")
def _issue(mf):
    other = order(mf)  # the first order already holds its full BOM requirement
    return MaterialQualityError, lambda: issue(mf, "1", target=other), "FG"


@refused("return")
def _return(mf):
    return MaterialQualityError, lambda: give_back(mf, "1"), "FG"


@refused("consume")
def _consume(mf):
    return MaterialQualityError, lambda: consume(mf, "1"), "FG"


@refused("receipt")
def _receipt(mf):
    return LotRejectedError, lambda: receive(mf), "FG"


@refused("transfer")
def _transfer(mf):
    return LotRejectedError, lambda: move(mf, "RM-A", "FG"), "LINE-1"


@refused("output")
def _output(mf):
    link = output(mf, "1")
    lamp = link.posting.ledger_entry.lot
    mf.rejecting = lamp
    return MaterialQualityError, lambda: output(mf, "1"), "FG"


@refused("reversal of a transfer")
def _reverse_transfer(mf):
    done = move(mf, "RM-A", "FG")
    release_pair(mf, mf.lot, "FG")
    from access_control.models import WarehouseRoleAssignment

    WarehouseRoleAssignment.objects.create(
        user=mf.users["approver"], warehouse=mf.wh["FG"], role="APPROVER"
    )
    transfer = done[0].transfer_out
    return (
        LotRejectedError,
        lambda: reverse_transfer(
            transfer=transfer, actor=mf.users["approver"], reason="Error", request_id=uuid4()
        ),
        "LINE-1",
    )


@refused("reversal of a CONSUME")
def _reverse_consume(mf):
    link = consume(mf, "5")
    return MaterialQualityError, lambda: reverse(mf, link), "FG"


@refused("reversal of a SCRAP")
def _reverse_scrap(mf):
    link = scrap(mf, "2")
    return MaterialQualityError, lambda: reverse(mf, link), "FG"


@allowed("scrap")
def _scrap(mf):
    return lambda: scrap(mf, "2"), "FG"


@allowed("reversal of a receipt")
def _reverse_receipt(mf):
    receipt = receive(mf, "5")
    return (
        lambda: reverse_receipt(
            receipt=receipt, actor=mf.users["approver"], reason="Error", request_id=uuid4()
        ),
        "FG",
    )


@allowed("reversal of an OUTPUT")
def _reverse_output(mf):
    link = output(mf, "1")
    mf.rejecting = link.posting.ledger_entry.lot
    return lambda: reverse(mf, link), "FG"


@pytest.mark.django_db
@pytest.mark.parametrize("name", REFUSED)
def test_command_refused_while_the_lot_is_rejected_then_works_after_hold(line, name):
    error, act, where = REFUSED[name](line)
    reject(line, where, getattr(line, "rejecting", None))
    before = entries()
    with pytest.raises(error):
        act()
    assert entries() == before
    unreject(line, where, getattr(line, "rejecting", None))
    act()  # gated only by its old rules again
    assert entries() > before


@pytest.mark.django_db
@pytest.mark.parametrize("name", ALLOWED)
def test_command_that_only_takes_stock_out_still_works_while_rejected(line, name):
    act, where = ALLOWED[name](line)
    reject(line, where, getattr(line, "rejecting", None))
    before = entries()
    act()
    assert entries() == before + 1


@pytest.mark.django_db
def test_inventory_commands_raise_the_inventory_error(line):
    """Manufacturing maps the Inventory error; Inventory itself raises LotRejectedError."""
    link = consume(line, "5")
    scrapped = scrap(line, "2")
    output_link = output(line, "1")
    lamp = output_link.posting.ledger_entry.lot
    reject(line, "FG")
    reject(line, "FG", lamp)
    calls = [
        lambda: post_production_transfer(
            lot=line.lot,
            source_warehouse=line.wh["RM-A"],
            destination_warehouse=line.wh["LINE-1"],
            actor=line.users["production"],
            quantity=D("1"),
            reason="Issue",
            request_id=uuid4(),
            quality_at_source=True,
        ),
        lambda: post_production_posting(
            kind="CONSUME",
            lot=line.lot,
            warehouse=line.wh["LINE-1"],
            actor=line.users["production"],
            quantity=D("1"),
            reason="Consume",
            request_id=uuid4(),
        ),
        lambda: post_production_posting(
            kind="OUTPUT",
            lot=lamp,
            warehouse=line.wh["FG"],
            actor=line.users["production"],
            quantity=D("1"),
            reason="Output",
            request_id=uuid4(),
        ),
        lambda: reverse_production_posting(
            posting=link.posting, actor=line.users["approver2"], reason="r", request_id=uuid4()
        ),
        lambda: reverse_production_posting(
            posting=scrapped.posting, actor=line.users["approver2"], reason="r", request_id=uuid4()
        ),
    ]
    for call in calls:
        with pytest.raises(LotRejectedError):
            call()


# ---------------------------------------------------------------- replay and Quality elsewhere


@pytest.mark.django_db
def test_exact_replay_after_rejection_returns_history(line):
    key = uuid4()
    first = move(line, "RM-A", "FG", key=key)
    receipt_key = uuid4()
    receipt = receive(line, key=receipt_key)
    consume_key = uuid4()
    consumed = consume(line, "3", key=consume_key)
    reject(line, "LINE-1")
    before = entries()
    assert move(line, "RM-A", "FG", key=key) == first
    assert receive(line, key=receipt_key) == receipt
    assert (
        consume_material(
            order=line.order,
            lot=line.lot,
            quantity=D("3"),
            actor=line.users["production"],
            reason="Synthetic consumption",
            request_id=consume_key,
        )
        == consumed
    )
    assert entries() == before


@pytest.mark.django_db
def test_exact_replay_of_a_reversal_returns_history(line):
    link = consume(line, "5")
    key = uuid4()
    first = reverse(line, link, key=key)
    reject(line, "FG")
    before = entries()
    assert reverse(line, link, key=key) == first
    assert entries() == before


@pytest.mark.django_db
def test_rejected_lot_inspected_and_released_elsewhere_stays_unusable(line):
    """Q4: the inspection at B is recorded, but the Lot is unusable until A is no longer REJECTED."""
    move(line, "RM-A", "FG", "10")  # FG pair starts at HOLD, now with stock
    reject(line, "RM-A")
    inspect_release(line.lot, line.wh["FG"], line.qc, quantity=D("1"), note="Synthetic retest")
    assert get_lot_disposition(lot=line.lot, warehouse=line.wh["FG"]) == "RELEASED"
    before = entries()
    with pytest.raises(LotRejectedError):
        move(line, "FG", "LINE-1", "5")
    assert entries() == before
    unreject(line, "RM-A")
    move(line, "FG", "LINE-1", "5")  # usable again; FG stayed RELEASED


@pytest.mark.django_db
def test_order_is_frozen_for_a_lot_rejected_elsewhere_but_can_scrap_and_close(line):
    """Q3: nothing happens automatically; an APPROVER scraps the line empty, then the order closes."""
    reject(line, "RM-A")
    with pytest.raises(MaterialQualityError):
        consume(line, "5")
    with pytest.raises(MaterialQualityError):
        give_back(line, "5")
    assert balance(line, "LINE-1") == D("40")  # nothing moved on its own
    scrap(line, "40")
    assert balance(line, "LINE-1") == D("0")
    closed = close_production_order(
        order=line.order,
        actor=line.users["production"],
        request_id=uuid4(),
        shortfall_reason=SHORT,
    )
    assert closed.status == "CLOSED"
