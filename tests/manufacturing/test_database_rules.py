"""M5.1 (Issue #69): cross-table and lifecycle rules PostgreSQL enforces for every writer,
including raw SQL, plus registration of manufacturing keys in the shared RequestKey registry.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from inventory.models import RequestKey
from manufacturing.models import BillOfMaterials, BomLine, ProductionOrder

from .conftest import activate, raw_bom, raw_order


def rejected(action):
    with pytest.raises(IntegrityError), transaction.atomic():
        action()


def sql(statement, params=()):
    with connection.cursor() as cursor:
        cursor.execute(statement, params)


def retire(bom):
    BillOfMaterials.objects.filter(pk=bom.pk).update(status="RETIRED")
    bom.refresh_from_db()
    return bom


def cancel(order):
    ProductionOrder.objects.filter(pk=order.pk).update(
        status="CANCELLED",
        cancelled_by=order.created_by,
        cancelled_at=timezone.now(),
        cancel_reason="Synthetic cancel",
        cancel_request_id=uuid4(),
    )


# ---------------------------------------------------------------- BOM header


@pytest.mark.django_db
def test_bom_item_must_be_finished_or_wip(mf):
    rejected(lambda: raw_bom(mf, mf.items["chip"]))
    raw_bom(mf, mf.items["board"])  # WIP is allowed


@pytest.mark.django_db
def test_bom_insert_must_be_draft(mf):
    rejected(
        lambda: BillOfMaterials.objects.create(
            item=mf.items["lamp"],
            version=1,
            status="ACTIVE",
            created_by=mf.users["production"],
            approved_by=mf.users["approver"],
            approved_at=timezone.now(),
            request_id=uuid4(),
            approval_request_id=uuid4(),
        )
    )


@pytest.mark.django_db
def test_bom_status_moves_forward_only(mf):
    draft = raw_bom(mf, version=1)
    rejected(
        lambda: sql(
            "UPDATE manufacturing_billofmaterials SET status='RETIRED' WHERE id=%s", [draft.pk]
        )
    )
    active = activate(draft, mf.users["approver"])
    rejected(
        lambda: sql(
            "UPDATE manufacturing_billofmaterials SET status='DRAFT', approved_by_id=NULL,"
            " approved_at=NULL, approval_request_id=NULL WHERE id=%s",
            [active.pk],
        )
    )
    retired = retire(active)
    rejected(
        lambda: sql(
            "UPDATE manufacturing_billofmaterials SET status='ACTIVE' WHERE id=%s", [retired.pk]
        )
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "column,value",
    [
        ("version", 9),
        ("request_id", "00000000-0000-0000-0000-000000000001"),
        ("created_by_id", None),
    ],
)
def test_bom_identity_fields_immutable(mf, column, value):
    bom = raw_bom(mf)
    value = mf.users["approver"].pk if column == "created_by_id" else value
    rejected(
        lambda: sql(
            f"UPDATE manufacturing_billofmaterials SET {column}=%s WHERE id=%s", [value, bom.pk]
        )
    )
    rejected(
        lambda: sql(
            "UPDATE manufacturing_billofmaterials SET item_id=%s WHERE id=%s",
            [mf.items["lamp2"].pk, bom.pk],
        )
    )


@pytest.mark.django_db
def test_bom_approval_written_once(mf):
    bom = retire(activate(raw_bom(mf), mf.users["approver"]))
    rejected(
        lambda: BillOfMaterials.objects.filter(pk=bom.pk).update(approved_by=mf.users["approver2"])
    )
    rejected(lambda: BillOfMaterials.objects.filter(pk=bom.pk).update(approval_request_id=uuid4()))


@pytest.mark.django_db
def test_bom_never_deleted(mf):
    bom = raw_bom(mf)
    sql("DELETE FROM manufacturing_bomline WHERE bom_id=%s", [bom.pk])  # draft lines may go
    rejected(lambda: sql("DELETE FROM manufacturing_billofmaterials WHERE id=%s", [bom.pk]))


# ---------------------------------------------------------------- BOM lines


@pytest.mark.django_db
def test_line_component_must_be_raw_or_wip(mf):
    rejected(lambda: raw_bom(mf, lines=[(mf.items["lamp2"], Decimal("1"))]))
    raw_bom(mf, lines=[(mf.items["board"], Decimal("1"))])


@pytest.mark.django_db
def test_line_component_same_organization(mf):
    rejected(lambda: raw_bom(mf, lines=[(mf.items["foreign"], Decimal("1"))]))


@pytest.mark.django_db
def test_line_component_not_bom_item(mf):
    board = mf.items["board"]
    rejected(lambda: raw_bom(mf, board, lines=[(board, Decimal("1"))]))


@pytest.mark.django_db
@pytest.mark.parametrize("final", ["ACTIVE", "RETIRED"])
def test_lines_locked_after_draft(mf, final):
    bom = activate(raw_bom(mf), mf.users["approver"])
    if final == "RETIRED":
        retire(bom)
    line = bom.lines.get()
    rejected(
        lambda: BomLine.objects.create(
            bom=bom, component=mf.items["driver"], quantity_per=Decimal("1")
        )
    )
    rejected(lambda: BomLine.objects.filter(pk=line.pk).update(quantity_per=Decimal("5")))
    rejected(lambda: BomLine.objects.filter(pk=line.pk).delete())
    assert bom.lines.get().quantity_per == Decimal("4")


@pytest.mark.django_db
def test_draft_line_may_not_move_to_another_bom(mf):
    bom = raw_bom(mf, version=1)
    other = raw_bom(mf, mf.items["lamp2"], version=1, lines=[(mf.items["driver"], Decimal("1"))])
    rejected(lambda: BomLine.objects.filter(bom=bom).update(bom=other))


# ---------------------------------------------------------------- production orders


@pytest.mark.django_db
def test_order_requires_active_bom(mf):
    draft = raw_bom(mf, version=1)
    rejected(lambda: raw_order(mf, draft))
    retired = retire(activate(draft, mf.users["approver"]))
    rejected(lambda: raw_order(mf, retired))


@pytest.mark.django_db
def test_order_warehouses_same_plant_in_item_org(mf):
    bom = activate(raw_bom(mf), mf.users["approver"])
    rejected(lambda: raw_order(mf, bom, output_warehouse=mf.wh["P2-FG"]))
    rejected(lambda: raw_order(mf, bom, line_warehouse=mf.wh["X-LINE"]))
    foreign = activate(
        raw_bom(mf, mf.items["foreign_lamp"], lines=[(mf.items["foreign"], Decimal("1"))]),
        mf.users["approver"],
    )
    rejected(lambda: raw_order(mf, foreign))  # P1 warehouses belong to another organization


@pytest.mark.django_db
def test_order_survives_bom_retirement(mf):
    bom = activate(raw_bom(mf), mf.users["approver"])
    order = raw_order(mf, bom)
    retire(bom)
    cancel(order)  # an order on a now-retired version can still be cancelled
    assert ProductionOrder.objects.get(pk=order.pk).status == "CANCELLED"


@pytest.mark.django_db
def test_order_only_open_to_cancelled(mf):
    bom = activate(raw_bom(mf), mf.users["approver"])
    order = raw_order(mf, bom)
    rows = ProductionOrder.objects.filter(pk=order.pk)
    rejected(lambda: rows.update(quantity=Decimal("11")))
    rejected(lambda: rows.update(output_warehouse=mf.wh["RM-A"]))
    cancel(order)
    rejected(
        lambda: rows.update(
            status="OPEN",
            cancelled_by=None,
            cancelled_at=None,
            cancel_reason=None,
            cancel_request_id=None,
        )
    )
    rejected(lambda: rows.update(cancel_reason="Rewritten"))


@pytest.mark.django_db
def test_order_never_deleted(mf):
    order = raw_order(mf, activate(raw_bom(mf), mf.users["approver"]))
    rejected(lambda: sql("DELETE FROM manufacturing_productionorder WHERE id=%s", [order.pk]))


# ---------------------------------------------------------------- shared request keys


@pytest.mark.django_db
def test_keys_registered_per_command(mf):
    bom = raw_bom(mf)
    bom = activate(bom, mf.users["approver"])
    order = raw_order(mf, bom)
    cancel(order)
    order.refresh_from_db()
    registered = dict(RequestKey.objects.values_list("request_id", "command"))
    assert registered[bom.request_id] == "BOM_DRAFT"
    assert registered[bom.approval_request_id] == "BOM_APPROVE"
    assert registered[order.request_id] == "ORDER_CREATE"
    assert registered[order.cancel_request_id] == "ORDER_CANCEL"


@pytest.mark.django_db
def test_key_shared_with_inventory_command_rejected(mf):
    key = uuid4()
    RequestKey.objects.create(request_id=key, command="RECEIPT")
    rejected(lambda: raw_bom(mf, request_id=key))
    assert not BillOfMaterials.objects.exists()
