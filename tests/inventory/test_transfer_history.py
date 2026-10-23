"""Typed transfer evidence, actual database invariants, and ownership races."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError

from facilities.models import Organization, Plant, Warehouse
from inventory.models import StockLedgerEntry, StockReceipt, StockTransfer

from .test_atomic_transfer import balances, post
from .test_atomic_transfer import transfer_scope as transfer_scope
from .test_stock_receipt_concurrency import blocked_action


def entries(scope, **credit_changes):
    payload = dict(lot=scope["lot"], actor=scope["actor"], reason="  โอน LED — synthetic  ")
    debit = StockLedgerEntry.objects.create(
        **payload, warehouse=scope["warehouse"], quantity_delta=Decimal("-10")
    )
    credit = StockLedgerEntry.objects.create(
        **(payload | dict(warehouse=scope["other"], quantity_delta=Decimal("10")) | credit_changes)
    )
    return debit, credit


@pytest.mark.django_db
def test_command_creates_traceable_immutable_history_without_changing_return_contract(
    transfer_scope,
):
    scope = transfer_scope
    debit, credit = post(scope)
    history = StockTransfer.objects.select_related("source_entry", "destination_entry").get()
    assert history.pk == debit.transfer_out.pk == credit.transfer_in.pk
    assert history.source_entry_id == debit.pk
    assert history.destination_entry_id == credit.pk
    assert history.source_entry.actor_id == history.destination_entry.actor_id == scope["actor"].pk
    assert (
        history.source_entry.reason == history.destination_entry.reason == "  โอน LED — synthetic  "
    )
    assert history.source_entry.lot_id == history.destination_entry.lot_id == scope["lot"].pk
    assert history.source_entry.quantity_delta + history.destination_entry.quantity_delta == 0
    assert history.created_at is not None
    assert balances(scope) == (Decimal("70"), Decimal("30.000001"))


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mismatch", ["quantity", "lot", "actor", "reason", "same_warehouse", "plant"]
)
def test_database_rejects_inconsistent_pair(transfer_scope, mismatch):
    scope = transfer_scope
    changes = {}
    if mismatch == "quantity":
        changes["quantity_delta"] = Decimal("11")
    elif mismatch == "lot":
        changes["lot"] = scope["second"]
    elif mismatch == "actor":
        changes["actor"] = get_user_model().objects.create(username="other-history-actor")
    elif mismatch == "reason":
        changes["reason"] = "Different reason"
    elif mismatch == "same_warehouse":
        changes["warehouse"] = scope["warehouse"]
    else:
        plant = Plant.objects.create(
            organization=scope["organization"], code="P2", display_name="P2"
        )
        changes["warehouse"] = Warehouse.objects.create(plant=plant, code="B", display_name="B")
    debit, credit = entries(scope, **changes)
    with pytest.raises(IntegrityError), transaction.atomic():
        StockTransfer.objects.create(source_entry=debit, destination_entry=credit)
    assert StockTransfer.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("invalid", ["same", "swapped", "missing_source", "missing_destination"])
def test_database_rejects_wrong_or_missing_entry_roles(transfer_scope, invalid):
    debit, credit = entries(transfer_scope)
    source, destination = debit.pk, credit.pk
    if invalid == "same":
        source = destination
    elif invalid == "swapped":
        source, destination = destination, source
    elif invalid == "missing_source":
        source = 999999999
    else:
        destination = 999999999
    with pytest.raises(IntegrityError), transaction.atomic():
        StockTransfer.objects.create(source_entry_id=source, destination_entry_id=destination)


@pytest.mark.django_db
@pytest.mark.parametrize("reuse", ["source", "destination", "both"])
def test_ledger_entry_cannot_belong_to_two_transfers(transfer_scope, reuse):
    debit, credit = entries(transfer_scope)
    other_debit, other_credit = entries(transfer_scope)
    StockTransfer.objects.create(source_entry=debit, destination_entry=credit)
    with pytest.raises(IntegrityError), transaction.atomic():
        StockTransfer.objects.create(
            source_entry=debit if reuse != "destination" else other_debit,
            destination_entry=credit if reuse != "source" else other_credit,
        )
    assert StockTransfer.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("receipt_first", [False, True])
def test_receipt_and_transfer_cannot_claim_the_same_credit(transfer_scope, receipt_first):
    debit, credit = entries(transfer_scope)

    def receipt():
        return StockReceipt.objects.create(ledger_entry=credit, request_id=uuid4())

    def transfer():
        return StockTransfer.objects.create(source_entry=debit, destination_entry=credit)

    (receipt if receipt_first else transfer)()
    with pytest.raises(IntegrityError), transaction.atomic():
        (transfer if receipt_first else receipt)()
    assert StockReceipt.objects.count() == int(receipt_first)
    assert StockTransfer.objects.count() == int(not receipt_first)


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["source_entry_id", "destination_entry_id", "created_at", "id"])
def test_history_update_is_rejected_even_if_noop(transfer_scope, field):
    debit, _ = post(transfer_scope)
    history = debit.transfer_out
    with pytest.raises(IntegrityError), transaction.atomic():
        StockTransfer.objects.filter(pk=history.pk).update(**{field: getattr(history, field)})


@pytest.mark.django_db
def test_history_delete_and_linked_ledger_delete_are_protected(transfer_scope):
    debit, credit = post(transfer_scope)
    with pytest.raises(IntegrityError), transaction.atomic():
        StockTransfer.objects.all().delete()
    for entry in (debit, credit):
        with pytest.raises(ProtectedError):
            entry.delete()
    assert StockTransfer.objects.count() == 1


@pytest.mark.django_db
def test_database_authors_identity_and_time(transfer_scope):
    debit, credit = entries(transfer_scope)
    with pytest.raises(DatabaseError, match="GENERATED ALWAYS"), transaction.atomic():
        StockTransfer.objects.create(pk=999, source_entry=debit, destination_entry=credit)
    supplied = datetime(2000, 1, 1, tzinfo=timezone.utc)
    history = StockTransfer.objects.create(
        source_entry=debit, destination_entry=credit, created_at=supplied
    )
    history.refresh_from_db()
    assert history.created_at > supplied


@pytest.mark.django_db
def test_real_history_insert_failure_rolls_back_both_entries_and_keeps_outer_usable(transfer_scope):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE FUNCTION pg_temp.reject_transfer_history() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic history failure' USING ERRCODE='23514'; END; $$;
            CREATE TRIGGER test_reject_transfer_history BEFORE INSERT ON inventory_stocktransfer
            FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_transfer_history();
        """)
    try:
        with transaction.atomic():
            with pytest.raises(IntegrityError, match="synthetic history failure"):
                post(transfer_scope)
            assert StockLedgerEntry.objects.count() == 1
            assert StockTransfer.objects.count() == 0
            assert balances(transfer_scope) == (Decimal("100.000001"), 0)
            Organization.objects.create(code="CONTINUE", display_name="Outer still usable")
        assert Organization.objects.filter(code="CONTINUE").exists()
    finally:
        with connection.cursor() as cursor:
            cursor.execute("DROP TRIGGER test_reject_transfer_history ON inventory_stocktransfer")
            cursor.execute("DROP FUNCTION pg_temp.reject_transfer_history()")


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("receipt_first", [False, True])
def test_concurrent_receipt_transfer_classification_has_one_winner(transfer_scope, receipt_first):
    debit, credit = entries(transfer_scope)

    def receipt():
        return StockReceipt.objects.create(ledger_entry=credit, request_id=uuid4())

    def transfer():
        return StockTransfer.objects.create(source_entry=debit, destination_entry=credit)

    _, outcome = blocked_action(
        receipt if receipt_first else transfer, transfer if receipt_first else receipt
    )
    assert outcome[0] == "IntegrityError", outcome
    assert StockReceipt.objects.count() == int(receipt_first)
    assert StockTransfer.objects.count() == int(not receipt_first)


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_pair_has_one_history(transfer_scope):
    debit, credit = entries(transfer_scope)

    def link():
        return StockTransfer.objects.create(source_entry=debit, destination_entry=credit)

    _, outcome = blocked_action(link, link)
    assert outcome[0] == "IntegrityError", outcome
    assert StockTransfer.objects.count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("receipt", [False, True])
def test_ownership_links_reject_stale_snapshot_isolation(transfer_scope, receipt):
    debit, credit = entries(transfer_scope)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        with pytest.raises(IntegrityError), transaction.atomic():
            if receipt:
                StockReceipt.objects.create(ledger_entry=credit, request_id=uuid4())
            else:
                StockTransfer.objects.create(source_entry=debit, destination_entry=credit)


@pytest.mark.django_db(transaction=True)
def test_upgrade_preserves_unlinked_history_without_inventing_pairs(transfer_scope):
    executor = MigrationExecutor(connection)
    try:
        executor.migrate([("inventory", "0004_stock_receipt")])
        debit, credit = entries(transfer_scope)
        expected = list(StockLedgerEntry.objects.order_by("id").values())
        receipt = StockReceipt.objects.create(ledger_entry=credit, request_id=uuid4())
        executor = MigrationExecutor(connection)
        executor.migrate([("inventory", "0005_stock_transfer")])
        assert list(StockLedgerEntry.objects.order_by("id").values()) == expected
        assert StockTransfer.objects.count() == 0
        assert StockReceipt.objects.get(pk=receipt.pk).ledger_entry_id == credit.pk
        with pytest.raises(IntegrityError), transaction.atomic():
            StockTransfer.objects.create(source_entry=debit, destination_entry=credit)
    finally:
        MigrationExecutor(connection).migrate([("inventory", "0005_stock_transfer")])
