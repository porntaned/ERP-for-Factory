"""Reject parent replacement at the statement, before deferred FKs can be repaired."""

import pytest
from django.db import IntegrityError, connection, transaction

from .test_stock_ledger import raw_append
from .test_stock_ledger_concurrency import wait_for_lock, worker


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("parent", ["lot", "warehouse", "actor", "item", "plant"])
@pytest.mark.parametrize("operation", ["delete", "move_pk"])
def test_history_parent_cannot_be_removed_before_same_pk_replacement(
    ledger_contract, ledger_scope, append_entry, parent, operation
):
    append_entry("1")
    append_entry("-1")
    record = ledger_scope[parent]
    table = connection.ops.quote_name(record._meta.db_table)
    with transaction.atomic():
        with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
            if operation == "delete":
                cursor.execute(f"DELETE FROM {table} WHERE id=%s", [record.pk])
            else:
                cursor.execute(f"UPDATE {table} SET id=%s WHERE id=%s", [2147483647, record.pk])
    record.refresh_from_db()
    assert ledger_contract[0].objects.count() == 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("parent", ["lot", "warehouse", "actor"])
def test_single_statement_parent_replacement_is_rejected(
    ledger_contract, ledger_scope, append_entry, parent
):
    append_entry()
    record = ledger_scope[parent]
    table = connection.ops.quote_name(record._meta.db_table)
    columns = ", ".join(connection.ops.quote_name(f.column) for f in record._meta.concrete_fields)
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            f"WITH removed AS (DELETE FROM {table} WHERE id=%s RETURNING *) "
            f"INSERT INTO {table} ({columns}) SELECT {columns} FROM removed",
            [record.pk],
        )
    record.refresh_from_db()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("parent", ["item", "plant"])
@pytest.mark.parametrize("operation", ["delete", "move_pk"])
@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "SERIALIZABLE"])
def test_ancestor_replacement_rejects_fixed_snapshots(
    ledger_contract, ledger_scope, parent, operation, isolation
):
    record = ledger_scope[parent]
    table = connection.ops.quote_name(record._meta.db_table)
    with pytest.raises(IntegrityError, match="ancestor replacement requires READ COMMITTED"):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL " + isolation)
            if operation == "delete":
                cursor.execute(f"DELETE FROM {table} WHERE id=%s", [record.pk])
            else:
                cursor.execute(f"UPDATE {table} SET id=%s WHERE id=%s", [2147483647, record.pk])
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL " + isolation)
        cursor.execute(
            f"UPDATE {table} SET id=id, display_name='metadata' WHERE id=%s", [record.pk]
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("parent", ["item", "plant"])
def test_unreferenced_ancestor_replacement_still_allowed(ledger_contract, ledger_scope, parent):
    record = ledger_scope[parent]
    table = connection.ops.quote_name(record._meta.db_table)
    columns = ", ".join(connection.ops.quote_name(f.column) for f in record._meta.concrete_fields)
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            f"WITH removed AS (DELETE FROM {table} WHERE id=%s RETURNING *) "
            f"INSERT INTO {table} ({columns}) SELECT {columns} FROM removed",
            [record.pk],
        )
    record.refresh_from_db()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("parent", ["lot", "warehouse", "actor", "item", "plant"])
@pytest.mark.parametrize("operation", ["delete", "move_pk"])
@pytest.mark.parametrize("replacement_first", [False, True])
def test_first_entry_and_parent_replacement_serialize(
    ledger_contract, ledger_scope, parent, operation, replacement_first
):
    from queue import Queue
    from threading import Thread

    record = ledger_scope[parent]
    table = connection.ops.quote_name(record._meta.db_table)
    original = {
        field.attname: getattr(record, field.attname) for field in record._meta.concrete_fields
    }
    if parent == "item":
        alternate = type(ledger_scope["uom"]).objects.create(code="EA", display_name="Each")
        original["base_uom_id"] = alternate.pk
    elif parent == "plant":
        alternate = type(ledger_scope["organization"]).objects.create(code="OTHER", display_name="")
        original["organization_id"] = alternate.pk

    def replace():
        with connection.cursor() as cursor:
            if operation == "delete":
                cursor.execute(f"DELETE FROM {table} WHERE id=%s", [record.pk])
            else:
                code_column = "username" if parent == "actor" else "code"
                cursor.execute(
                    f"UPDATE {table} SET id=%s, {code_column}=%s WHERE id=%s",
                    [2147483647, "OLD", record.pk],
                )
        type(record).objects.create(**original)

    def append():
        raw_append(ledger_scope, "1")

    first, second = (replace, append) if replacement_first else (append, replace)
    outcomes, pids = Queue(), Queue()
    thread = Thread(target=worker, args=(second, outcomes, pids))
    try:
        with transaction.atomic():
            first()
            thread.start()
            wait_for_lock(pids.get(timeout=5))
    finally:
        if thread.ident:
            thread.join(timeout=12)
    assert not thread.is_alive()
    # Replacing a Plant first changes the organization: the waiting append must
    # validate that new relationship and fail, not use its original snapshot.
    outcome = outcomes.get(timeout=1)
    if replacement_first and parent != "plant":
        # A row removed during a locking read may disappear from that statement's
        # snapshot. Failing closed is valid; a fresh attempt sees the new identity.
        assert outcome in {"committed", "rejected"}
        if outcome == "rejected":
            assert ledger_contract[0].objects.count() == 0
            raw_append(ledger_scope, "1")
    else:
        assert outcome == "rejected"
    assert ledger_contract[0].objects.count() == (
        0 if replacement_first and parent == "plant" else 1
    )


@pytest.mark.django_db(transaction=True)
def test_parent_lifetime_migration_reverse_reapply(ledger_contract, ledger_scope, append_entry):
    from django.db.migrations.executor import MigrationExecutor

    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()

    def foreign_key_modes():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT condeferrable, confupdtype, confdeltype FROM pg_constraint "
                "WHERE conrelid='inventory_stockledgerentry'::regclass AND contype='f'"
            )
            return cursor.fetchall()

    append_entry()
    try:
        MigrationExecutor(connection).migrate([("inventory", "0002_stock_ledger")])
        assert foreign_key_modes() == [(True, "a", "a")] * 3
        assert ledger_contract[0].objects.count() == 1
    finally:
        MigrationExecutor(connection).migrate(latest)
    assert foreign_key_modes() == [(False, "r", "r")] * 3
    assert ledger_contract[0].objects.count() == 1
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("DELETE FROM catalog_item WHERE id=%s", [ledger_scope["item"].pk])
