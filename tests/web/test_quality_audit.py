"""M6.4 (Issue #113): the QC history page.

Owner ruling 1 (chat, 2026-11-11): a read-only page `/quality/audit/` lists every inspection and
every disposition change, filtered by warehouse and date range, for users with QUALITY or APPROVER
at that warehouse (as `/quality/`). Manager decisions approved with the spec: one combined,
newest-first table; a fixed page size with "older" paging; inclusive local dates.
"""

import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from access_control.models import WarehouseRoleAssignment
from facilities.models import Warehouse
from inventory.models import Lot
from quality.models import LotDispositionEvent, LotInspection
from quality.services import record_inspection, return_rejected_to_hold, transition_lot_disposition
from tests.quality.helpers import settle

from .test_production_screens import table

URL = "/quality/audit/"


@pytest.fixture
def demo(db):
    """seed_production_demo: inspections at RM-A (receipts) and FG (LED-BOARD-0001, FINAL)."""
    call_command("seed_production_demo", verbosity=0)


def user(name):
    return get_user_model().objects.get(username=name)


def login(client, name):
    client.force_login(user(name))
    return client


def wh(code):
    return Warehouse.objects.get(code=code)


def lamp(code="LAMP-0001"):
    return Lot.objects.get(code=code)


def fail_and_return(note="Lens cracked", reason="Re-test after rework", code="LAMP-0001"):
    """demo-quality rejects a lamp at FG; demo-approver returns it to HOLD."""
    settle()  # M6.2: the history so far stands for earlier commits (see helpers.settle)
    inspection = record_inspection(
        lot=lamp(code),
        warehouse=wh("FG"),
        result="FAIL",
        sample_quantity=Decimal("1"),
        note=note,
        actor=user("demo-quality"),
        request_id=uuid4(),
    )
    event = return_rejected_to_hold(
        lot=lamp(code),
        warehouse=wh("FG"),
        actor=user("demo-approver"),
        reason=reason,
        request_id=uuid4(),
    )
    return inspection, event


def rows(client, query=""):
    return table(client.get(URL + query).content.decode(), "audit")


def data_rows(html):
    """(kind, id) of each body row, in page order."""
    return re.findall(r'<tr data-kind="(inspection|event)" data-id="(\d+)"', html)


def expected_count(warehouses):
    return (
        LotInspection.objects.filter(warehouse__in=warehouses).count()
        + LotDispositionEvent.objects.filter(warehouse__in=warehouses).count()
    )


# ---------------------------------------------------------------- access


@pytest.mark.django_db
def test_audit_page_requires_login(client, demo):
    response = client.get(URL)
    assert response.status_code == 302 and response["Location"].startswith("/accounts/login/")


@pytest.mark.django_db
def test_audit_page_requires_quality_or_approver(client, demo):
    assert login(client, "demo-warehouse").get(URL).status_code == 403
    assert 'href="/quality/audit/"' not in client.get("/").content.decode()
    for name in ("demo-quality", "demo-approver"):
        assert login(client, name).get(URL).status_code == 200
        assert "ประวัติ QC" in client.get("/").content.decode()
        assert 'href="/quality/audit/"' in client.get("/").content.decode()


@pytest.mark.django_db
def test_audit_page_shows_only_the_users_warehouses(client, demo):
    fg_only = get_user_model().objects.create(username="qc-fg-only")
    WarehouseRoleAssignment.objects.create(user=fg_only, warehouse=wh("FG"), role="QUALITY")
    html = login(client, "qc-fg-only").get(URL).content.decode()
    found = table(html, "audit")
    assert found and {r[1] for r in found} == {"FG"}
    assert len(found) == expected_count([wh("FG")])
    choices = re.search(r'<select name="warehouse".*?</select>', html, re.S).group(0)
    assert re.findall(r"<option[^>]*>([^<]+)</option>", choices) == ["ทุกคลัง", "FG"]
    # demo-quality (QUALITY at RM-A, RM-B, FG) sees RM-A too
    assert {"RM-A", "FG"} <= {r[1] for r in rows(login(client, "demo-quality"))}


# ---------------------------------------------------------------- rows


@pytest.mark.django_db
def test_both_row_kinds_with_their_fields_newest_first(client, demo):
    inspection, returned = fail_and_return()
    html = login(client, "demo-approver").get(URL).content.decode()
    found = table(html, "audit")
    local = timezone.localtime(returned.created_at).strftime("%Y-%m-%d %H:%M:%S")
    assert found[0] == [
        local,
        "FG",
        "LAMP-0001",
        "เปลี่ยนสถานะ",
        "REJECTED → HOLD",
        "",
        "demo-approver",
        "Re-test after rework",
        "",
    ]
    assert found[1][1:] == [
        "FG",
        "LAMP-0001",
        "เปลี่ยนสถานะ",
        "HOLD → REJECTED",
        "",
        "demo-quality",
        "Lens cracked",
        f"#{inspection.pk}",
    ]
    assert found[2][1:] == [
        "FG",
        "LAMP-0001",
        "ตรวจ FINAL",
        "FAIL",
        "1",
        "demo-quality",
        "Lens cracked",
        f"#{inspection.pk}",
    ]
    assert f'href="/lots/{lamp().pk}/genealogy/"' in html
    assert data_rows(html)[:3] == [
        ("event", str(returned.pk)),
        ("event", str(inspection.event.pk)),
        ("inspection", str(inspection.pk)),
    ]
    times = [r[0] for r in found]
    assert times == sorted(times, reverse=True)
    assert len(found) == expected_count(Warehouse.objects.filter(code__in=["RM-A", "RM-B", "FG"]))


@pytest.mark.django_db
def test_a_disposition_change_without_inspection_is_listed(client, demo):
    """RELEASED -> HOLD (containment) has no inspection: the column stays empty."""
    board = Lot.objects.get(code="LED-BOARD-0001")
    transition_lot_disposition(
        lot=board,
        warehouse=wh("FG"),
        actor=user("demo-quality"),
        expected_disposition="RELEASED",
        target_disposition="HOLD",
        reason="Containment",
        request_id=uuid4(),
    )
    first = rows(login(client, "demo-quality"))[0]
    assert first[1:] == [
        "FG",
        "LED-BOARD-0001",
        "เปลี่ยนสถานะ",
        "RELEASED → HOLD",
        "",
        "demo-quality",
        "Containment",
        "",
    ]


@pytest.mark.django_db
def test_thai_text_and_html_in_a_note_are_escaped(client, demo):
    note = "<script>alert('x')</script> เลนส์แตก & <b>ร้าว</b>"
    fail_and_return(note=note, reason='"><img src=x> ส่งกลับ')
    html = login(client, "demo-quality").get(URL).content.decode()
    assert "<script>alert" not in html and "<b>ร้าว</b>" not in html and "<img src=x>" not in html
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; เลนส์แตก &amp; &lt;b&gt;ร้าว" in html
    assert "&quot;&gt;&lt;img src=x&gt; ส่งกลับ" in html
    found = table(html, "audit")
    assert found[0][7] == '"><img src=x> ส่งกลับ' and found[1][7] == note


@pytest.mark.django_db
def test_page_is_read_only(client, demo):
    login(client, "demo-quality")
    html = client.get(URL).content.decode()
    main = re.search(r"<main.*?</main>", html, re.S).group(0)
    assert 'method="post"' not in main.lower()
    assert 'method="get"' in main.lower()
    assert client.post(URL, {}).status_code == 405


# ---------------------------------------------------------------- filters


@pytest.mark.django_db
def test_warehouse_filter(client, demo):
    fail_and_return()
    login(client, "demo-quality")
    found = rows(client, f"?warehouse={wh('FG').pk}")
    assert found and {r[1] for r in found} == {"FG"}
    assert len(found) == expected_count([wh("FG")])
    rm_a = rows(client, f"?warehouse={wh('RM-A').pk}")
    assert rm_a and {r[1] for r in rm_a} == {"RM-A"}


@pytest.mark.django_db
@pytest.mark.parametrize("value", ["LINE-1", "999999", "abc", "-1"])
def test_other_or_invalid_warehouse_shows_a_message(client, demo, value):
    """demo-quality has no QUALITY or APPROVER at LINE-1, where LED-BOARD-0001 was output."""
    line = wh("LINE-1")
    WarehouseRoleAssignment.objects.create(
        user=get_user_model().objects.create(username="qc-line"), warehouse=line, role="QUALITY"
    )
    if value == "LINE-1":
        value = str(line.pk)
    response = login(client, "demo-quality").get(f"{URL}?warehouse={value}")
    html = response.content.decode()
    assert response.status_code == 200
    assert "ตัวกรองไม่ถูกต้อง" in html
    assert data_rows(html) == []


def put_at(record, moment):
    """Place a synthetic record at a chosen time; the append-only triggers are off only inside
    this test's transaction, which is rolled back."""
    settle()
    table_name = type(record)._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {table_name} DISABLE TRIGGER USER")
        cursor.execute(
            f"UPDATE {table_name} SET created_at = %s WHERE id = %s",  # noqa: S608
            [moment, record.pk],
        )
    settle()  # the UPDATE queued deferred foreign-key checks; fire them before re-enabling
    with connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {table_name} ENABLE TRIGGER USER")


@pytest.mark.django_db
def test_date_filter_uses_inclusive_local_dates(client, demo):
    inspection, returned = fail_and_return()
    # Asia/Bangkok is UTC+7: 2026-11-10 17:30 UTC is 2026-11-11 00:30 local.
    put_at(inspection, datetime(2026, 11, 10, 17, 30, tzinfo=UTC))
    put_at(inspection.event, datetime(2026, 11, 11, 16, 59, 59, tzinfo=UTC))  # 23:59:59 local
    put_at(returned, datetime(2026, 11, 11, 17, 0, tzinfo=UTC))  # 2026-11-12 00:00 local
    login(client, "demo-quality")
    fg = wh("FG").pk

    def ids(query):
        return data_rows(client.get(f"{URL}?warehouse={fg}&{query}").content.decode())

    inspected, failed, back = (
        ("inspection", str(inspection.pk)),
        ("event", str(inspection.event.pk)),
        ("event", str(returned.pk)),
    )
    # Other synthetic rows were written today (real time), so only these three are checked.
    one_day = ids("date_from=2026-11-11&date_to=2026-11-11")
    assert inspected in one_day and failed in one_day and back not in one_day
    assert back in ids("date_from=2026-11-12") and inspected not in ids("date_from=2026-11-12")
    assert inspected not in ids("date_to=2026-11-10") and failed not in ids("date_to=2026-11-10")
    assert failed in ids("date_to=2026-11-11") and back not in ids("date_to=2026-11-11")
    today = timezone.localdate()
    assert len(ids(f"date_from={today - timedelta(days=1)}")) >= 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query",
    [
        "date_from=2026-13-40",
        "date_to=yesterday",
        "date_from=2026-11-12&date_to=2026-11-11",
        "page=0",
        "page=abc",
        "page=99999999999999999999999",
        "date_from=99999-01-01",
    ],
)
def test_invalid_filters_show_a_message(client, demo, query):
    response = login(client, "demo-quality").get(f"{URL}?{query}")
    assert response.status_code == 200
    html = response.content.decode()
    assert "ตัวกรองไม่ถูกต้อง" in html and data_rows(html) == []


@pytest.mark.django_db
def test_extreme_valid_dates_do_not_fail(client, demo):
    login(client, "demo-quality")
    for query in ("date_from=0001-01-01", f"date_to={date.max}", f"date_from={date.max}"):
        response = client.get(f"{URL}?{query}")
        assert response.status_code == 200
        assert "ตัวกรองไม่ถูกต้อง" not in response.content.decode()


# ---------------------------------------------------------------- paging and query count


def more_history(cycles):
    """Each cycle: PASS inspection (inspection + event), then RELEASED -> HOLD (event)."""
    lot, fg, qc = lamp(), wh("FG"), user("demo-quality")
    for n in range(cycles):
        record_inspection(
            lot=lot,
            warehouse=fg,
            result="PASS",
            sample_quantity=Decimal("1"),
            note=f"Cycle {n}",
            actor=qc,
            request_id=uuid4(),
        )
        transition_lot_disposition(
            lot=lot,
            warehouse=fg,
            actor=qc,
            expected_disposition="RELEASED",
            target_disposition="HOLD",
            reason=f"Containment {n}",
            request_id=uuid4(),
        )


@pytest.mark.django_db
def test_older_paging_walks_every_row_once(client, demo, monkeypatch):
    from demo import quality_views

    monkeypatch.setattr(quality_views, "AUDIT_PAGE_SIZE", 4)
    more_history(3)
    login(client, "demo-quality")
    fg = wh("FG").pk
    seen, page, pages = [], 1, 0
    while True:
        html = client.get(f"{URL}?warehouse={fg}&page={page}").content.decode()
        found = data_rows(html)
        assert len(found) <= 4
        seen += found
        pages += 1
        older = re.search(r'<a [^>]*data-action="older"[^>]*href="([^"]+)"', html)
        if not older:
            break
        assert f"warehouse={fg}" in older.group(1) and f"page={page + 1}" in older.group(1)
        page += 1
    assert len(seen) == len(set(seen)) == expected_count([wh("FG")])
    assert pages == -(-len(seen) // 4)
    beyond = client.get(f"{URL}?warehouse={fg}&page={pages + 5}").content.decode()
    assert data_rows(beyond) == [] and "ไม่มีรายการ" in beyond


@pytest.mark.django_db
def test_query_count_does_not_grow_with_history(client, demo, django_assert_max_num_queries):
    login(client, "demo-quality")
    client.get(URL)  # warm the session and content types
    with django_assert_max_num_queries(12) as small:
        assert client.get(URL).status_code == 200
    more_history(40)  # 120 more rows, more than two pages
    with django_assert_max_num_queries(12) as large:
        html = client.get(URL).content.decode()
    assert len(data_rows(html)) == 50 and 'data-action="older"' in html
    assert len(large.captured_queries) == len(small.captured_queries)
    with django_assert_max_num_queries(12):
        client.get(f"{URL}?warehouse={wh('FG').pk}&date_from=2026-01-01&page=2")
