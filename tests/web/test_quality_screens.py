"""M6.1 PR 2 (Issue #96): Quality inspection screens.

A Quality page lists HOLD and REJECTED Lot-Warehouses with stock at the warehouses where the user
holds QUALITY or APPROVER. QUALITY records PASS/FAIL through record_inspection; APPROVER returns a
REJECTED pair to HOLD through return_rejected_to_hold. The commands keep enforcing authority.
Owner decisions (chat, 2026-11-06): design approved; demo-quality gets QUALITY and demo-approver
gets APPROVER at FG so FINAL inspection can be shown.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from access_control.models import WarehouseRoleAssignment
from facilities.models import Warehouse
from inventory.models import Lot
from quality.models import LotInspection
from quality.services import get_lot_disposition

from .test_production_screens import table


@pytest.fixture
def fg(db):
    """seed_production_demo leaves LAMP-0001 (5) and LAMP-0002 (4) HOLD at FG."""
    call_command("seed_production_demo", verbosity=0)
    return Warehouse.objects.get(code="FG")


def login(client, name):
    client.force_login(get_user_model().objects.get(username=name))
    return client


def lamp(code="LAMP-0001"):
    return Lot.objects.get(code=code)


def inspect(client, fg, *, result="PASS", sample="1", code="LAMP-0001", key=None):
    return client.post(
        "/quality/inspect/",
        {
            "lot": lamp(code).pk,
            "warehouse": fg.pk,
            "result": result,
            "sample_quantity": sample,
            "note": "Synthetic end-of-line check",
            "request_id": str(key or uuid4()),
        },
        follow=True,
    )


def give_back(client, fg, *, code="LAMP-0001"):
    return client.post(
        "/quality/return/",
        {
            "lot": lamp(code).pk,
            "warehouse": fg.pk,
            "reason": "Re-test after rework",
            "request_id": str(uuid4()),
        },
        follow=True,
    )


def state(fg, code="LAMP-0001"):
    return get_lot_disposition(lot=lamp(code), warehouse=fg)


# ---------------------------------------------------------------- seed grants


@pytest.mark.django_db
def test_seed_grants_quality_and_approver_at_fg(fg):
    roles = set(
        WarehouseRoleAssignment.objects.filter(warehouse=fg).values_list("user__username", "role")
    )
    assert {("demo-quality", "QUALITY"), ("demo-approver", "APPROVER")} <= roles


# ---------------------------------------------------------------- list page


@pytest.mark.django_db
def test_quality_page_lists_hold_pairs_with_stock(client, fg):
    html = login(client, "demo-quality").get("/quality/").content.decode()
    rows = table(html, "pairs")
    assert ["FG", "LAMP-0001", "LAMP-A19", "5", "HOLD"] == rows[0][:5]
    assert any(r[:5] == ["FG", "LAMP-0002", "LAMP-A19", "4", "HOLD"] for r in rows)
    assert not any("L-0001" in r for r in rows)  # RELEASED pairs are not listed
    assert 'data-action="inspect"' in html


@pytest.mark.django_db
def test_quality_page_requires_quality_or_approver(client, fg):
    assert login(client, "demo-warehouse").get("/quality/").status_code == 403
    assert client.get("/").content.decode().count('href="/quality/"') == 0
    nav = login(client, "demo-quality").get("/").content.decode()
    assert 'href="/quality/"' in nav


@pytest.mark.django_db
def test_approver_sees_no_inspect_form(client, fg):
    html = login(client, "demo-approver").get("/quality/").content.decode()
    assert table(html, "pairs") and 'data-action="inspect"' not in html


@pytest.mark.django_db
def test_quality_page_requires_login(client, fg):
    response = client.get("/quality/")
    assert response.status_code == 302 and response["Location"].startswith("/accounts/login/")


# ---------------------------------------------------------------- inspect


@pytest.mark.django_db
def test_pass_releases_through_a_final_inspection(client, fg):
    response = inspect(login(client, "demo-quality"), fg)
    assert response.redirect_chain[-1][0] == "/quality/"
    assert state(fg) == "RELEASED"
    inspection = LotInspection.objects.get(lot=lamp(), warehouse=fg)
    assert (inspection.kind, inspection.result, inspection.sample_quantity) == (
        "FINAL",
        "PASS",
        Decimal("1"),
    )
    assert inspection.inspector.username == "demo-quality"


@pytest.mark.django_db
def test_fail_rejects_and_only_an_approver_returns_to_hold(client, fg):
    inspect(login(client, "demo-quality"), fg, result="FAIL")
    assert state(fg) == "REJECTED"
    quality_html = client.get("/quality/").content.decode()
    assert 'data-action="return-hold"' not in quality_html
    refused = give_back(client, fg)
    assert state(fg) == "REJECTED" and "ไม่มีสิทธิ์" in refused.content.decode()
    approver_html = login(client, "demo-approver").get("/quality/").content.decode()
    assert 'data-action="return-hold"' in approver_html
    give_back(client, fg)
    assert state(fg) == "HOLD"


@pytest.mark.django_db
def test_inspection_errors_become_messages_and_write_nothing(client, fg):
    login(client, "demo-quality")
    too_many = inspect(client, fg, sample="6")
    assert "ข้อมูลไม่ถูกต้อง" in too_many.content.decode()
    blank = client.post(
        "/quality/inspect/",
        {
            "lot": lamp().pk,
            "warehouse": fg.pk,
            "result": "PASS",
            "sample_quantity": "1",
            "note": "  ",
            "request_id": str(uuid4()),
        },
        follow=True,
    )
    assert blank.status_code == 200
    assert state(fg) == "HOLD" and not LotInspection.objects.filter(warehouse=fg).exists()


@pytest.mark.django_db
def test_double_submit_records_one_inspection(client, fg):
    key = uuid4()
    login(client, "demo-quality")
    inspect(client, fg, key=key)
    inspect(client, fg, key=key)
    assert LotInspection.objects.filter(warehouse=fg).count() == 1


@pytest.mark.django_db
def test_forms_are_post_only(client, fg):
    login(client, "demo-quality")
    assert client.get("/quality/inspect/").status_code == 405
    assert client.get("/quality/return/").status_code == 405


# ---------------------------------------------------------------- history on genealogy


@pytest.mark.django_db
def test_genealogy_page_shows_inspection_history(client, fg):
    login(client, "demo-quality")
    inspect(client, fg, result="FAIL")
    login(client, "demo-approver")
    give_back(client, fg)
    html = client.get(f"/lots/{lamp().pk}/genealogy/").content.decode()
    rows = table(html, "inspections")
    assert any(r[:4] == ["FG", "FINAL", "FAIL", "1"] and "demo-quality" in r for r in rows)
    events = table(html, "dispositions")
    assert [r[1:3] for r in events if r[0] == "FG"][-2:] == [
        ["HOLD", "REJECTED"],
        ["REJECTED", "HOLD"],
    ]
