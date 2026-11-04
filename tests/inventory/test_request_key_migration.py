"""M4.4.1 migrations: backfill existing keys; abort with no partial state on cross-command reuse."""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor

from inventory.models import RequestKey, StockLedgerEntry, StockReceipt, StockTransfer
from inventory.services import receive_stock
from quality.models import LotDispositionEvent

from .test_atomic_transfer import post
from .test_atomic_transfer import transfer_scope as transfer_scope  # noqa: F401

# Targets before M4.4.1: quality 0004 and inventory 0007 are unapplied.
PRE = [("inventory", "0006_transfer_request_id"), ("quality", "0003_authoritative_event_identity")]


def migrate_to(targets):
    executor = MigrationExecutor(connection)
    executor.migrate(targets)


def latest():
    return MigrationExecutor(connection).loader.graph.leaf_nodes()


# Both tests run inside one rolled-back transaction: DDL and data from a reverse/forward
# migration round trip (or a failed upgrade) disappear at the end, so the shared database
# is never left with synthetic cross-command duplicates that block later restores.


@pytest.mark.django_db
def test_backfill_registers_each_existing_key_under_its_command(transfer_scope):
    scope = transfer_scope
    receipt_key, transfer_key = uuid4(), uuid4()
    receive_stock(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=scope["actor"],
        quantity=Decimal("5"),
        reason="Synthetic receipt",
        request_id=receipt_key,
    )
    post(scope, request_id=transfer_key)
    disposition_keys = set(LotDispositionEvent.objects.values_list("request_id", flat=True))
    assert disposition_keys  # transfer_scope released the destination through the service

    migrate_to(PRE)
    migrate_to(latest())

    rows = set(RequestKey.objects.values_list("request_id", "command"))
    assert (receipt_key, "RECEIPT") in rows
    assert (transfer_key, "TRANSFER") in rows
    assert {(k, "DISPOSITION") for k in disposition_keys} <= rows
    assert StockReceipt.objects.count() == 1 and StockTransfer.objects.count() == 1


@pytest.mark.django_db
def test_upgrade_aborts_when_one_uuid_was_used_by_two_commands(transfer_scope):
    scope = transfer_scope
    shared = uuid4()
    migrate_to(PRE)
    debit = StockLedgerEntry.objects.create(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=scope["actor"],
        quantity_delta=Decimal("-1"),
        reason="Synthetic pre-upgrade",
    )
    credit = StockLedgerEntry.objects.create(
        lot=scope["lot"],
        warehouse=scope["other"],
        actor=scope["actor"],
        quantity_delta=Decimal("1"),
        reason="Synthetic pre-upgrade",
    )
    receipt_entry = StockLedgerEntry.objects.create(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=scope["actor"],
        quantity_delta=Decimal("2"),
        reason="Synthetic pre-upgrade",
    )
    StockReceipt.objects.create(request_id=shared, ledger_entry=receipt_entry)
    StockTransfer.objects.create(source_entry=debit, destination_entry=credit, request_id=shared)

    with pytest.raises(DatabaseError):
        migrate_to(latest())

    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('inventory_requestkey')")
        assert cursor.fetchone()[0] is None


def applied(app, name):
    from django.db.migrations.recorder import MigrationRecorder

    return MigrationRecorder(connection).migration_qs.filter(app=app, name=name).exists()


@pytest.mark.django_db
def test_quality_backfill_aborts_when_a_disposition_key_was_used_by_a_receipt(transfer_scope):
    scope = transfer_scope
    shared = uuid4()
    migrate_to(PRE)
    entry = StockLedgerEntry.objects.create(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=scope["actor"],
        quantity_delta=Decimal("2"),
        reason="Synthetic pre-upgrade",
    )
    StockReceipt.objects.create(request_id=shared, ledger_entry=entry)
    LotDispositionEvent.objects.create(
        lot=scope["lot"],
        warehouse=scope["other"],
        actor=scope["actor"],
        request_id=shared,
        from_disposition="HOLD",
        to_disposition="RELEASED",
        reason="Synthetic pre-upgrade",
    )
    with pytest.raises(DatabaseError, match="request_id"):
        migrate_to(latest())
    # Migrations are atomic one by one: 0007 (receipts/transfers) applied, 0004 did not.
    assert applied("inventory", "0007_request_key_registry")
    assert not applied("quality", "0004_request_key_registration")
    assert not RequestKey.objects.filter(command="DISPOSITION").exists()


@pytest.mark.django_db
def test_legacy_null_transfer_survives_upgrade_unregistered(transfer_scope):
    from .test_transfer_history import entries

    migrate_to([("inventory", "0006_transfer_request_id")])
    debit, credit = entries(transfer_scope)
    legacy = StockTransfer.objects.create(source_entry=debit, destination_entry=credit)
    migrate_to(latest())
    legacy.refresh_from_db()
    assert legacy.request_id is None
    keyed = set(StockTransfer.objects.exclude(request_id=None).values_list("request_id", flat=True))
    assert (
        set(RequestKey.objects.filter(command="TRANSFER").values_list("request_id", flat=True))
        == keyed
    )


@pytest.mark.django_db
def test_require_key_constraint_reverses_and_reapplies(transfer_scope):
    from django.db import IntegrityError, transaction

    from .test_transfer_history import entries

    migrate_to([("inventory", "0007_request_key_registry")])
    debit, credit = entries(transfer_scope)
    StockTransfer.objects.create(source_entry=debit, destination_entry=credit)  # allowed
    migrate_to(latest())
    debit, credit = entries(transfer_scope)
    with pytest.raises(IntegrityError, match="transfer_request_id_required"), transaction.atomic():
        StockTransfer.objects.create(source_entry=debit, destination_entry=credit)
