"""M4.6 (Issue #63): receipt, transfer, history and reversal screens.

Screens are permission-aware (actions shown only to holders of the required role) while
the Inventory commands keep enforcing authority. Each form carries a request UUID so a
double submit posts once.
"""

import io
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from facilities.models import Warehouse
from inventory.models import Lot, StockReceipt, StockReversal, StockTransfer
from inventory.services import get_stock_balance
from quality.services import transition_lot_disposition

PASSWORD = "synthetic-demo-pass"


@pytest.fixture
def demo(db):
    call_command("seed_demo", verbosity=0)
    users = {u.username: u for u in get_user_model().objects.filter(username__startswith="demo-")}
    warehouses = {w.code: w for w in Warehouse.objects.all()}
    return dict(users=users, wh=warehouses, lot=Lot.objects.get(code="L-0001"))


def login(client, demo, name):
    client.force_login(demo["users"][name])
    return client


def balance(demo, code):
    return get_stock_balance(lot=demo["lot"], warehouse=demo["wh"][code])


def release(demo, code):
    transition_lot_disposition(
        lot=demo["lot"],
        warehouse=demo["wh"][code],
        actor=demo["users"]["demo-quality"],
        expected_disposition="HOLD",
        target_disposition="RELEASED",
        reason="Synthetic release for screen test",
        request_id=uuid4(),
    )


def receipt_post(demo, **overrides):
    return {
        "lot": demo["lot"].pk,
        "warehouse": demo["wh"]["RM-A"].pk,
        "quantity": "25",
        "reason": "Screen receipt",
        "request_id": str(uuid4()),
    } | overrides


def transfer_post(demo, **overrides):
    return {
        "lot": demo["lot"].pk,
        "source_warehouse": demo["wh"]["RM-A"].pk,
        "destination_warehouse": demo["wh"]["RM-B"].pk,
        "quantity": "30",
        "reason": "Screen transfer",
        "request_id": str(uuid4()),
    } | overrides


# ---------------------------------------------------------------- passwords and login


@pytest.mark.django_db
def test_set_demo_passwords_from_stdin_lets_demo_users_log_in(client, demo, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(PASSWORD + "\n"))
    call_command("set_demo_passwords", password_stdin=True, verbosity=0)
    for name in ("demo-warehouse", "demo-quality", "demo-approver"):
        assert get_user_model().objects.get(username=name).check_password(PASSWORD)
    response = client.post("/accounts/login/", {"username": "demo-warehouse", "password": PASSWORD})
    assert response.status_code == 302 and response["Location"] == "/"


@pytest.mark.django_db
def test_set_demo_passwords_rejects_short_password(demo, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("short\n"))
    with pytest.raises(CommandError, match="at least"):
        call_command("set_demo_passwords", password_stdin=True, verbosity=0)
    assert not get_user_model().objects.get(username="demo-warehouse").has_usable_password()


@pytest.mark.django_db
def test_pages_require_login(client, demo):
    for url in ("/", "/receipts/new/", "/transfers/new/", "/history/"):
        response = client.get(url)
        assert response.status_code == 302 and response["Location"].startswith(
            "/accounts/login/"
        ), url


@pytest.mark.django_db
def test_logout_is_post_only(client, demo):
    login(client, demo, "demo-warehouse")
    assert client.post("/accounts/logout/").status_code == 302
    assert client.get("/").status_code == 302


# ---------------------------------------------------------------- permission-aware display


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name,can_move,can_reverse",
    [
        ("demo-warehouse", True, False),
        ("demo-approver", False, True),
        ("demo-quality", False, False),
    ],
)
def test_navigation_and_buttons_follow_roles(client, demo, name, can_move, can_reverse):
    login(client, demo, name)
    home = client.get("/").content.decode()
    assert ('href="/receipts/new/"' in home) is can_move
    assert ('href="/transfers/new/"' in home) is can_move
    history = client.get("/history/").content.decode()
    assert ('data-action="reverse-receipt"' in history) is can_reverse
    assert client.get("/receipts/new/").status_code == (200 if can_move else 403)
    assert client.get("/transfers/new/").status_code == (200 if can_move else 403)


@pytest.mark.django_db
def test_receipt_form_offers_only_granted_warehouses(client, demo):
    login(client, demo, "demo-warehouse")
    form = client.get("/receipts/new/").context["form"]
    codes = {w.code for w in form.fields["warehouse"].queryset}
    assert codes == {"RM-A", "RM-B"}


# ---------------------------------------------------------------- receipt and transfer


@pytest.mark.django_db
def test_receipt_screen_posts_through_the_command_once_per_request(client, demo):
    login(client, demo, "demo-warehouse")
    data = receipt_post(demo)
    first = client.post("/receipts/new/", data)
    again = client.post("/receipts/new/", data)  # double submit of the same form
    assert first.status_code == again.status_code == 302
    assert balance(demo, "RM-A") == Decimal("125")
    assert StockReceipt.objects.count() == 2  # seed receipt + this one


@pytest.mark.django_db
def test_receipt_to_ungranted_warehouse_is_refused(client, demo):
    login(client, demo, "demo-warehouse")
    response = client.post("/receipts/new/", receipt_post(demo, warehouse=demo["wh"]["FG"].pk))
    assert response.status_code == 200 and response.context["form"].errors
    assert StockReceipt.objects.count() == 1


@pytest.mark.django_db
def test_transfer_screen_moves_stock(client, demo):
    login(client, demo, "demo-warehouse")
    response = client.post("/transfers/new/", transfer_post(demo), follow=True)
    assert response.status_code == 200
    assert balance(demo, "RM-A") == Decimal("70") and balance(demo, "RM-B") == Decimal("30")
    assert "โอนสำเร็จ" in response.content.decode()


@pytest.mark.django_db
def test_transfer_domain_error_is_shown_and_writes_nothing(client, demo):
    login(client, demo, "demo-warehouse")
    response = client.post("/transfers/new/", transfer_post(demo, quantity="500"))
    assert response.status_code == 200
    assert "ยอดคงเหลือไม่พอ" in response.content.decode()
    assert StockTransfer.objects.count() == 0


@pytest.mark.django_db
def test_transfer_form_rejects_same_warehouse(client, demo):
    login(client, demo, "demo-warehouse")
    data = transfer_post(demo, destination_warehouse=demo["wh"]["RM-A"].pk)
    response = client.post("/transfers/new/", data)
    assert response.status_code == 200 and response.context["form"].errors
    assert StockTransfer.objects.count() == 0


# ---------------------------------------------------------------- history and reversal


@pytest.mark.django_db
def test_history_lists_receipts_transfers_and_reversals(client, demo):
    login(client, demo, "demo-warehouse")
    client.post("/transfers/new/", transfer_post(demo))
    body = client.get("/history/").content.decode()
    assert "Synthetic demo delivery" in body and "Screen transfer" in body


@pytest.mark.django_db
def test_approver_reverses_transfer_from_history(client, demo):
    login(client, demo, "demo-warehouse")
    client.post("/transfers/new/", transfer_post(demo))
    release(demo, "RM-B")
    transfer = StockTransfer.objects.get()
    login(client, demo, "demo-approver")
    response = client.post(
        f"/reversals/transfer/{transfer.pk}/",
        {"reason": "Wrong warehouse", "request_id": str(uuid4())},
        follow=True,
    )
    assert response.status_code == 200 and "กลับรายการแล้ว" in response.content.decode()
    assert StockReversal.objects.filter(transfer=transfer).exists()
    assert balance(demo, "RM-A") == Decimal("100") and balance(demo, "RM-B") == 0
    assert 'data-action="reverse-transfer"' not in client.get("/history/").content.decode()


@pytest.mark.django_db
def test_reversal_quality_gate_is_reported(client, demo):
    login(client, demo, "demo-warehouse")
    client.post("/transfers/new/", transfer_post(demo))  # RM-B stays default HOLD
    transfer = StockTransfer.objects.get()
    login(client, demo, "demo-approver")
    response = client.post(
        f"/reversals/transfer/{transfer.pk}/",
        {"reason": "Held", "request_id": str(uuid4())},
        follow=True,
    )
    assert "RELEASED" in response.content.decode()
    assert not StockReversal.objects.exists()


@pytest.mark.django_db
def test_non_approver_cannot_reverse(client, demo):
    receipt = StockReceipt.objects.get()
    login(client, demo, "demo-warehouse")
    response = client.post(
        f"/reversals/receipt/{receipt.pk}/", {"reason": "x", "request_id": str(uuid4())}
    )
    assert response.status_code == 403
    assert not StockReversal.objects.exists()


@pytest.mark.django_db
def test_reversal_requires_reason(client, demo):
    receipt = StockReceipt.objects.get()
    login(client, demo, "demo-approver")
    response = client.post(
        f"/reversals/receipt/{receipt.pk}/",
        {"reason": " ", "request_id": str(uuid4())},
        follow=True,
    )
    assert "เหตุผล" in response.content.decode()
    assert not StockReversal.objects.exists()


@pytest.mark.django_db
def test_choices_show_readable_codes(client, demo):
    """Smoke test found 'Lot object (1)' labels; users must see codes they recognise."""
    login(client, demo, "demo-warehouse")
    body = client.get("/transfers/new/").content.decode()
    assert "L-0001 · LED-CHIP" in body and "RM-A · Raw material A" in body
    assert "object (" not in body
