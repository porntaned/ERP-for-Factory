"""Storage integrity only: these synthetic writes are not business commands."""

from decimal import Decimal

import pytest
from django.apps import apps
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError


def raw_append(scope, delta, **overrides):
    values = dict(
        lot_id=scope["lot"].pk,
        warehouse_id=scope["warehouse"].pk,
        actor_id=scope["actor"].pk,
        quantity_delta=delta,
        reason="Synthetic SQL",
    )
    values.update(overrides)
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO inventory_stockledgerentry "
            "(lot_id, warehouse_id, actor_id, quantity_delta, reason) "
            "VALUES (%s, %s, %s, %s, %s)",
            list(values.values()),
        )


@pytest.mark.django_db
def test_exact_balance_empty_exhaustion_and_pair_isolation(
    ledger_contract, ledger_scope, append_entry
):
    _, balance = ledger_contract
    pair = dict(lot=ledger_scope["lot"], warehouse=ledger_scope["warehouse"])
    assert balance(**pair) == Decimal("0")
    append_entry("1.234567")
    append_entry("0.000001")
    append_entry("5", warehouse=ledger_scope["other"])
    append_entry("7", lot=ledger_scope["second"])
    assert balance(**pair) == Decimal("1.234568")
    append_entry("-1.234568")
    assert balance(**pair) == Decimal("0")
    assert balance(lot=pair["lot"], warehouse=ledger_scope["other"]) == Decimal("5")
    assert balance(lot=ledger_scope["second"], warehouse=pair["warehouse"]) == Decimal("7")


@pytest.mark.django_db
def test_total_can_exceed_single_entry_range(ledger_contract, ledger_scope, append_entry):
    append_entry("99999999999999.999999")
    append_entry("99999999999999.999999")
    assert ledger_contract[1](lot=ledger_scope["lot"], warehouse=ledger_scope["warehouse"]) == (
        Decimal("199999999999999.999998")
    )
    # Isolate the entry lower bound from the nonnegative-balance rule.
    with pytest.raises(IntegrityError), transaction.atomic():
        raw_append(ledger_scope, "-100000000000000")
    assert ledger_contract[0].objects.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    "delta",
    [
        "0",
        "-0.000001",
        "100000000000000",
        "-100000000000000",
        "0.0000001",
        "1.2345678",
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_raw_invalid_quantity_rejected_without_entry(ledger_contract, ledger_scope, delta):
    with pytest.raises(IntegrityError), transaction.atomic():
        raw_append(ledger_scope, delta)
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("delta", ["0.0000001", "1.2345678", "0", "100000000000000"])
def test_orm_does_not_silently_round_quantity(ledger_contract, append_entry, delta):
    with pytest.raises(IntegrityError), transaction.atomic():
        append_entry(delta)
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db
def test_harmless_trailing_zeros_are_exact(ledger_contract, ledger_scope):
    raw_append(ledger_scope, "1.0000000")
    assert ledger_contract[1](lot=ledger_scope["lot"], warehouse=ledger_scope["warehouse"]) == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field", ["lot_id", "warehouse_id", "actor_id", "quantity_delta", "reason"]
)
def test_null_fields_rejected(ledger_contract, ledger_scope, field):
    with pytest.raises(IntegrityError), transaction.atomic():
        raw_append(ledger_scope, "1", **{field: None})


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("field", ["lot_id", "warehouse_id", "actor_id"])
def test_missing_references_rejected(ledger_contract, ledger_scope, field):
    with pytest.raises(IntegrityError), transaction.atomic():
        raw_append(ledger_scope, "1", **{field: 2147483647})


@pytest.mark.django_db
@pytest.mark.parametrize("reason", ["", " \t\n"])
def test_blank_reason_rejected(ledger_contract, append_entry, reason):
    with pytest.raises(IntegrityError), transaction.atomic():
        append_entry(reason=reason)


@pytest.mark.django_db
def test_cross_organization_rejected(ledger_contract, ledger_scope, append_entry):
    org = apps.get_model("facilities", "Organization").objects.create(code="OTHER", display_name="")
    type(ledger_scope["plant"]).objects.filter(pk=ledger_scope["plant"].pk).update(organization=org)
    with pytest.raises(IntegrityError), transaction.atomic():
        append_entry()
    with pytest.raises(ValueError):
        ledger_contract[1](lot=ledger_scope["lot"], warehouse=ledger_scope["warehouse"])


@pytest.mark.django_db
def test_overdraw_and_outer_rollback_preserve_history(ledger_contract, ledger_scope, append_entry):
    append_entry("10")
    with pytest.raises(IntegrityError), transaction.atomic():
        append_entry("-11")
    with pytest.raises(RuntimeError), transaction.atomic():
        append_entry("-4")
        raise RuntimeError("abort synthetic transaction")
    assert ledger_contract[0].objects.count() == 1
    assert ledger_contract[1](lot=ledger_scope["lot"], warehouse=ledger_scope["warehouse"]) == 10


@pytest.mark.django_db
def test_bulk_statement_failure_has_no_partial_entries(ledger_contract, ledger_scope):
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO inventory_stockledgerentry "
            "(lot_id,warehouse_id,actor_id,quantity_delta,reason) VALUES "
            "(%s,%s,%s,2,'synthetic'),(%s,%s,%s,-3,'synthetic')",
            [ledger_scope[k].pk for k in ("lot", "warehouse", "actor")] * 2,
        )
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["update", "delete", "sql_update", "sql_delete"])
def test_history_is_immutable(ledger_contract, append_entry, method):
    entry = append_entry()
    with pytest.raises(IntegrityError), transaction.atomic():
        if method == "update":
            ledger_contract[0].objects.filter(pk=entry.pk).update(quantity_delta=20)
        elif method == "delete":
            ledger_contract[0].objects.filter(pk=entry.pk).delete()
        else:
            sql = (
                "UPDATE inventory_stockledgerentry SET reason='rewritten' WHERE id=%s"
                if method == "sql_update"
                else "DELETE FROM inventory_stockledgerentry WHERE id=%s"
            )
            with connection.cursor() as cursor:
                cursor.execute(sql, [entry.pk])
    entry.refresh_from_db()
    assert entry.quantity_delta == 10


@pytest.mark.django_db
@pytest.mark.parametrize("parent", ["lot", "warehouse", "actor"])
def test_parent_deletion_protected(ledger_contract, ledger_scope, append_entry, parent):
    append_entry()
    with pytest.raises(ProtectedError):
        ledger_scope[parent].delete()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "parent,field,target",
    [
        ("lot", "item_id", "second_item"),
        ("item", "base_uom_id", "second_uom"),
        ("item", "organization_id", "second_org"),
        ("warehouse", "plant_id", "second_plant"),
        ("plant", "organization_id", "second_org"),
    ],
)
def test_history_freezes_identity_even_at_zero(
    ledger_contract, ledger_scope, append_entry, parent, field, target
):
    scope = ledger_scope
    scope["second_org"] = type(scope["organization"]).objects.create(code="OTHER", display_name="")
    scope["second_uom"] = type(scope["uom"]).objects.create(code="EA", display_name="")
    scope["second_plant"] = type(scope["plant"]).objects.create(
        organization=scope["organization"], code="OTHER", display_name=""
    )
    scope["second_item"] = type(scope["item"]).objects.create(
        organization=scope["organization"],
        base_uom=scope["uom"],
        code="OTHER",
        item_type="RAW",
        display_name="",
    )
    append_entry("2")
    append_entry("-2")
    with pytest.raises(IntegrityError), transaction.atomic():
        type(scope[parent]).objects.filter(pk=scope[parent].pk).update(**{field: scope[target].pk})


@pytest.mark.django_db
def test_metadata_edits_and_identity_before_history_allowed(
    ledger_contract, ledger_scope, append_entry
):
    uom = type(ledger_scope["uom"]).objects.create(code="EA", display_name="Each")
    type(ledger_scope["item"]).objects.filter(pk=ledger_scope["item"].pk).update(base_uom=uom)
    append_entry()
    type(ledger_scope["item"]).objects.filter(pk=ledger_scope["item"].pk).update(display_name="ใหม่")
    ledger_scope["item"].refresh_from_db()
    assert ledger_scope["item"].display_name == "ใหม่"


@pytest.mark.django_db
@pytest.mark.parametrize("parent", ["lot", "warehouse"])
@pytest.mark.parametrize("kind", ["none", "unsaved_collision", "missing"])
def test_balance_rejects_invalid_inputs(ledger_contract, ledger_scope, parent, kind):
    pair = {key: ledger_scope[key] for key in ("lot", "warehouse")}
    if kind == "none":
        pair[parent] = None
    elif kind == "unsaved_collision":
        pair[parent] = type(pair[parent])(pk=pair[parent].pk)
    else:
        pair[parent].pk = 2147483647
    with pytest.raises(ValueError):
        ledger_contract[1](**pair)


@pytest.mark.django_db
def test_server_timestamp_and_identity(ledger_contract, ledger_scope, append_entry):
    from datetime import datetime, timezone

    old = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with connection.cursor() as cursor:
        cursor.execute("SELECT clock_timestamp()")
        before = cursor.fetchone()[0]
    entry = append_entry(created_at=old)
    entry.refresh_from_db()
    with connection.cursor() as cursor:
        cursor.execute("SELECT clock_timestamp()")
        after = cursor.fetchone()[0]
    assert before <= entry.created_at <= after
    assert entry.created_at.tzinfo is not None
    with pytest.raises(DatabaseError) as rejected, transaction.atomic():
        append_entry(id=entry.pk + 1000000)
    assert rejected.value.__cause__.sqlstate == "428C9"
    with (
        pytest.raises(DatabaseError) as rejected,
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "INSERT INTO inventory_stockledgerentry "
            "(id,lot_id,warehouse_id,actor_id,quantity_delta,reason) VALUES (%s,%s,%s,%s,1,'test')",
            [
                entry.pk + 1000000,
                ledger_scope["lot"].pk,
                ledger_scope["warehouse"].pk,
                ledger_scope["actor"].pk,
            ],
        )
    assert rejected.value.__cause__.sqlstate == "428C9"
    assert ledger_contract[0].objects.count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "SERIALIZABLE"])
def test_unsupported_isolation_fails_closed(ledger_contract, ledger_scope, isolation):
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL " + isolation)
        raw_append(ledger_scope, "1")
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "SERIALIZABLE"])
@pytest.mark.parametrize(
    "parent,field",
    [
        ("lot", "item_id"),
        ("item", "base_uom_id"),
        ("item", "organization_id"),
        ("warehouse", "plant_id"),
        ("plant", "organization_id"),
    ],
)
def test_parent_changes_require_read_committed_even_without_history(
    ledger_contract, ledger_scope, isolation, parent, field
):
    record = ledger_scope[parent]
    # Invalid reference deliberately catches the trigger before deferred FK checking.
    # A named 23514 check failure establishes that isolation, not the FK, rejected it.
    with pytest.raises(IntegrityError, match="identity changes require READ COMMITTED"):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL " + isolation)
            type(record).objects.filter(pk=record.pk).update(**{field: 2147483647})
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL " + isolation)
        type(record).objects.filter(pk=record.pk).update(**{field: getattr(record, field)})
        if parent != "lot":
            type(record).objects.filter(pk=record.pk).update(display_name="Metadata only")


@pytest.mark.django_db(transaction=True)
def test_ledger_migration_reverse_and_reapply_restores_guards(ledger_contract, ledger_scope):
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("inventory", "0001_initial")])
        assert "inventory_stockledgerentry" not in connection.introspection.table_names()
    finally:
        MigrationExecutor(connection).migrate(latest)
    raw_append(ledger_scope, "1")
    with pytest.raises(IntegrityError), transaction.atomic():
        raw_append(ledger_scope, "-2")
    assert ledger_contract[0].objects.count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("parent", ["lot", "warehouse"])
def test_deferred_forward_parent_cannot_bypass_locked_identity(
    ledger_contract, ledger_scope, parent
):
    # The failure must happen at INSERT, not when the outer FK constraint is checked.
    # Otherwise a later cross-organization parent creation could legitimize an
    # entry whose organization was never validated and whose parent was never locked.
    with transaction.atomic():
        with pytest.raises(IntegrityError, match="require one organization"), transaction.atomic():
            raw_append(ledger_scope, "1", **{parent + "_id": 2147483647})
        assert ledger_contract[0].objects.count() == 0
