"""Web scaffold and synthetic demo data: read-only overview, read-only admin, seed command."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from facilities.models import Warehouse
from inventory.models import RequestKey, StockLedgerEntry, StockReceipt
from inventory.services import get_stock_balance
from quality.models import LotDispositionEvent
from quality.services import get_lot_disposition


@pytest.fixture
def viewer(db):
    return get_user_model().objects.create_user(username="viewer", password=None)


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(username="root-demo", password=None)


@pytest.mark.django_db
def test_overview_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302 and "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_seed_creates_pilot_factory_through_real_commands(viewer):
    call_command("seed_demo", verbosity=0)
    assert set(Warehouse.objects.values_list("code", flat=True)) == {"RM-A", "RM-B", "LINE-1", "FG"}
    lot = StockReceipt.objects.get().ledger_entry.lot
    rm_a = Warehouse.objects.get(code="RM-A")
    assert get_stock_balance(lot=lot, warehouse=rm_a) == Decimal("100")
    assert get_lot_disposition(lot=lot, warehouse=rm_a) == "RELEASED"
    assert set(RequestKey.objects.values_list("command", flat=True)) == {
        "RECEIPT",
        "DISPOSITION",
        "BOM_DRAFT",
        "BOM_APPROVE",
    }


@pytest.mark.django_db
def test_seed_is_idempotent(viewer):
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)
    assert StockReceipt.objects.count() == 1
    assert StockLedgerEntry.objects.count() == 1
    assert LotDispositionEvent.objects.count() == 1
    assert Warehouse.objects.count() == 4


@pytest.mark.django_db
def test_overview_shows_balance_and_quality(client, viewer):
    call_command("seed_demo", verbosity=0)
    client.force_login(viewer)
    response = client.get("/")
    body = response.content.decode()
    assert response.status_code == 200
    assert "L-0001" in body and "RM-A" in body and ">100<" in body and "RELEASED" in body


@pytest.mark.django_db
def test_overview_is_empty_without_data(client, viewer):
    client.force_login(viewer)
    assert "seed_demo" in client.get("/").content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model", ["inventory/stockledgerentry", "quality/lotdispositionevent", "facilities/warehouse"]
)
def test_admin_is_read_only(client, superuser, model):
    call_command("seed_demo", verbosity=0)
    client.force_login(superuser)
    assert client.get(f"/admin/{model}/").status_code == 200
    assert client.get(f"/admin/{model}/add/").status_code == 403
    obj_id = {
        "inventory/stockledgerentry": StockLedgerEntry.objects.get().pk,
        "quality/lotdispositionevent": LotDispositionEvent.objects.get().pk,
        "facilities/warehouse": Warehouse.objects.get(code="FG").pk,
    }[model]
    assert client.post(f"/admin/{model}/{obj_id}/delete/", {"post": "yes"}).status_code == 403


@pytest.mark.django_db(transaction=True)
def test_seed_reset_flushes_then_recreates(viewer):
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", reset=True, verbosity=0)
    assert StockReceipt.objects.count() == 1 and Warehouse.objects.count() == 4
    assert not get_user_model().objects.filter(username="viewer").exists()
