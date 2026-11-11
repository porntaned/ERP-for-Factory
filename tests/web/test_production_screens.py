"""M5.5 (Issue #89): Manufacturing screens over the seed_production_demo order.

PR 1 is read-only: the order list, the order page (materials, outputs, history) and Lot
genealogy show what the Manufacturing commands recorded and write nothing.
"""

import re
from html import unescape

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from inventory.models import Lot, StockLedgerEntry
from manufacturing.models import ProductionOrder


def table(html, table_id):
    """Rows of <table id=...> as lists of cell texts (header row excluded)."""
    match = re.search(rf'<table[^>]*id="{table_id}"[^>]*>(.*?)</table>', html, re.S)
    assert match, f"table {table_id} not found"
    body = re.search(r"<tbody>(.*?)</tbody>", match.group(1), re.S).group(1)
    return [
        [" ".join(unescape(re.sub(r"<[^>]+>", " ", cell)).split()) for cell in cells]
        for cells in (
            re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S)
        )
    ]


@pytest.fixture
def plant(db):
    call_command("seed_production_demo", verbosity=0)
    return ProductionOrder.objects.get(bom__item__code="LAMP-A19")  # M6.3 adds two more orders


def page(client, url, user="demo-warehouse"):
    client.force_login(get_user_model().objects.get(username=user))
    response = client.get(url)
    assert response.status_code == 200, url
    return response.content.decode()


@pytest.mark.django_db
def test_pages_require_login(client, plant):
    lamp = Lot.objects.get(code="LAMP-0001")
    for url in ("/production/", f"/production/{plant.pk}/", f"/lots/{lamp.pk}/genealogy/"):
        response = client.get(url)
        assert response.status_code == 302 and "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_menu_links_to_production(client, plant):
    assert 'href="/production/"' in page(client, "/")


@pytest.mark.django_db
def test_order_list_shows_status_and_net_output(client, plant):
    rows = table(page(client, "/production/"), "orders")
    board, br30 = (
        ProductionOrder.objects.get(bom__item__code=c) for c in ("LED-BOARD", "LAMP-BR30")
    )
    assert rows == [  # newest first; M6.3 adds the LED-BOARD and LAMP-BR30 orders
        [f"#{br30.pk}", "LAMP-BR30 v1", "5", "5", "CLOSED"],
        [f"#{board.pk}", "LED-BOARD v1", "5", "5", "CLOSED"],
        [f"#{plant.pk}", "LAMP-A19 v1", "10", "9", "CLOSED"],
    ]
    assert f'href="/production/{plant.pk}/"' in page(client, "/production/")


@pytest.mark.django_db
def test_order_page_accounts_for_every_material_lot(client, plant):
    html = page(client, f"/production/{plant.pk}/")
    # Lot | item | issued | returned | consumed | scrapped | on line
    assert table(html, "materials") == [
        ["D-0001", "DRIVER", "10", "1", "9", "0", "0"],
        ["L-0002", "LED-CHIP", "30", "0", "28", "2", "0"],
        ["L-0003", "LED-CHIP", "10", "2", "8", "0", "0"],
    ]
    assert "One lamp failed end-of-line test" in html
    assert "LINE-1" in html and "FG" in html


@pytest.mark.django_db
def test_order_page_shows_outputs_with_quality_and_reversal(client, plant):
    rows = table(page(client, f"/production/{plant.pk}/"), "outputs")
    # Lot | net | Quality | note
    assert rows == [
        ["LAMP-0001", "5", "HOLD", ""],
        ["LAMP-0002", "4", "HOLD", ""],
        ["LAMP-0003", "0", "HOLD", "กลับรายการแล้ว"],
    ]


@pytest.mark.django_db
def test_order_history_lists_every_recorded_step(client, plant):
    rows = table(page(client, f"/production/{plant.pk}/"), "history")
    kinds = [row[1] for row in rows]
    assert kinds.count("เบิก") == 3 and kinds.count("คืน") == 2
    assert kinds.count("ใช้") == 4 and kinds.count("scrap") == 1
    assert kinds.count("ผลผลิต") == 3 and kinds.count("กลับรายการ") == 2
    reversal = next(row for row in rows if row[1] == "กลับรายการ" and "LAMP-0003" in row)
    assert "demo-approver" in reversal


@pytest.mark.django_db
def test_genealogy_page_both_directions(client, plant):
    lamp = Lot.objects.get(code="LAMP-0001")
    html = page(client, f"/lots/{lamp.pk}/genealogy/")
    assert table(html, "inputs") == [
        [f"#{plant.pk}", "D-0001", "DRIVER", "9"],
        [f"#{plant.pk}", "L-0002", "LED-CHIP", "28"],
        [f"#{plant.pk}", "L-0003", "LED-CHIP", "8"],
    ]
    chip = Lot.objects.get(code="L-0003")
    html = page(client, f"/lots/{chip.pk}/genealogy/")
    assert table(html, "outputs-of") == [
        [f"#{plant.pk}", "LAMP-0001", "LAMP-A19", "5", "8"],
        [f"#{plant.pk}", "LAMP-0002", "LAMP-A19", "4", "8"],
    ]


@pytest.mark.django_db
def test_order_page_links_lots_to_genealogy(client, plant):
    html = page(client, f"/production/{plant.pk}/")
    lamp = Lot.objects.get(code="LAMP-0001")
    assert f'href="/lots/{lamp.pk}/genealogy/"' in html


@pytest.mark.django_db
def test_read_pages_write_nothing_and_offer_no_forms(client, plant):
    before = StockLedgerEntry.objects.count()
    lamp = Lot.objects.get(code="LAMP-0001")
    for url in ("/production/", f"/production/{plant.pk}/", f"/lots/{lamp.pk}/genealogy/"):
        html = page(client, url, user="demo-production")
        assert '<form method="post"' not in html.split("</nav>", 1)[1]
    assert StockLedgerEntry.objects.count() == before


@pytest.mark.django_db
def test_unknown_order_or_lot_is_404(client, plant):
    client.force_login(get_user_model().objects.get(username="demo-warehouse"))
    assert client.get("/production/999999/").status_code == 404
    assert client.get("/lots/999999/genealogy/").status_code == 404


@pytest.mark.django_db
def test_history_follows_recording_order_even_within_one_transaction(client, plant):
    rows = table(page(client, f"/production/{plant.pk}/"), "history")
    steps = [(row[1], row[2]) for row in rows]
    assert steps == [
        ("เบิก", "L-0002"),
        ("เบิก", "L-0003"),
        ("เบิก", "D-0001"),
        ("ใช้", "L-0002"),
        ("ใช้", "L-0003"),
        ("ใช้", "D-0001"),
        ("ใช้", "L-0003"),
        ("scrap", "L-0002"),
        ("ผลผลิต", "LAMP-0001"),
        ("ผลผลิต", "LAMP-0002"),
        ("ผลผลิต", "LAMP-0003"),
        ("กลับรายการ", "L-0003"),
        ("กลับรายการ", "LAMP-0003"),
        ("คืน", "L-0003"),
        ("คืน", "D-0001"),
    ]


# ---------------------------------------------------------------- PR 2: record forms
# Every form posts through manufacturing.services; buttons follow roles; a hidden request UUID
# makes a double submit post once; command errors are shown and write nothing.

from decimal import Decimal  # noqa: E402
from uuid import uuid4  # noqa: E402

from facilities.models import Warehouse  # noqa: E402
from inventory.services import get_stock_balance  # noqa: E402
from manufacturing.models import (  # noqa: E402
    BillOfMaterials,
    OrderPosting,
    ProductionMaterialMovement,
)


def as_user(client, name):
    client.force_login(get_user_model().objects.get(username=name))
    return client


def wh(code):
    return Warehouse.objects.get(code=code)


def lot(code):
    return Lot.objects.get(code=code)


def submit(client, url, **data):
    return client.post(url, {"request_id": str(uuid4())} | data)


@pytest.fixture
def open_order(client, plant):
    """A new order for 2 x LAMP-A19 created through the screen by demo-production."""
    seeded = list(ProductionOrder.objects.values_list("pk", flat=True))  # M6.3: three orders
    as_user(client, "demo-production")
    response = submit(
        client,
        "/production/new/",
        bom=BillOfMaterials.objects.get(status="ACTIVE", item__code="LAMP-A19").pk,
        quantity="2",
        line_warehouse=wh("LINE-1").pk,
        output_warehouse=wh("FG").pk,
    )
    order = ProductionOrder.objects.exclude(pk__in=seeded).get()
    assert response.status_code == 302 and response["Location"] == f"/production/{order.pk}/"
    return order


def issue(client, order, code, quantity, **extra):
    return submit(
        client,
        f"/production/{order.pk}/issue/",
        lot=lot(code).pk,
        source_warehouse=wh("RM-A").pk,
        quantity=quantity,
        reason="Issue on screen",
        **extra,
    )


@pytest.mark.django_db
def test_new_order_form_offers_active_bom_and_production_warehouses(client, plant):
    html = page(client, "/production/new/", user="demo-production")
    assert "LAMP-A19 v1" in html and "LINE-1" in html and "FG" in html
    as_user(client, "demo-warehouse")
    assert client.get("/production/new/").status_code == 403


@pytest.mark.django_db
def test_buttons_follow_roles_and_order_status(client, open_order, plant):
    production = page(client, f"/production/{open_order.pk}/", user="demo-production")
    for path in ("issue", "return", "consume", "output", "close"):
        assert f'href="/production/{open_order.pk}/{path}/"' in production
    assert f'href="/production/{open_order.pk}/scrap/"' not in production
    approver = page(client, f"/production/{open_order.pk}/", user="demo-approver")
    assert f'href="/production/{open_order.pk}/scrap/"' in approver
    warehouse = page(client, f"/production/{open_order.pk}/", user="demo-warehouse")
    assert f"/production/{open_order.pk}/issue/" not in warehouse
    closed = page(client, f"/production/{plant.pk}/", user="demo-production")
    assert f"/production/{plant.pk}/issue/" not in closed
    assert "/reverse/" not in page(client, f"/production/{plant.pk}/", user="demo-approver")
    assert 'href="/production/new/"' in page(client, "/production/", user="demo-production")


@pytest.mark.django_db
def test_full_flow_through_the_screens(client, open_order):
    o = open_order.pk
    for code, quantity in (("L-0001", "8"), ("D-0001", "2")):
        assert issue(client, open_order, code, quantity).status_code == 302
    consume = dict(reason="Run on screen")
    for code, quantity in (("L-0001", "7"), ("D-0001", "2")):
        response = submit(
            client, f"/production/{o}/consume/", lot=lot(code).pk, quantity=quantity, **consume
        )
        assert response.status_code == 302
    as_user(client, "demo-approver")
    response = submit(
        client,
        f"/production/{o}/scrap/",
        lot=lot("L-0001").pk,
        quantity="1",
        reason="Chip dropped",
    )
    assert response.status_code == 302
    as_user(client, "demo-production")
    for _ in range(2):
        response = submit(
            client,
            f"/production/{o}/output/",
            lot_code="LAMP-1001",
            quantity="1",
            reason="Output on screen",
        )
        assert response.status_code == 302
    second = OrderPosting.objects.filter(order=open_order, kind="OUTPUT").order_by("pk").last()
    as_user(client, "demo-approver")
    detail = page(client, f"/production/{o}/", user="demo-approver")
    assert f'href="/production/{o}/reverse/{second.pk}/"' in detail
    response = submit(client, f"/production/{o}/reverse/{second.pk}/", reason="Lamp failed test")
    assert response.status_code == 302
    as_user(client, "demo-production")
    response = submit(client, f"/production/{o}/close/", shortfall_reason="")
    assert response.status_code == 200 and "shortfall" in response.content.decode()
    response = submit(client, f"/production/{o}/close/", shortfall_reason="One lamp failed")
    assert response.status_code == 302
    open_order.refresh_from_db()
    assert (open_order.status, open_order.shortfall_reason) == ("CLOSED", "One lamp failed")
    assert get_stock_balance(lot=lot("LAMP-1001"), warehouse=wh("FG")) == Decimal("1")
    assert get_stock_balance(lot=lot("L-0001"), warehouse=wh("LINE-1")) == Decimal("0")
    detail = page(client, f"/production/{o}/")
    assert "One lamp failed" in detail
    assert table(detail, "outputs") == [["LAMP-1001", "1", "HOLD", "กลับรายการบางส่วน"]]


@pytest.mark.django_db
def test_double_submit_posts_once(client, open_order):
    key = str(uuid4())
    for _ in range(2):
        assert issue(client, open_order, "L-0001", "4", request_id=key).status_code == 302
    assert ProductionMaterialMovement.objects.filter(order=open_order).count() == 1


@pytest.mark.django_db
def test_command_error_is_shown_and_writes_nothing(client, open_order):
    response = issue(client, open_order, "L-0001", "9")  # BOM allows 4 x 2 = 8 chips
    assert response.status_code == 200
    assert "เกินจำนวนที่อนุญาต" in response.content.decode()
    assert not ProductionMaterialMovement.objects.filter(order=open_order).exists()


@pytest.mark.django_db
def test_close_refusal_names_the_lots_on_the_line(client, open_order):
    issue(client, open_order, "L-0001", "4")
    response = submit(client, f"/production/{open_order.pk}/close/", shortfall_reason="x")
    assert response.status_code == 200
    assert "LED-CHIP lot L-0001 holds 4" in response.content.decode()


@pytest.mark.django_db
def test_forms_refuse_users_without_the_role(client, open_order, plant):
    o = open_order.pk
    as_user(client, "demo-warehouse")
    for path in ("issue", "return", "consume", "output", "close", "scrap"):
        assert client.get(f"/production/{o}/{path}/").status_code == 403
    assert issue(client, open_order, "L-0001", "4").status_code == 403
    as_user(client, "demo-production")
    assert client.get(f"/production/{o}/scrap/").status_code == 403
    posting = OrderPosting.objects.filter(order=plant).first()
    assert client.post(f"/production/{plant.pk}/reverse/{posting.pk}/").status_code == 403
    assert not ProductionMaterialMovement.objects.filter(order=open_order).exists()


@pytest.mark.django_db
def test_closed_order_forms_are_refused(client, plant):
    as_user(client, "demo-production")
    assert client.get(f"/production/{plant.pk}/issue/").status_code == 403


@pytest.mark.django_db
def test_unknown_action_is_404(client, open_order):
    assert client.get(f"/production/{open_order.pk}/explode/").status_code == 404


# ---------------------------------------------------------------- cancel (Issue #86)
# Owner ruling 2026-11-05 (option A): an order with net output cannot be cancelled.


def record_output(client, order, quantity="1"):
    for code, amount in (("L-0001", "8"), ("D-0001", "2")):
        issue(client, order, code, amount)
        submit(
            client,
            f"/production/{order.pk}/consume/",
            lot=lot(code).pk,
            quantity=amount,
            reason="Run on screen",
        )
    return submit(
        client,
        f"/production/{order.pk}/output/",
        lot_code="LAMP-1001",
        quantity=quantity,
        reason="Output on screen",
    )


@pytest.mark.django_db
def test_cancel_button_follows_roles_and_status(client, open_order, plant):
    link = f'href="/production/{open_order.pk}/cancel/"'
    assert link in page(client, f"/production/{open_order.pk}/", user="demo-production")
    assert link not in page(client, f"/production/{open_order.pk}/", user="demo-warehouse")
    closed = page(client, f"/production/{plant.pk}/", user="demo-production")
    assert f"/production/{plant.pk}/cancel/" not in closed


@pytest.mark.django_db
def test_cancel_through_the_screen_then_the_form_is_closed(client, open_order):
    url = f"/production/{open_order.pk}/cancel/"
    assert client.get(url).status_code == 200
    key = str(uuid4())
    response = client.post(url, {"request_id": key, "reason": "Customer withdrew"})
    assert response.status_code == 302 and response["Location"] == f"/production/{open_order.pk}/"
    open_order.refresh_from_db()
    assert (open_order.status, open_order.cancel_reason) == ("CANCELLED", "Customer withdrew")
    # Like "close": once cancelled the order is not OPEN, so a repeated post is a 403, not a
    # second cancellation. The command's own request-key replay is tested in tests/manufacturing.
    repeat = client.post(url, {"request_id": key, "reason": "Customer withdrew"})
    assert repeat.status_code == 403


@pytest.mark.django_db
def test_cancel_with_output_is_refused_and_writes_nothing(client, open_order):
    assert record_output(client, open_order).status_code == 302
    response = submit(client, f"/production/{open_order.pk}/cancel/", reason="Changed mind")
    assert response.status_code == 200
    assert "net output is 1" in response.content.decode()
    open_order.refresh_from_db()
    assert open_order.status == "OPEN"


@pytest.mark.django_db
def test_cancel_refuses_users_without_the_role_and_closed_orders(client, open_order, plant):
    url = f"/production/{open_order.pk}/cancel/"
    as_user(client, "demo-warehouse")
    assert client.get(url).status_code == 403
    assert submit(client, url, reason="No").status_code == 403
    as_user(client, "demo-production")
    assert client.get(f"/production/{plant.pk}/cancel/").status_code == 403
    open_order.refresh_from_db()
    assert open_order.status == "OPEN"
