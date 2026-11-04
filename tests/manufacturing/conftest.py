"""Synthetic manufacturing scope for M5.1 (Issue #69): one organization, plant P1 with RM-A,
LINE-1 and FG, a second organization for scope checks, and users granted like seed_demo.
"""

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from access_control.models import WarehouseRoleAssignment
from catalog.models import Item, UnitOfMeasure
from facilities.models import Organization, Plant, Warehouse


def _item(org, uom, code, kind):
    return Item.objects.create(
        organization=org, code=code, display_name=code, item_type=kind, base_uom=uom
    )


@pytest.fixture
def mf(db):
    org = Organization.objects.create(code="LEDCO", display_name="Synthetic LED")
    other_org = Organization.objects.create(code="OTHER", display_name="Other synthetic")
    plant = Plant.objects.create(organization=org, code="P1", display_name="Plant 1")
    plant2 = Plant.objects.create(organization=org, code="P2", display_name="Plant 2")
    other_plant = Plant.objects.create(organization=other_org, code="X1", display_name="X")
    wh = {
        code: Warehouse.objects.create(plant=plant, code=code, display_name=code)
        for code in ("RM-A", "LINE-1", "FG")
    }
    wh["P2-FG"] = Warehouse.objects.create(plant=plant2, code="FG", display_name="P2 FG")
    wh["X-LINE"] = Warehouse.objects.create(plant=other_plant, code="LINE", display_name="X")
    uom = UnitOfMeasure.objects.create(code="EA", display_name="Each")
    items = {
        "chip": _item(org, uom, "LED-CHIP", "RAW"),
        "driver": _item(org, uom, "DRIVER", "RAW"),
        "board": _item(org, uom, "BOARD", "WIP"),
        "lamp": _item(org, uom, "LAMP-A19", "FINISHED"),
        "lamp2": _item(org, uom, "LAMP-B", "FINISHED"),
        "foreign": _item(other_org, uom, "FOREIGN", "RAW"),
        "foreign_lamp": _item(other_org, uom, "FOREIGN-LAMP", "FINISHED"),
    }
    users = {}
    for name in ("production", "approver", "approver2", "outsider", "foreign"):
        users[name] = get_user_model().objects.create(username=f"mf-{name}")
    grants = [
        ("production", "PRODUCTION", ("RM-A", "LINE-1", "FG")),
        ("approver", "APPROVER", ("RM-A",)),
        ("approver2", "APPROVER", ("FG",)),
        ("approver", "PRODUCTION", ("LINE-1", "FG")),
        ("foreign", "PRODUCTION", ("X-LINE",)),
        ("foreign", "APPROVER", ("X-LINE",)),
    ]
    for user, role, codes in grants:
        for code in codes:
            WarehouseRoleAssignment.objects.create(user=users[user], warehouse=wh[code], role=role)
    return SimpleNamespace(org=org, plant=plant, wh=wh, items=items, users=users)


def raw_bom(mf, item=None, *, version=1, creator=None, lines=None, request_id=None):
    """Insert a DRAFT BOM directly (no command), with lines."""
    from manufacturing.models import BillOfMaterials, BomLine

    bom = BillOfMaterials.objects.create(
        item=item or mf.items["lamp"],
        version=version,
        created_by=creator or mf.users["production"],
        request_id=request_id or uuid4(),
    )
    for component, qty in lines or [(mf.items["chip"], Decimal("4"))]:
        BomLine.objects.create(bom=bom, component=component, quantity_per=qty)
    return bom


def activate(bom, approver):
    """Move a DRAFT BOM to ACTIVE directly (no command)."""
    type(bom).objects.filter(pk=bom.pk).update(
        status="ACTIVE",
        approved_by=approver,
        approved_at=timezone.now(),
        approval_request_id=uuid4(),
    )
    bom.refresh_from_db()
    return bom


def raw_order(mf, bom, **overrides):
    from manufacturing.models import ProductionOrder

    fields = (
        dict(
            bom=bom,
            quantity=Decimal("10"),
            line_warehouse=mf.wh["LINE-1"],
            output_warehouse=mf.wh["FG"],
            created_by=mf.users["production"],
            request_id=uuid4(),
        )
        | overrides
    )
    return ProductionOrder.objects.create(**fields)
