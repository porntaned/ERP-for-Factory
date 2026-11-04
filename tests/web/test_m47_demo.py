"""M4.7 (Issue #66): the Inventory demo walked end to end through the screens.

seed_demo receives 100 of lot L-0001 at RM-A and releases it; demo-warehouse logs in with a
password set by set_demo_passwords, opens the transfer form, posts 30 to RM-B with the form's
own request UUID, and sees 70 / 30 on the balance page and the transfer on the history page.
No test helper writes stock: every movement goes through the screens or seed_demo.
"""

import io
import re
from decimal import Decimal

import pytest
from django.core.management import call_command

from demo.quantities import format_quantity
from facilities.models import Warehouse
from inventory.models import Lot, StockLedgerEntry, StockReceipt, StockTransfer
from inventory.services import get_stock_balance

PASSWORD = "synthetic-demo-pass"


def balance_rows(html):
    """(lot, warehouse, balance, quality) for each row of the balance table."""
    return re.findall(
        r"<tr><td>LED-CHIP</td><td>(L-\d+)</td><td>([\w-]+)</td>"
        r'<td class="text-end">([\d.]+)</td><td>(\w+)</td></tr>',
        html,
    )


def hidden_request_id(html):
    return re.search(r'name="request_id" value="([0-9a-f-]{36})"', html).group(1)


@pytest.mark.django_db
def test_demo_receive_100_transfer_30_shows_70_and_30(client, monkeypatch):
    call_command("seed_demo", verbosity=0)
    monkeypatch.setattr("sys.stdin", io.StringIO(PASSWORD + "\n"))
    call_command("set_demo_passwords", password_stdin=True, verbosity=0)
    lot = Lot.objects.get(code="L-0001")
    rm_a, rm_b = (Warehouse.objects.get(code=code) for code in ("RM-A", "RM-B"))

    # 1. Log in through the login page, not force_login.
    response = client.post("/accounts/login/", {"username": "demo-warehouse", "password": PASSWORD})
    assert response.status_code == 302 and response["Location"] == "/"

    # 2. Before: 100 at RM-A, RELEASED; nothing at RM-B.
    before = client.get("/").content.decode()
    assert balance_rows(before) == [("L-0001", "RM-A", "100", "RELEASED")]

    # 3. Open the transfer form and post 30 RM-A -> RM-B with the form's own request UUID.
    form_page = client.get("/transfers/new/")
    assert form_page.status_code == 200
    data = {
        "lot": lot.pk,
        "source_warehouse": rm_a.pk,
        "destination_warehouse": rm_b.pk,
        "quantity": "30",
        "reason": "M4.7 demo transfer",
        "request_id": hidden_request_id(form_page.content.decode()),
    }
    response = client.post("/transfers/new/", data, follow=True)
    assert response.redirect_chain == [("/", 302)]
    after = response.content.decode()
    assert "โอนสำเร็จ 30 RM-A → RM-B" in after

    # 4. After: 70 / 30. RM-B keeps its own HOLD disposition (M4.3.3 policy).
    assert balance_rows(after) == [
        ("L-0001", "RM-A", "70", "RELEASED"),
        ("L-0001", "RM-B", "30", "HOLD"),
    ]
    assert get_stock_balance(lot=lot, warehouse=rm_a) == Decimal("70")
    assert get_stock_balance(lot=lot, warehouse=rm_b) == Decimal("30")

    # 5. A double submit of the same form replays; it does not post a second time.
    client.post("/transfers/new/", data)
    assert StockTransfer.objects.count() == 1
    assert get_stock_balance(lot=lot, warehouse=rm_a) == Decimal("70")

    # 6. The ledger holds exactly receipt +100, transfer -30 / +30, all by demo-warehouse.
    transfer = StockTransfer.objects.select_related("source_entry", "destination_entry").get()
    assert str(transfer.request_id) == data["request_id"]
    assert (transfer.source_entry.warehouse, transfer.source_entry.quantity_delta) == (
        rm_a,
        Decimal("-30"),
    )
    assert (transfer.destination_entry.warehouse, transfer.destination_entry.quantity_delta) == (
        rm_b,
        Decimal("30"),
    )
    assert transfer.source_entry.lot == transfer.destination_entry.lot == lot
    assert sorted(StockLedgerEntry.objects.values_list("quantity_delta", flat=True)) == [
        Decimal("-30"),
        Decimal("30"),
        Decimal("100"),
    ]
    assert set(StockLedgerEntry.objects.values_list("actor__username", flat=True)) == {
        "demo-warehouse"
    }

    # 7. History shows the seeded receipt and the transfer, without reverse buttons for
    #    demo-warehouse (APPROVER only).
    history = client.get("/history/").content.decode()
    receipt = StockReceipt.objects.get()
    assert f"<td>R{receipt.pk}</td><td>L-0001</td><td>RM-A</td>" in history
    assert (
        f"<td>T{transfer.pk}</td><td>L-0001</td>\n    <td>RM-A → RM-B</td>\n"
        f'    <td class="text-end">30</td>' in history
    )
    assert "M4.7 demo transfer" in history
    assert 'data-action="reverse-transfer"' not in history


@pytest.mark.parametrize(
    "value,shown",
    [
        ("30", "30"),
        ("100", "100"),
        ("70.000", "70"),
        ("-30", "-30"),
        ("2.500", "2.5"),
        ("0.001", "0.001"),
        ("0", "0"),
    ],
)
def test_quantities_are_shown_without_scientific_notation(value, shown):
    """Decimal.normalize() alone shows 30 as "3E+1"; found while walking the M4.7 demo."""
    assert format_quantity(Decimal(value)) == shown
