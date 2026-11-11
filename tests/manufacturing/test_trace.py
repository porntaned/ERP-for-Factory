"""M6.3 (Issue #108): trace a Lot through every production level.

`trace(lot, direction)` walks the M5.3 links level by level: backward to Lots no order produced,
forward to Lots no order consumed. It nets reversed postings exactly as inputs_of/outputs_of,
expands each Lot once (a repeat is listed but not expanded) and reads one batch per level.
Every chain here is built through the real commands.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from access_control.models import WarehouseRoleAssignment
from catalog.models import Item
from inventory.models import Lot
from manufacturing.genealogy import inputs_of, outputs_of, trace
from manufacturing.services import (
    approve_bom,
    create_bom_draft,
    create_production_order,
    reverse_order_posting,
)
from tests.quality.helpers import release as inspect_release

from .test_material_movements import issue, plant, stock  # noqa: F401
from .test_production_postings import consume, output

D = Decimal


def bom(mf, item, lines):
    """An ACTIVE BOM through the real commands; `item` and components are mf.items keys or Items."""
    get = lambda key: mf.items[key] if isinstance(key, str) else key  # noqa: E731
    draft = create_bom_draft(
        item=get(item),
        lines=[(get(component), D(quantity)) for component, quantity in lines],
        actor=mf.users["production"],
        request_id=uuid4(),
    )
    return approve_bom(bom=draft, actor=mf.users["approver"], request_id=uuid4())


def new_order(mf, active_bom, quantity):
    return create_production_order(
        bom=active_bom,
        quantity=D(quantity),
        line_warehouse=mf.wh["LINE-1"],
        output_warehouse=mf.wh["FG"],
        actor=mf.users["production"],
        request_id=uuid4(),
    )


def make(mf, code, quantity, *, target, release=True):
    """Record output `code` on `target`; release it at FG by a FINAL inspection that passes."""
    posting = output(mf, quantity, code=code, target=target)
    lot = Lot.objects.get(code=code)
    if release:
        inspect_release(lot, mf.wh["FG"], mf.qc, quantity=D("1"))
    return lot, posting


def reverse(mf, posting):
    return reverse_order_posting(
        order_posting=posting,
        actor=mf.users["approver2"],
        reason="Recorded in error",
        request_id=uuid4(),
    )


@pytest.fixture
def chain(plant):  # noqa: F811 (fixture imported from test_material_movements)
    """RAW -> WIP -> FINISHED.

    Order A: 5 BOARD (2 chips each) consumes 10 of L1, outputs BRD-1 5 at FG (FINAL PASS).
    Order B: 6 LAMP-B (1 BOARD + 1 DRIVER) consumes BRD-1 5 and D1 5 (a mistaken D1 2 is
    reversed in between), outputs LMP-1 5; LMP-X 1 is output and reversed (net zero).
    """
    WarehouseRoleAssignment.objects.create(
        user=plant.users["approver2"], warehouse=plant.wh["LINE-1"], role="APPROVER"
    )
    plant.a = new_order(plant, bom(plant, "board", [("chip", "2")]), "5")
    issue(plant, "10", target=plant.a)
    consume(plant, "10", target=plant.a)
    plant.brd, _ = make(plant, "BRD-1", "5", target=plant.a)

    plant.d1 = stock(plant, "D1", D("20"), item="driver")
    plant.b = new_order(plant, bom(plant, "lamp2", [("board", "1"), ("driver", "1")]), "6")
    issue(plant, "5", lot=plant.brd, source="FG", target=plant.b)
    issue(plant, "5", lot=plant.d1, target=plant.b)
    consume(plant, "5", lot=plant.brd, target=plant.b)
    consume(plant, "3", lot=plant.d1, target=plant.b)
    reverse(plant, consume(plant, "2", lot=plant.d1, target=plant.b))
    consume(plant, "2", lot=plant.d1, target=plant.b)
    plant.lmp, _ = make(plant, "LMP-1", "5", target=plant.b, release=False)
    plant.lmpx, wrong = make(plant, "LMP-X", "1", target=plant.b, release=False)
    reverse(plant, wrong)
    return plant


def flat(result):
    return [
        (e.level, e.from_lot.code, e.order.pk, e.to_lot.code, e.quantity, e.repeat)
        for e in result.edges
    ]


@pytest.mark.django_db
def test_backward_trace_reaches_every_material_lot_through_wip(chain):
    result = trace(chain.lmp, "backward")
    assert result.lot == chain.lmp
    assert flat(result) == [
        (1, "LMP-1", chain.b.pk, "BRD-1", D("5"), False),
        (1, "LMP-1", chain.b.pk, "D1", D("5"), False),  # 3 + 2 (a reversed 2 nets out)
        (2, "BRD-1", chain.a.pk, "L1", D("10"), False),
    ]
    assert [lot.code for lot in result.lots] == ["LMP-1", "BRD-1", "D1", "L1"]


@pytest.mark.django_db
def test_forward_trace_reaches_every_finished_lot_through_wip(chain):
    result = trace(chain.lot, "forward")
    assert flat(result) == [
        (1, "L1", chain.a.pk, "BRD-1", D("5"), False),
        (2, "BRD-1", chain.b.pk, "LMP-1", D("5"), False),  # LMP-X nets to zero: not listed
    ]
    assert [e.consumed for e in result.edges] == [D("10"), D("5")]
    assert [lot.code for lot in result.lots] == ["L1", "BRD-1", "LMP-1"]


@pytest.mark.django_db
def test_level_one_equals_the_one_level_genealogy(chain):
    """Same netting as M5.3: reversed postings and zero nets are excluded the same way."""

    def level_one(lot, direction):
        return {
            (e.order.pk, e.to_lot.pk, e.quantity, e.consumed)
            for e in trace(lot, direction).edges
            if e.level == 1
        }

    for lot in (chain.lmp, chain.lmpx, chain.brd, chain.d1, chain.lot):
        assert level_one(lot, "backward") == {
            (link.order.pk, link.lot.pk, link.quantity, None) for link in inputs_of(lot)
        }
        assert level_one(lot, "forward") == {
            (link.order.pk, link.lot.pk, link.quantity, link.consumed) for link in outputs_of(lot)
        }
    assert trace(chain.lmpx, "backward").edges == []  # its output was reversed: from nothing


@pytest.mark.django_db
def test_one_lot_feeding_two_orders_and_one_order_with_two_outputs(chain):
    second = new_order(chain, chain.a.bom, "5")
    issue(chain, "6", target=second)
    consume(chain, "6", target=second)
    make(chain, "BRD-2", "2", target=second, release=False)
    make(chain, "BRD-3", "1", target=second, release=False)
    assert flat(trace(chain.lot, "forward"))[:3] == [
        (1, "L1", chain.a.pk, "BRD-1", D("5"), False),
        (1, "L1", second.pk, "BRD-2", D("2"), False),
        (1, "L1", second.pk, "BRD-3", D("1"), False),
    ]
    for code in ("BRD-2", "BRD-3"):  # order granularity: each output lists all the order used
        assert flat(trace(Lot.objects.get(code=code), "backward")) == [
            (1, code, second.pk, "L1", D("6"), False)
        ]


@pytest.mark.django_db
def test_a_diamond_expands_each_lot_once(plant):  # noqa: F811
    board = bom(plant, "board", [("chip", "2")])
    left, right = new_order(plant, board, "5"), new_order(plant, board, "5")
    for target, code in ((left, "W1"), (right, "W2")):
        issue(plant, "4", target=target)
        consume(plant, "4", target=target)
        make(plant, code, "2", target=target)
    joined = new_order(plant, bom(plant, "lamp2", [("board", "1")]), "4")
    for code in ("W1", "W2"):
        wip = Lot.objects.get(code=code)
        issue(plant, "2", lot=wip, source="FG", target=joined)
        consume(plant, "2", lot=wip, target=joined)
    make(plant, "F1", "4", target=joined, release=False)

    assert flat(trace(plant.lot, "forward")) == [
        (1, "L1", left.pk, "W1", D("2"), False),
        (1, "L1", right.pk, "W2", D("2"), False),
        (2, "W1", joined.pk, "F1", D("4"), False),
        (2, "W2", joined.pk, "F1", D("4"), True),  # listed, not expanded again
    ]
    backward = trace(Lot.objects.get(code="F1"), "backward")
    assert flat(backward) == [
        (1, "F1", joined.pk, "W1", D("2"), False),
        (1, "F1", joined.pk, "W2", D("2"), False),
        (2, "W1", left.pk, "L1", D("4"), False),
        (2, "W2", right.pk, "L1", D("4"), True),
    ]
    assert [lot.code for lot in backward.lots] == ["F1", "W1", "W2", "L1"]


@pytest.mark.django_db
def test_a_cycle_is_listed_once_and_the_walk_ends(plant):  # noqa: F811
    """An open order consumes a Lot made downstream of its own output (real commands).

    Order A (BOARD = 1 chip + 1 BOARD2) outputs W; order B (BOARD2 = 1 BOARD) turns W into Y;
    order A, still open, then consumes Y. W -> Y -> W is a cycle.
    """
    board2 = Item.objects.create(
        organization=plant.org,
        code="BOARD2",
        display_name="Synthetic sub-board",
        item_type="WIP",
        base_uom=plant.items["chip"].base_uom,
    )
    a = new_order(plant, bom(plant, "board", [("chip", "1"), (board2, "1")]), "5")
    issue(plant, "2", target=a)
    consume(plant, "2", target=a)
    w, _ = make(plant, "W", "2", target=a)
    b = new_order(plant, bom(plant, board2, [("board", "1")]), "5")
    issue(plant, "2", lot=w, source="FG", target=b)
    consume(plant, "2", lot=w, target=b)
    y, _ = make(plant, "Y", "2", target=b)
    issue(plant, "1", lot=y, source="FG", target=a)
    consume(plant, "1", lot=y, target=a)

    assert flat(trace(w, "forward")) == [
        (1, "W", b.pk, "Y", D("2"), False),
        (2, "Y", a.pk, "W", D("2"), True),
    ]
    assert flat(trace(w, "backward")) == [
        (1, "W", a.pk, "L1", D("2"), False),
        (1, "W", a.pk, "Y", D("1"), False),
        (2, "Y", b.pk, "W", D("2"), True),
    ]


@pytest.mark.django_db
def test_a_lot_without_production_history_has_an_empty_trace(chain):
    fresh = stock(chain, "L7", D("5"))
    for direction in ("backward", "forward"):
        result = trace(fresh, direction)
        assert (result.edges, result.lots) == ([], [fresh])
    assert trace(chain.lmp, "forward").edges == []  # nothing consumed the finished Lot
    assert trace(chain.lot, "backward").edges == []  # received material: no order produced it


@pytest.mark.django_db
def test_trace_refuses_an_unsaved_lot_and_an_unknown_direction(chain):
    with pytest.raises(ValueError):
        trace(Lot(item=chain.items["lamp"], code="NEW"), "backward")
    with pytest.raises(ValueError):
        trace(chain.lot, "sideways")


@pytest.mark.django_db
def test_queries_grow_with_levels_not_lots(chain, django_assert_max_num_queries):
    """Two levels each way: 1 query loads the start Lot, at most 4 per expanded level, and 1
    finds that the last frontier expands no further."""
    for lot, direction in ((chain.lmp, "backward"), (chain.lot, "forward")):
        with django_assert_max_num_queries(1 + 4 * 2 + 1):
            result = trace(lot, direction)
            [(e.order.pk, e.from_lot.item.code, e.to_lot.item.code) for e in result.edges]
    # Wider levels (more Lots and orders per level) cost the same number of queries.
    for n in range(2, 5):
        extra = new_order(chain, chain.a.bom, "1")
        issue(chain, "2", target=extra)
        consume(chain, "2", target=extra)
        make(chain, f"BRD-{n}", "1", target=extra, release=False)
    with django_assert_max_num_queries(1 + 4 * 2 + 1):
        result = trace(chain.lot, "forward")
        [(e.order.pk, e.to_lot.item.code) for e in result.edges]
    assert len([e for e in result.edges if e.level == 1]) == 4
