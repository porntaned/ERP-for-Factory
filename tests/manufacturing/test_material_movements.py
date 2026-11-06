"""M5.2a (Issue #72): issue material RM -> LINE-1 and return it, for one production order.

Owner rules: net issue (issued - returned) per component never exceeds order quantity x
quantity_per; the source must be RELEASED; movements go through Inventory and keep history.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction

from access_control.models import WarehouseRoleAssignment
from inventory.models import Lot, StockTransfer
from inventory.services import get_stock_balance, receive_stock
from inventory.transfers import TransferAuthorizationError, transfer_stock
from manufacturing.models import ProductionMaterialMovement
from manufacturing.services import (
    MaterialAuthorizationError,
    MaterialConflictError,
    MaterialLimitError,
    MaterialQualityError,
    MaterialValidationError,
    OrderValidationError,
    approve_bom,
    cancel_production_order,
    create_bom_draft,
    create_production_order,
    issue_material,
    return_material,
)
from tests.inventory.test_stock_receipt_concurrency import blocked_action
from tests.quality.helpers import release as inspect_release

D = Decimal


@pytest.fixture
def plant(mf):
    """10 lamps of 4 chips each: requirement 40 chips. Chip lot L1 has 100 RELEASED at RM-A."""
    staff = get_user_model().objects.create(username="mf-stores")
    qc = get_user_model().objects.create(username="mf-qc")
    for code in ("RM-A", "LINE-1", "FG"):
        WarehouseRoleAssignment.objects.create(user=staff, warehouse=mf.wh[code], role="WAREHOUSE")
        WarehouseRoleAssignment.objects.create(user=qc, warehouse=mf.wh[code], role="QUALITY")
    mf.staff, mf.qc = staff, qc
    mf.lot = stock(mf, "L1", D("100"))
    bom = create_bom_draft(
        item=mf.items["lamp"],
        lines=[(mf.items["chip"], D("4"))],
        actor=mf.users["production"],
        request_id=uuid4(),
    )
    mf.bom = approve_bom(bom=bom, actor=mf.users["approver"], request_id=uuid4())
    mf.order = order(mf)
    return mf


def stock(mf, code, quantity, *, item="chip", warehouse="RM-A", release=True):
    lot = Lot.objects.create(item=mf.items[item], code=code)
    receive_stock(
        lot=lot,
        warehouse=mf.wh[warehouse],
        actor=mf.staff,
        quantity=quantity,
        reason="Synthetic receipt",
        request_id=uuid4(),
    )
    if release:  # M6.1: release by an INCOMING inspection that passes
        inspect_release(
            lot, mf.wh[warehouse], mf.qc, quantity=Decimal("1"), note="Synthetic release"
        )
    return lot


def order(mf, quantity=D("10")):
    return create_production_order(
        bom=mf.bom,
        quantity=quantity,
        line_warehouse=mf.wh["LINE-1"],
        output_warehouse=mf.wh["FG"],
        actor=mf.users["production"],
        request_id=uuid4(),
    )


def issue(mf, quantity, *, lot=None, source="RM-A", target=None, actor="production", key=None):
    return issue_material(
        order=target or mf.order,
        lot=lot or mf.lot,
        source_warehouse=mf.wh[source],
        quantity=D(quantity),
        actor=mf.users[actor] if isinstance(actor, str) else actor,
        reason="Synthetic issue",
        request_id=key or uuid4(),
    )


def give_back(mf, quantity, *, lot=None, destination="RM-A", target=None, key=None):
    return return_material(
        order=target or mf.order,
        lot=lot or mf.lot,
        destination_warehouse=mf.wh[destination],
        quantity=D(quantity),
        actor=mf.users["production"],
        reason="Synthetic return",
        request_id=key or uuid4(),
    )


def balance(mf, code, lot=None):
    return get_stock_balance(lot=lot or mf.lot, warehouse=mf.wh[code])


# ---------------------------------------------------------------- issue


@pytest.mark.django_db
def test_issue_moves_stock_through_inventory_and_records_movement(plant):
    movement = issue(plant, "40")
    assert (balance(plant, "RM-A"), balance(plant, "LINE-1")) == (D("60"), D("40"))
    assert (movement.kind, movement.order, movement.lot, movement.quantity) == (
        "ISSUE",
        plant.order,
        plant.lot,
        D("40"),
    )
    entries = (movement.transfer.source_entry, movement.transfer.destination_entry)
    assert [e.warehouse.code for e in entries] == ["RM-A", "LINE-1"]
    assert entries[0].actor == plant.users["production"]


@pytest.mark.django_db
def test_issue_cannot_exceed_bom_requirement(plant):
    issue(plant, "30")
    with pytest.raises(MaterialLimitError):
        issue(plant, "10.000001")
    issue(plant, "10")  # exactly 40 is allowed
    with pytest.raises(MaterialLimitError):
        issue(plant, "0.000001")
    assert balance(plant, "LINE-1") == D("40")


@pytest.mark.django_db
def test_issue_cap_counts_every_lot_of_the_component(plant):
    second = stock(plant, "L2", D("50"))
    issue(plant, "25")
    with pytest.raises(MaterialLimitError):
        issue(plant, "16", lot=second)
    issue(plant, "15", lot=second)


@pytest.mark.django_db
def test_issue_rejects_component_not_in_bom(plant):
    driver = stock(plant, "D1", D("10"), item="driver")
    with pytest.raises(MaterialValidationError, match="BOM"):
        issue(plant, "1", lot=driver)


@pytest.mark.django_db
def test_issue_requires_released_source(plant):
    held = stock(plant, "L3", D("50"), release=False)
    with pytest.raises(MaterialQualityError):
        issue(plant, "1", lot=held)
    assert not ProductionMaterialMovement.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("who", ["approver2", "outsider", "staff"])
def test_issue_requires_production_at_both_warehouses(plant, who):
    actor = plant.staff if who == "staff" else plant.users[who]
    with pytest.raises(MaterialAuthorizationError):
        issue(plant, "1", actor=actor)
    assert balance(plant, "RM-A") == D("100")


@pytest.mark.django_db
def test_issue_source_must_not_be_the_line(plant):
    with pytest.raises(MaterialValidationError):
        issue(plant, "1", source="LINE-1")


@pytest.mark.django_db
def test_issue_requires_open_order(plant):
    cancel_production_order(
        order=plant.order, actor=plant.users["production"], reason="Stop", request_id=uuid4()
    )
    with pytest.raises(MaterialValidationError, match="OPEN"):
        issue(plant, "1")


@pytest.mark.django_db
def test_issue_replay_and_conflict(plant):
    key = uuid4()
    first = issue(plant, "5", key=key)
    assert issue(plant, "5", key=key) == first
    assert balance(plant, "LINE-1") == D("5")
    with pytest.raises(MaterialConflictError):
        issue(plant, "6", key=key)
    other = order(plant)
    with pytest.raises(MaterialConflictError):
        issue(plant, "5", key=key, target=other)


@pytest.mark.django_db
def test_plain_transfer_key_is_not_adopted(plant):
    key = uuid4()
    transfer_stock(
        lot=plant.lot,
        source_warehouse=plant.wh["RM-A"],
        destination_warehouse=plant.wh["LINE-1"],
        actor=plant.staff,
        quantity=D("5"),
        reason="Synthetic issue",
        request_id=key,
    )
    with pytest.raises(MaterialConflictError):
        issue(plant, "5", key=key)
    assert not ProductionMaterialMovement.objects.exists()


@pytest.mark.django_db
def test_transfer_stock_still_requires_warehouse_role(plant):
    with pytest.raises(TransferAuthorizationError):
        transfer_stock(
            lot=plant.lot,
            source_warehouse=plant.wh["RM-A"],
            destination_warehouse=plant.wh["LINE-1"],
            actor=plant.users["production"],
            quantity=D("1"),
            reason="Not through an order",
            request_id=uuid4(),
        )


# ---------------------------------------------------------------- return


@pytest.mark.django_db
def test_return_reduces_net_issue_and_allows_reissue(plant):
    issue(plant, "40")
    movement = give_back(plant, "10")
    assert movement.kind == "RETURN"
    assert (balance(plant, "RM-A"), balance(plant, "LINE-1")) == (D("70"), D("30"))
    issue(plant, "10")
    with pytest.raises(MaterialLimitError):
        issue(plant, "1")


@pytest.mark.django_db
def test_return_limited_to_what_the_order_holds(plant):
    issue(plant, "20")
    with pytest.raises(MaterialLimitError):
        give_back(plant, "21")
    other_lot = stock(plant, "L4", D("10"))
    with pytest.raises(MaterialLimitError):
        give_back(plant, "1", lot=other_lot)
    # Another order's issue does not raise this order's holding.
    other = order(plant)
    issue(plant, "5", target=other)
    with pytest.raises(MaterialLimitError):
        give_back(plant, "21")
    give_back(plant, "20")


@pytest.mark.django_db
def test_return_destination_must_be_released_for_the_lot(plant):
    issue(plant, "10")
    plant.wh["RM-B"] = type(plant.wh["RM-A"]).objects.create(
        plant=plant.plant, code="RM-B", display_name="RM-B"
    )
    WarehouseRoleAssignment.objects.create(
        user=plant.users["production"], warehouse=plant.wh["RM-B"], role="PRODUCTION"
    )
    with pytest.raises(MaterialQualityError):
        give_back(plant, "5", destination="RM-B")  # L1 is HOLD at RM-B
    with pytest.raises(MaterialValidationError):
        give_back(plant, "5", destination="LINE-1")
    give_back(plant, "5")


@pytest.mark.django_db
def test_cancel_requires_no_material_on_the_line(plant):
    issue(plant, "10")
    with pytest.raises(OrderValidationError, match="line"):
        cancel_production_order(
            order=plant.order, actor=plant.users["production"], reason="Stop", request_id=uuid4()
        )
    give_back(plant, "10")
    cancel_production_order(
        order=plant.order, actor=plant.users["production"], reason="Stop", request_id=uuid4()
    )


# ---------------------------------------------------------------- database rules


def raw_movement(plant, transfer, kind="ISSUE", target=None):
    ProductionMaterialMovement.objects.create(
        order=target or plant.order, kind=kind, transfer=transfer
    )


def plain_transfer(plant, quantity, source="RM-A", destination="LINE-1", lot=None):
    debit, _ = transfer_stock(
        lot=lot or plant.lot,
        source_warehouse=plant.wh[source],
        destination_warehouse=plant.wh[destination],
        actor=plant.staff,
        quantity=D(quantity),
        reason="Synthetic raw transfer",
        request_id=uuid4(),
    )
    return debit.transfer_out


def rejected(action):
    with pytest.raises(IntegrityError), transaction.atomic():
        action()


@pytest.mark.django_db
def test_database_enforces_cap_direction_and_bom(plant):
    rejected(lambda: raw_movement(plant, plain_transfer(plant, "41")))
    rejected(lambda: raw_movement(plant, plain_transfer(plant, "1"), kind="RETURN"))
    rejected(
        lambda: raw_movement(
            plant, plain_transfer(plant, "1", lot=stock(plant, "D2", D("5"), item="driver"))
        )
    )
    raw_movement(plant, plain_transfer(plant, "40"))


@pytest.mark.django_db
def test_movements_are_immutable(plant):
    movement = issue(plant, "5")
    rejected(
        lambda: ProductionMaterialMovement.objects.filter(pk=movement.pk).update(kind="RETURN")
    )
    rejected(
        lambda: connection.cursor().execute(
            "DELETE FROM manufacturing_productionmaterialmovement WHERE id = %s", [movement.pk]
        )
    )
    rejected(lambda: raw_movement(plant, movement.transfer))  # one movement per transfer


# ---------------------------------------------------------------- concurrency


@pytest.mark.django_db(transaction=True)
def test_concurrent_issues_respect_the_cap(plant):
    first, outcome = blocked_action(lambda: issue(plant, "30"), lambda: issue(plant, "30"))
    assert outcome[0] == "MaterialLimitError"
    assert balance(plant, "LINE-1") == D("30")
    assert StockTransfer.objects.count() == 1
