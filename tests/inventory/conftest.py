from collections.abc import Callable
from decimal import Decimal
from importlib import import_module
from typing import Any

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model


@pytest.fixture
def inventory_model() -> Callable[[str], Any]:
    def resolve(name: str) -> Any:
        try:
            return apps.get_model("inventory", name)
        except LookupError:
            pytest.fail(
                f"inventory.{name} is not registered; expected RED until Issue #7 is implemented",
                pytrace=False,
            )

    return resolve


@pytest.fixture
def organization(db: None) -> Any:
    organization_model = apps.get_model("facilities", "Organization")
    return organization_model.objects.create(code="ACME", display_name="ACME")


@pytest.fixture
def each_uom(db: None) -> Any:
    uom_model = apps.get_model("catalog", "UnitOfMeasure")
    return uom_model.objects.create(code="EA", display_name="Each")


@pytest.fixture
def raw_item(organization: Any, each_uom: Any) -> Any:
    item_model = apps.get_model("catalog", "Item")
    return item_model.objects.create(
        organization=organization,
        code="LED-CHIP",
        display_name="LED chip",
        item_type="RAW",
        base_uom=each_uom,
    )


@pytest.fixture
def ledger_contract():
    try:
        model = apps.get_model("inventory", "StockLedgerEntry")
        balance = import_module("inventory.services").get_stock_balance
    except LookupError, ModuleNotFoundError, AttributeError:
        pytest.fail("M4.1 ledger contract absent: controlled Issue #26 RED", pytrace=False)
    return model, balance


@pytest.fixture
def ledger_scope(db):
    organization = apps.get_model("facilities", "Organization").objects.create(
        code="LEDGER", display_name="Synthetic"
    )
    plant = apps.get_model("facilities", "Plant").objects.create(
        organization=organization, code="P", display_name="Synthetic"
    )
    warehouse_model = apps.get_model("facilities", "Warehouse")
    warehouse = warehouse_model.objects.create(plant=plant, code="A", display_name="A")
    other = warehouse_model.objects.create(plant=plant, code="B", display_name="B")
    uom = apps.get_model("catalog", "UnitOfMeasure").objects.create(
        code="KG", display_name="Kilogram"
    )
    item = apps.get_model("catalog", "Item").objects.create(
        organization=organization,
        code="RAW",
        display_name="Synthetic",
        item_type="RAW",
        base_uom=uom,
    )
    lot = apps.get_model("inventory", "Lot").objects.create(item=item, code="L1")
    second = apps.get_model("inventory", "Lot").objects.create(item=item, code="L2")
    actor = get_user_model().objects.create(username="synthetic-ledger")
    actor.set_unusable_password()
    actor.save()
    return dict(
        lot=lot,
        warehouse=warehouse,
        other=other,
        second=second,
        actor=actor,
        item=item,
        uom=uom,
        plant=plant,
        organization=organization,
    )


@pytest.fixture
def append_entry(ledger_contract, ledger_scope):
    model, _ = ledger_contract

    def append(delta="10", **overrides):
        values = dict(
            lot=ledger_scope["lot"],
            warehouse=ledger_scope["warehouse"],
            actor=ledger_scope["actor"],
            quantity_delta=Decimal(delta),
            reason="Synthetic ledger verification — ทดสอบ",
        )
        values.update(overrides)
        return model.objects.create(**values)

    return append
