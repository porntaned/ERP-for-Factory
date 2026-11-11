"""M6.3 (Issue #108): Lot search and the multi-level trace page, over seed_production_demo.

Both pages need login only (owner ruling 2, as the genealogy page) and only read.
"""

from decimal import Decimal
from urllib.parse import quote
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from catalog.models import Item
from facilities.models import Warehouse
from inventory.models import Lot, StockLedgerEntry
from manufacturing.models import ProductionOrder
from quality.services import record_inspection
from tests.quality.helpers import settle

from .test_production_screens import table


@pytest.fixture
def plant(db):
    call_command("seed_production_demo", verbosity=0)
    return ProductionOrder.objects.get(bom__item__code="LAMP-A19")


def login(client, user="demo-warehouse"):
    client.force_login(get_user_model().objects.get(username=user))
    return client


def page(client, url, user="demo-warehouse"):
    response = login(client, user).get(url)
    assert response.status_code == 200, url
    return response.content.decode()


def lot(code, item=None):
    lots = Lot.objects.filter(code=code)
    return (lots.filter(item__code=item) if item else lots).get()


@pytest.mark.django_db
def test_search_and_trace_require_login(client, plant):
    for url in ("/lots/search/", "/lots/search/?code=L-0003", f"/lots/{lot('L-0003').pk}/trace/"):
        response = client.get(url)
        assert response.status_code == 302 and "/accounts/login/" in response["Location"], url


@pytest.mark.django_db
def test_menu_links_to_lot_search(client, plant):
    assert 'href="/lots/search/"' in page(client, "/")


@pytest.mark.django_db
def test_search_with_one_match_redirects_to_its_trace(client, plant):
    for code in ("L-0003", "  L-0003 "):  # surrounding spaces are not part of a code
        response = login(client).get(f"/lots/search/?code={quote(code)}")
        assert response.status_code == 302
        assert response["Location"] == f"/lots/{lot('L-0003').pk}/trace/"


@pytest.mark.django_db
def test_search_with_no_match_says_so(client, plant):
    for code in ("NOPE-1", "l-0003", "ล็อต-๑", "LED😀"):  # exact code; Unicode is just no match
        html = page(client, f"/lots/search/?code={quote(code)}")
        assert "ไม่พบ Lot" in html, code
        assert 'id="lots"' not in html


@pytest.mark.django_db
def test_search_lists_several_matches_by_item(client, plant):
    driver = Item.objects.get(code="DRIVER")
    other = Lot.objects.create(item=driver, code="L-0003")  # same code, another item
    html = page(client, "/lots/search/?code=L-0003")
    assert table(html, "lots") == [["DRIVER", "L-0003"], ["LED-CHIP", "L-0003"]]
    assert f'href="/lots/{other.pk}/trace/"' in html
    assert f'href="/lots/{lot("L-0003", "LED-CHIP").pk}/trace/"' in html


@pytest.mark.django_db
def test_blank_or_invalid_search_shows_the_form_only(client, plant):
    for url in ("/lots/search/", "/lots/search/?code=", "/lots/search/?code=%20%20"):
        html = page(client, url)
        assert 'name="code"' in html and "ไม่พบ Lot" not in html and 'id="lots"' not in html
    html = page(client, "/lots/search/?code=L-0003%00")  # NUL cannot reach PostgreSQL
    assert "รหัส Lot ไม่ถูกต้อง" in html and 'id="lots"' not in html


@pytest.mark.django_db
def test_trace_page_backward_with_positions(client, plant):
    html = page(client, f"/lots/{lot('LAMP-0001').pk}/trace/")
    # level | from Lot | order | Lot | item | consumed | note
    assert table(html, "backward") == [
        ["1", "LAMP-0001", f"#{plant.pk}", "D-0001", "DRIVER", "9", ""],
        ["1", "LAMP-0001", f"#{plant.pk}", "L-0002", "LED-CHIP", "28", ""],
        ["1", "LAMP-0001", f"#{plant.pk}", "L-0003", "LED-CHIP", "8", ""],
    ]
    assert table(html, "forward") == [["ไม่ถูกใช้ผลิตต่อ"]]
    # Lot | item | warehouse | balance | Quality
    assert table(html, "positions") == [
        ["LAMP-0001", "LAMP-A19", "FG", "5", "HOLD"],
        ["D-0001", "DRIVER", "RM-A", "11", "RELEASED"],
        ["L-0002", "LED-CHIP", "ไม่มียอดคงเหลือ"],
        ["L-0003", "LED-CHIP", "RM-A", "12", "RELEASED"],
    ]
    assert f'href="/production/{plant.pk}/"' in html
    assert f'href="/lots/{lot("D-0001").pk}/trace/"' in html
    assert f'href="/lots/{lot("LAMP-0001").pk}/genealogy/"' in html


@pytest.mark.django_db
def test_trace_page_forward_and_rejected_stands_out(client, plant):
    fg = Warehouse.objects.get(code="FG")
    settle()  # M6.2: the history so far stands for earlier commits (see helpers.settle)
    record_inspection(
        lot=lot("LAMP-0002"),
        warehouse=fg,
        result="FAIL",
        sample_quantity=Decimal("1"),
        note="Synthetic end-of-line failure",
        actor=get_user_model().objects.get(username="demo-quality"),
        request_id=uuid4(),
    )
    html = page(client, f"/lots/{lot('L-0003').pk}/trace/")
    assert table(html, "backward") == [["ไม่ได้เป็นผลผลิตของ order ใด"]]
    # level | from Lot | order | output Lot | item | output | consumed of from Lot | note
    assert table(html, "forward") == [
        ["1", "L-0003", f"#{plant.pk}", "LAMP-0001", "LAMP-A19", "5", "8", ""],
        ["1", "L-0003", f"#{plant.pk}", "LAMP-0002", "LAMP-A19", "4", "8", ""],
    ]
    assert table(html, "positions") == [
        ["L-0003", "LED-CHIP", "RM-A", "12", "RELEASED"],
        ["LAMP-0001", "LAMP-A19", "FG", "5", "HOLD"],
        ["LAMP-0002", "LAMP-A19", "FG", "4", "REJECTED"],
    ]
    assert 'class="table-danger" data-disposition="REJECTED"' in html


@pytest.mark.django_db
def test_genealogy_page_links_to_the_trace(client, plant):
    lamp = lot("LAMP-0001")
    assert f'href="/lots/{lamp.pk}/trace/"' in page(client, f"/lots/{lamp.pk}/genealogy/")


@pytest.mark.django_db
def test_trace_and_search_write_nothing_and_offer_no_post_forms(client, plant):
    before = StockLedgerEntry.objects.count()
    for url in (f"/lots/{lot('LAMP-0001').pk}/trace/", "/lots/search/?code=NOPE"):
        html = page(client, url, user="demo-production")
        assert '<form method="post"' not in html.split("</nav>", 1)[1]
    assert StockLedgerEntry.objects.count() == before


@pytest.mark.django_db
def test_unknown_lot_trace_is_404(client, plant):
    assert login(client).get("/lots/999999/trace/").status_code == 404


@pytest.mark.django_db
def test_trace_page_on_the_wip_demo_chain(client, plant):
    lamp = lot("LAMP-BR30-0001")
    order = ProductionOrder.objects.get(bom__item__code="LED-BOARD")
    html = page(client, f"/lots/{lamp.pk}/trace/")
    assert table(html, "backward")[-1] == [
        "2",
        "LED-BOARD-0001",
        f"#{order.pk}",
        "L-0004",
        "LED-CHIP",
        "20",
        "",
    ]
    assert ["L-0004", "LED-CHIP", "RM-A", "10", "RELEASED"] in table(html, "positions")
