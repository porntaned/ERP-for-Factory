"""M5.1 (Issue #69): seed_demo adds the production line, a production user and an approved
LAMP-A19 BOM through the real commands, stays rerunnable and moves no stock."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from access_control.models import WarehouseRoleAssignment
from facilities.models import Warehouse
from inventory.models import StockLedgerEntry
from manufacturing.models import BillOfMaterials


@pytest.mark.django_db
def test_seed_demo_adds_line_production_user_and_active_bom():
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)
    assert Warehouse.objects.filter(code="LINE-1").count() == 1
    production = get_user_model().objects.get(username="demo-production")
    assert set(
        WarehouseRoleAssignment.objects.filter(user=production).values_list(
            "warehouse__code", "role"
        )
    ) == {(code, "PRODUCTION") for code in ("RM-A", "RM-B", "LINE-1", "FG")}
    bom = BillOfMaterials.objects.get()
    assert (bom.item.code, bom.version, bom.status) == ("LAMP-A19", 1, "ACTIVE")
    assert (bom.created_by.username, bom.approved_by.username) == (
        "demo-production",
        "demo-approver",
    )
    assert dict(bom.lines.values_list("component__code", "quantity_per")) == {
        "LED-CHIP": Decimal("4"),
        "DRIVER": Decimal("1"),
    }
    assert StockLedgerEntry.objects.count() == 1  # only the M4 receipt
