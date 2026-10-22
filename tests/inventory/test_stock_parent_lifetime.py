"""Reject parent replacement at the statement, before deferred FKs can be repaired."""

import pytest
from django.db import IntegrityError, connection, transaction


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
