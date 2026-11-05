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
    return ProductionOrder.objects.get()


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
    assert rows == [[f"#{plant.pk}", "LAMP-A19 v1", "10", "9", "CLOSED"]]
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
