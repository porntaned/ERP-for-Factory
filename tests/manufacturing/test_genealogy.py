"""M5.3 (Issue #78): which input Lots went into an output Lot, and where an input Lot went.

Genealogy is read from immutable M5.2 records: output Lot -> order (OUTPUT) -> consumed Lots
(CONSUME). Returned and scrapped material is not part of the output.
"""

from decimal import Decimal

import pytest

from inventory.models import Lot
from manufacturing.genealogy import inputs_of, outputs_of

from .test_material_movements import give_back, issue, order, plant, stock  # noqa: F401
from .test_production_postings import consume, output, scrap

D = Decimal


@pytest.fixture
def made(plant):  # noqa: F811 (fixture imported from test_material_movements)
    """Order 1 consumes 25 of L1 and 15 of L2, scraps 0, returns nothing else, outputs LAMP-1."""
    from access_control.models import WarehouseRoleAssignment

    WarehouseRoleAssignment.objects.create(
        user=plant.users["approver2"], warehouse=plant.wh["LINE-1"], role="APPROVER"
    )
    plant.lot2 = stock(plant, "L2", D("50"))
    issue(plant, "25")
    issue(plant, "15", lot=plant.lot2)
    consume(plant, "24")
    scrap(plant, "1")
    consume(plant, "10", lot=plant.lot2)
    give_back(plant, "5", lot=plant.lot2)
    output(plant, "9", code="LAMP-1")
    return plant


def rows(result):
    return {(r.order.pk, r.lot.code): r.quantity for r in result}


@pytest.mark.django_db
def test_inputs_of_an_output_lot_count_consumption_only(made):
    lamp = Lot.objects.get(code="LAMP-1")
    assert rows(inputs_of(lamp)) == {
        (made.order.pk, "L1"): D("24"),
        (made.order.pk, "L2"): D("10"),
    }


@pytest.mark.django_db
def test_outputs_of_an_input_lot(made):
    second = order(made)
    issue(made, "10", target=second)
    consume(made, "10", target=second)
    output(made, "2", code="LAMP-2", target=second)
    result = outputs_of(made.lot)
    assert rows(result) == {(made.order.pk, "LAMP-1"): D("9"), (second.pk, "LAMP-2"): D("2")}
    assert {r.consumed for r in result} == {D("24"), D("10")}
    assert rows(outputs_of(made.lot2)) == {(made.order.pk, "LAMP-1"): D("9")}


@pytest.mark.django_db
def test_lots_without_production_history_have_no_genealogy(made):
    fresh = stock(made, "L7", D("5"))
    assert inputs_of(fresh) == [] and outputs_of(fresh) == []
    assert outputs_of(Lot.objects.get(code="LAMP-1")) == []


@pytest.mark.django_db
def test_genealogy_rejects_unsaved_lot(made):
    with pytest.raises(ValueError):
        inputs_of(Lot(item=made.items["lamp"], code="NEW"))
