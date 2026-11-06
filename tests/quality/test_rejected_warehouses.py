"""M6.2 (Issue #103): Quality's read of where a Lot is REJECTED.

Inventory enforces the owner's rule (a REJECTED Lot is unusable at every warehouse); Quality owns
the reading. The latest event per warehouse decides, as in get_lot_disposition.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model

from access_control.models import WarehouseRoleAssignment
from inventory.models import Lot, StockLedgerEntry
from quality import services as quality_services
from quality.services import return_rejected_to_hold
from tests.manufacturing.conftest import mf as mf  # noqa: F401
from tests.quality.helpers import force_reject, force_release, give_origin


@pytest.fixture
def scope(mf):
    qc = get_user_model().objects.create(username="mf-qc-reject")
    for code in ("RM-A", "LINE-1", "FG"):
        WarehouseRoleAssignment.objects.create(user=qc, warehouse=mf.wh[code], role="QUALITY")
    mf.qc = qc
    mf.lot = Lot.objects.create(item=mf.items["chip"], code="L1")
    give_origin(
        StockLedgerEntry.objects.create(
            lot=mf.lot,
            warehouse=mf.wh["RM-A"],
            actor=qc,
            quantity_delta=Decimal("5"),
            reason="Synthetic origin",
        )
    )
    return mf


def rejected_codes(scope, lot=None):
    found = quality_services.get_rejected_warehouses(lot=lot or scope.lot)
    return [warehouse.code for warehouse in found]


@pytest.mark.django_db
def test_a_lot_with_no_events_is_rejected_nowhere(scope):
    assert rejected_codes(scope) == []


@pytest.mark.django_db
def test_lists_every_warehouse_where_the_latest_event_is_rejected(scope):
    force_reject(scope.lot, scope.wh["RM-A"], scope.qc)
    force_reject(scope.lot, scope.wh["FG"], scope.qc)
    force_release(scope.lot, scope.wh["LINE-1"], scope.qc)
    assert rejected_codes(scope) == ["RM-A", "FG"]


@pytest.mark.django_db
def test_returning_to_hold_removes_the_warehouse(scope):
    force_reject(scope.lot, scope.wh["RM-A"], scope.qc)
    force_reject(scope.lot, scope.wh["FG"], scope.qc)
    return_rejected_to_hold(
        lot=scope.lot,
        warehouse=scope.wh["RM-A"],
        actor=scope.users["approver"],
        reason="Re-test",
        request_id=uuid4(),
    )
    assert rejected_codes(scope) == ["FG"]


@pytest.mark.django_db
def test_other_lots_are_not_affected(scope):
    other = Lot.objects.create(item=scope.items["chip"], code="L2")
    force_reject(scope.lot, scope.wh["RM-A"], scope.qc)
    assert rejected_codes(scope, other) == []
