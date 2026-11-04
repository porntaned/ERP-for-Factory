"""M5.1 (Issue #69): column-level CHECK and unique constraints on BOM, BOM line and order."""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from .conftest import activate, raw_bom, raw_order


def rejected(action):
    with pytest.raises(IntegrityError), transaction.atomic():
        action()


@pytest.mark.django_db
def test_version_must_be_positive(mf):
    rejected(lambda: raw_bom(mf, version=0))


@pytest.mark.django_db
def test_version_unique_per_item(mf):
    raw_bom(mf, version=1)
    rejected(lambda: raw_bom(mf, version=1))
    raw_bom(mf, mf.items["lamp2"], version=1)  # another item may reuse 1


@pytest.mark.django_db
def test_one_active_per_item(mf):
    activate(raw_bom(mf, version=1), mf.users["approver"])
    second = raw_bom(mf, version=2)
    rejected(lambda: activate(second, mf.users["approver"]))


@pytest.mark.django_db
def test_approver_differs_from_creator(mf):
    bom = raw_bom(mf)
    rejected(lambda: activate(bom, mf.users["production"]))


@pytest.mark.django_db
def test_draft_has_no_approval(mf):
    bom = raw_bom(mf)
    rejected(
        lambda: (
            type(bom)
            .objects.filter(pk=bom.pk)
            .update(approved_by=mf.users["approver"], approved_at=timezone.now())
        )
    )


@pytest.mark.django_db
def test_active_requires_approval(mf):
    bom = raw_bom(mf)
    rejected(lambda: type(bom).objects.filter(pk=bom.pk).update(status="ACTIVE"))


@pytest.mark.django_db
@pytest.mark.parametrize("qty", ["0", "-1", "0.0000001", "100000000000000"])
def test_line_quantity_positive_and_six_decimals(mf, qty):
    rejected(lambda: raw_bom(mf, lines=[(mf.items["chip"], Decimal(qty))]))


@pytest.mark.django_db
def test_line_component_unique_per_bom(mf):
    chip = mf.items["chip"]
    rejected(lambda: raw_bom(mf, lines=[(chip, Decimal("1")), (chip, Decimal("2"))]))


@pytest.mark.django_db
@pytest.mark.parametrize("qty", ["0", "-5", "1.0000001"])
def test_order_quantity_positive(mf, qty):
    bom = activate(raw_bom(mf), mf.users["approver"])
    rejected(lambda: raw_order(mf, bom, quantity=Decimal(qty)))


@pytest.mark.django_db
def test_order_warehouses_differ(mf):
    bom = activate(raw_bom(mf), mf.users["approver"])
    rejected(lambda: raw_order(mf, bom, output_warehouse=mf.wh["LINE-1"]))


@pytest.mark.django_db
def test_cancel_fields_set_together_only_when_cancelled(mf):
    bom = activate(raw_bom(mf), mf.users["approver"])
    order = raw_order(mf, bom)
    rows = type(order).objects.filter(pk=order.pk)
    rejected(lambda: rows.update(status="CANCELLED"))
    rejected(lambda: rows.update(cancel_reason="x", cancelled_by=mf.users["production"]))
    rows.update(
        status="CANCELLED",
        cancelled_by=mf.users["production"],
        cancelled_at=timezone.now(),
        cancel_reason="Synthetic cancel",
        cancel_request_id=uuid4(),
    )
