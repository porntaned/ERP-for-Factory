# ruff: noqa: F811, F401 (fixtures imported from sibling test modules)
"""M6.2 (Issue #103): a screen that posts for a REJECTED Lot shows a message, not a 500.

The Inventory and Manufacturing commands refuse (tests/inventory/test_rejected_lot_gate.py);
these tests check that every demo screen that posts a transfer, issue, return, consume, receipt,
output or reversal turns that refusal into a Thai message and records nothing, while SCRAP and
the reversal of a receipt, which only take stock out, still work.
"""

from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model

from inventory.models import StockLedgerEntry, StockReceipt, StockReversal, StockTransfer
from manufacturing.models import OrderPosting
from tests.quality.helpers import force_reject

from .test_inventory_screens import demo, login, receipt_post, release, transfer_post
from .test_production_screens import as_user, issue, lot, open_order, page, plant, submit, wh

REJECTED_MESSAGE = "ถูก REJECTED"


def reject_at(code, name="L-0001", user="demo-quality"):
    force_reject(lot(name), wh(code), get_user_model().objects.get(username=user))


def ledger():
    return StockLedgerEntry.objects.count()


# ---------------------------------------------------------------- inventory screens


@pytest.mark.django_db
def test_receipt_screen_shows_a_message_for_a_rejected_lot(client, demo):
    reject_at("RM-B")
    login(client, demo, "demo-warehouse")
    before = ledger()
    response = client.post("/receipts/new/", receipt_post(demo))
    assert response.status_code == 200 and REJECTED_MESSAGE in response.content.decode()
    assert ledger() == before


@pytest.mark.django_db
def test_transfer_screen_shows_a_message_for_a_rejected_lot(client, demo):
    reject_at("FG")
    login(client, demo, "demo-warehouse")
    before = ledger()
    response = client.post("/transfers/new/", transfer_post(demo))
    assert response.status_code == 200 and REJECTED_MESSAGE in response.content.decode()
    assert ledger() == before


@pytest.mark.django_db
def test_reversal_of_a_transfer_shows_a_message_but_a_receipt_reversal_works(client, demo):
    login(client, demo, "demo-warehouse")
    client.post("/transfers/new/", transfer_post(demo))
    client.post("/receipts/new/", receipt_post(demo))  # 25 more, to reverse later
    release(demo, "RM-B")
    transfer = StockTransfer.objects.get()
    reject_at("FG")
    login(client, demo, "demo-approver")
    before = ledger()
    response = client.post(
        f"/reversals/transfer/{transfer.pk}/",
        {"reason": "Wrong warehouse", "request_id": str(uuid4())},
        follow=True,
    )
    assert response.status_code == 200 and REJECTED_MESSAGE in response.content.decode()
    assert ledger() == before and not StockReversal.objects.exists()
    receipt = StockReceipt.objects.order_by("pk").last()  # taking stock out stays allowed
    client.post(
        f"/reversals/receipt/{receipt.pk}/",
        {"reason": "Counted wrong", "request_id": str(uuid4())},
    )
    assert StockReversal.objects.filter(receipt=receipt).exists()


# ---------------------------------------------------------------- production screens


@pytest.mark.django_db
def test_issue_screen_shows_a_message_for_a_rejected_lot(client, open_order):
    reject_at("FG")
    before = ledger()
    response = issue(client, open_order, "L-0001", "4")
    assert response.status_code == 200 and REJECTED_MESSAGE in response.content.decode()
    assert ledger() == before


@pytest.mark.django_db
def test_line_screens_show_a_message_for_a_rejected_lot_and_scrap_still_works(client, open_order):
    o = open_order.pk
    assert issue(client, open_order, "L-0001", "4").status_code == 302
    consumed = submit(
        client, f"/production/{o}/consume/", lot=lot("L-0001").pk, quantity="1", reason="Run"
    )
    assert consumed.status_code == 302
    link = OrderPosting.objects.get(order=open_order, kind="CONSUME")
    reject_at("FG")
    before = ledger()
    for path, extra in (
        ("consume", dict(quantity="1", reason="Run")),
        ("return", dict(quantity="1", reason="Back", destination_warehouse=wh("RM-A").pk)),
    ):
        response = submit(client, f"/production/{o}/{path}/", lot=lot("L-0001").pk, **extra)
        assert response.status_code == 200, path
        assert REJECTED_MESSAGE in response.content.decode(), path
    as_user(client, "demo-approver")
    response = submit(client, f"/production/{o}/reverse/{link.pk}/", reason="Recorded in error")
    assert response.status_code == 200 and REJECTED_MESSAGE in response.content.decode()
    assert ledger() == before
    response = submit(
        client, f"/production/{o}/scrap/", lot=lot("L-0001").pk, quantity="3", reason="Rejected"
    )
    assert response.status_code == 302 and ledger() == before + 1


@pytest.mark.django_db
def test_output_screen_shows_a_message_for_a_rejected_lot(client, open_order):
    o = open_order.pk
    as_user(client, "demo-production")
    data = dict(lot_code="LAMP-1001", quantity="1", reason="Output")
    assert submit(client, f"/production/{o}/output/", **data).status_code == 302
    reject_at("FG", "LAMP-1001")
    before = ledger()
    response = submit(client, f"/production/{o}/output/", **data)
    assert response.status_code == 200 and REJECTED_MESSAGE in response.content.decode()
    assert ledger() == before
