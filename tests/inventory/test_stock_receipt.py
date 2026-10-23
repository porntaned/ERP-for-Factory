"""Synthetic receipt behavior and authoritative PostgreSQL storage boundaries."""

from decimal import Decimal
from importlib import import_module
from uuid import uuid4

import pytest
from django.apps import apps
from django.db import DatabaseError, connection, transaction
from django.db.models.deletion import ProtectedError


@pytest.fixture
def receipt_contract():
    try:
        services = import_module("inventory.services")
        return {
            "model": apps.get_model("inventory", "StockReceipt"),
            "receive": services.receive_stock,
            "validation": services.ReceiptValidationError,
            "authorization": services.ReceiptAuthorizationError,
            "conflict": services.ReceiptConflictError,
        }
    except LookupError, AttributeError, ModuleNotFoundError:
        pytest.fail("M4.2 receipt contract absent: controlled RED", pytrace=False)


@pytest.fixture
def receipt_scope(ledger_scope):
    scope = ledger_scope
    scope["grant"] = apps.get_model("access_control", "WarehouseRoleAssignment").objects.create(
        user=scope["actor"], warehouse=scope["warehouse"], role="WAREHOUSE"
    )
    return scope


def receipt_values(scope, **overrides):
    values = dict(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=scope["actor"],
        quantity=Decimal("100.000001"),
        reason="Synthetic receipt — ทดสอบ",
        request_id=uuid4(),
    )
    values.update(overrides)
    return values


@pytest.mark.django_db
def test_receipt_posts_exact_positive_entry_and_preserves_default_hold(
    receipt_contract, receipt_scope, ledger_contract
):
    values = receipt_values(receipt_scope)
    receipt = receipt_contract["receive"](**values)
    entry = receipt.ledger_entry
    assert entry.quantity_delta == values["quantity"]
    assert entry.reason == values["reason"]
    assert entry.lot_id == values["lot"].pk
    assert entry.warehouse_id == values["warehouse"].pk
    assert entry.actor_id == values["actor"].pk
    assert entry.created_at is not None
    assert receipt.request_id == values["request_id"]
    assert (
        ledger_contract[1](lot=values["lot"], warehouse=values["warehouse"]) == values["quantity"]
    )
    quality = import_module("quality.services")
    assert quality.get_lot_disposition(lot=values["lot"], warehouse=values["warehouse"]) == "HOLD"
    assert apps.get_model("quality", "LotDispositionEvent").objects.count() == 0


@pytest.mark.django_db
def test_exact_retry_returns_original_without_second_post(
    receipt_contract, receipt_scope, ledger_contract
):
    values = receipt_values(receipt_scope)
    original = receipt_contract["receive"](**values)
    retried = receipt_contract["receive"](**values)
    assert retried.pk == original.pk
    assert receipt_contract["model"].objects.count() == 1
    assert ledger_contract[0].objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value",
    [
        ("quantity", Decimal("2")),
        ("reason", "Changed"),
        ("lot", "second"),
        ("warehouse", "other"),
        ("actor", "new_actor"),
    ],
)
def test_reused_request_with_changed_payload_conflicts_atomically(
    receipt_contract, receipt_scope, ledger_contract, field, value
):
    values = receipt_values(receipt_scope)
    receipt_contract["receive"](**values)
    if field in ("lot", "warehouse"):
        value = receipt_scope[value]
    if field == "actor":
        value = type(receipt_scope["actor"]).objects.create(username="other-receiver")
    if field in ("actor", "warehouse"):
        apps.get_model("access_control", "WarehouseRoleAssignment").objects.create(
            user=value if field == "actor" else receipt_scope["actor"],
            warehouse=value if field == "warehouse" else receipt_scope["warehouse"],
            role="WAREHOUSE",
        )
    with pytest.raises(receipt_contract["conflict"]):
        receipt_contract["receive"](**(values | {field: value}))
    assert receipt_contract["model"].objects.count() == 1
    assert ledger_contract[0].objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value",
    [
        ("reason", ""),
        ("reason", " \t\n"),
        ("reason", None),
        ("reason", 12),
        ("request_id", None),
        ("request_id", "not-a-uuid"),
        ("request_id", "00000000-0000-0000-0000-000000000000"),
    ],
)
def test_invalid_reason_or_request_rejected(
    receipt_contract, receipt_scope, ledger_contract, field, value
):
    with pytest.raises(receipt_contract["validation"]):
        receipt_contract["receive"](**receipt_values(receipt_scope, **{field: value}))
    assert ledger_contract[0].objects.count() == 0
    assert receipt_contract["model"].objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("role", [None, "QUALITY", "PRODUCTION", "APPROVER"])
def test_exact_warehouse_role_required_even_for_superuser(
    receipt_contract, receipt_scope, ledger_contract, role
):
    receipt_scope["grant"].delete()
    actor = receipt_scope["actor"]
    actor.is_superuser = True
    actor.save()
    if role:
        apps.get_model("access_control", "WarehouseRoleAssignment").objects.create(
            user=actor, warehouse=receipt_scope["warehouse"], role=role
        )
    with pytest.raises(receipt_contract["authorization"]):
        receipt_contract["receive"](**receipt_values(receipt_scope))
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db
def test_sibling_warehouse_grant_does_not_authorize_destination(receipt_contract, receipt_scope):
    with pytest.raises(receipt_contract["authorization"]):
        receipt_contract["receive"](
            **receipt_values(receipt_scope, warehouse=receipt_scope["other"])
        )


@pytest.mark.django_db
def test_outer_rollback_removes_receipt_and_ledger(
    receipt_contract, receipt_scope, ledger_contract
):
    with transaction.atomic():
        receipt_contract["receive"](**receipt_values(receipt_scope))
        transaction.set_rollback(True)
    assert receipt_contract["model"].objects.count() == 0
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db
def test_trailing_zeros_and_reason_are_preserved(receipt_contract, receipt_scope):
    receipt = receipt_contract["receive"](
        **receipt_values(receipt_scope, quantity=Decimal("1.0000000000"), reason="  exact reason  ")
    )
    assert receipt.ledger_entry.quantity_delta == 1
    assert receipt.ledger_entry.reason == "  exact reason  "


@pytest.mark.django_db
@pytest.mark.parametrize("initial", ["HOLD", "RELEASED"])
def test_receipt_preserves_existing_quality_history(receipt_contract, receipt_scope, initial):
    scope = receipt_scope
    apps.get_model("access_control", "WarehouseRoleAssignment").objects.create(
        user=scope["actor"], warehouse=scope["warehouse"], role="QUALITY"
    )
    quality = import_module("quality.services")
    quality.transition_lot_disposition(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=scope["actor"],
        expected_disposition="HOLD",
        target_disposition="RELEASED",
        reason="Synthetic accepted",
        request_id=uuid4(),
    )
    if initial == "HOLD":
        quality.transition_lot_disposition(
            lot=scope["lot"],
            warehouse=scope["warehouse"],
            actor=scope["actor"],
            expected_disposition="RELEASED",
            target_disposition="HOLD",
            reason="Synthetic recheck",
            request_id=uuid4(),
        )
    events = apps.get_model("quality", "LotDispositionEvent")
    before = list(events.objects.values())
    receipt_contract["receive"](**receipt_values(scope))
    assert quality.get_lot_disposition(lot=scope["lot"], warehouse=scope["warehouse"]) == initial
    assert list(events.objects.values()) == before


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["update", "delete", "rewrite_pk"])
def test_database_receipt_history_is_immutable(receipt_contract, receipt_scope, action):
    receipt = receipt_contract["receive"](**receipt_values(receipt_scope))
    table = receipt._meta.db_table
    sql = {
        "update": f"UPDATE {table} SET request_id = %s WHERE id = %s",
        "delete": f"DELETE FROM {table} WHERE id = %s",
        "rewrite_pk": f"UPDATE {table} SET id = id + 100 WHERE id = %s",
    }[action]
    params = [uuid4(), receipt.pk] if action == "update" else [receipt.pk]
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(sql, params)
    assert receipt_contract["model"].objects.get(pk=receipt.pk).request_id == receipt.request_id


@pytest.mark.django_db
@pytest.mark.parametrize(
    "violation",
    ["request", "entry", "negative", "missing", "null_request", "null_entry", "explicit_id"],
)
def test_database_receipt_constraints(receipt_contract, receipt_scope, append_entry, violation):
    receipt = receipt_contract["receive"](**receipt_values(receipt_scope))
    entry = append_entry("2")
    request_id, entry_id = uuid4(), entry.pk
    if violation == "request":
        request_id = receipt.request_id
    elif violation == "entry":
        entry_id = receipt.ledger_entry_id
    elif violation == "negative":
        entry_id = append_entry("-1").pk
    elif violation == "missing":
        entry_id = 999999999
    elif violation == "null_request":
        request_id = None
    elif violation == "null_entry":
        entry_id = None
    columns = "request_id, ledger_entry_id"
    placeholders = "%s, %s"
    params = [request_id, entry_id]
    if violation == "explicit_id":
        columns += ", id"
        placeholders += ", %s"
        params.append(receipt.pk + 100)
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {receipt._meta.db_table} ({columns}) VALUES ({placeholders})", params
        )
        # Force deferred FK checks inside the exception-catching savepoint.
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    assert receipt_contract["model"].objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "quantity",
    [
        None,
        1,
        1.0,
        "1",
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("100000000000000"),
        Decimal("0.0000001"),
    ],
)
def test_invalid_quantity_leaves_no_receipt_or_ledger(
    receipt_contract, receipt_scope, ledger_contract, quantity
):
    with pytest.raises(receipt_contract["validation"]):
        receipt_contract["receive"](**receipt_values(receipt_scope, quantity=quantity))
    assert receipt_contract["model"].objects.count() == 0
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("revocation", ["grant", "active"])
def test_retry_rechecks_current_persisted_authorization(
    receipt_contract, receipt_scope, ledger_contract, revocation
):
    values = receipt_values(receipt_scope)
    receipt_contract["receive"](**values)
    if revocation == "grant":
        receipt_scope["grant"].delete()
    else:
        type(receipt_scope["actor"]).objects.filter(pk=values["actor"].pk).update(is_active=False)
    with pytest.raises(receipt_contract["authorization"]):
        receipt_contract["receive"](**values)
    assert ledger_contract[0].objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["lot", "warehouse"])
@pytest.mark.parametrize("kind", ["unsaved", "manual_pk", "missing", "wrong_type"])
def test_reject_invalid_parent_records(
    receipt_contract, receipt_scope, ledger_contract, field, kind
):
    original = receipt_scope[field]
    if kind == "wrong_type":
        invalid = receipt_scope["actor"]
    elif kind == "missing":
        invalid = type(original).objects.get(pk=original.pk)
        invalid.pk = 999999999
    else:
        invalid = type(original)()
        if kind == "manual_pk":
            invalid.pk = original.pk
    with pytest.raises(receipt_contract["validation"]):
        receipt_contract["receive"](**receipt_values(receipt_scope, **{field: invalid}))
    assert ledger_contract[0].objects.count() == 0
    assert receipt_contract["model"].objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["unsaved", "manual_pk", "missing", "wrong_type", "inactive"])
def test_reject_invalid_actor_records(receipt_contract, receipt_scope, ledger_contract, kind):
    actor = receipt_scope["actor"]
    if kind == "wrong_type":
        actor = receipt_scope["lot"]
    elif kind in ("unsaved", "manual_pk"):
        actor = type(actor)(username="unpersisted")
        if kind == "manual_pk":
            actor.pk = receipt_scope["actor"].pk
    elif kind == "missing":
        actor.pk = 999999999
    else:
        type(actor).objects.filter(pk=actor.pk).update(is_active=False)
    with pytest.raises(receipt_contract["authorization"]):
        receipt_contract["receive"](**receipt_values(receipt_scope, actor=actor))
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db
def test_maximum_quantity_and_distinct_receipts_add_exactly(
    receipt_contract, receipt_scope, ledger_contract
):
    values = receipt_values(receipt_scope, quantity=Decimal("99999999999999.999999"))
    first = receipt_contract["receive"](**values)
    second = receipt_contract["receive"](
        **(values | {"request_id": uuid4(), "quantity": Decimal("0.000001")})
    )
    assert first.pk != second.pk
    assert ledger_contract[1](lot=values["lot"], warehouse=values["warehouse"]) == Decimal(
        "100000000000000.000000"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("parent", ["lot", "warehouse"])
def test_stale_cached_parent_uses_current_organization(
    receipt_contract, receipt_scope, ledger_contract, parent
):
    scope = receipt_scope
    # Populate caller-side relation caches before changing the persisted identity.
    assert scope["lot"].item.organization_id == scope["warehouse"].plant.organization_id
    organization = type(scope["organization"]).objects.create(
        code="FOREIGN", display_name="Synthetic"
    )
    if parent == "warehouse":
        plant = type(scope["plant"]).objects.create(
            organization=organization, code="F", display_name="Synthetic"
        )
        type(scope["warehouse"]).objects.filter(pk=scope["warehouse"].pk).update(plant=plant)
    else:
        item = type(scope["item"]).objects.create(
            organization=organization,
            base_uom=scope["uom"],
            code="F",
            display_name="Synthetic",
            item_type="RAW",
        )
        type(scope["lot"]).objects.filter(pk=scope["lot"].pk).update(item=item)
    with pytest.raises(receipt_contract["validation"]):
        receipt_contract["receive"](**receipt_values(scope))
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db
def test_stale_inactive_cache_does_not_deny_current_active_actor(receipt_contract, receipt_scope):
    actor = receipt_scope["actor"]
    actor.is_active = False
    receipt = receipt_contract["receive"](**receipt_values(receipt_scope))
    assert receipt.ledger_entry.actor_id == actor.pk


@pytest.mark.django_db
def test_failure_after_ledger_insert_rolls_back_both_writes(
    receipt_contract, receipt_scope, ledger_contract, monkeypatch
):
    values = receipt_values(receipt_scope)

    def fail_receipt_insert(**kwargs):
        assert ledger_contract[0].objects.count() == 1
        raise RuntimeError("Injected receipt insert failure after real ledger insert")

    with monkeypatch.context() as patch:
        patch.setattr(receipt_contract["model"].objects, "create", fail_receipt_insert)
        with pytest.raises(RuntimeError, match="Injected receipt insert failure"):
            receipt_contract["receive"](**values)
    assert receipt_contract["model"].objects.count() == 0
    assert ledger_contract[0].objects.count() == 0
    receipt_contract["receive"](**values)
    assert ledger_contract[0].objects.count() == 1


@pytest.mark.django_db
def test_receipt_link_cannot_be_changed_and_ledger_is_protected(
    receipt_contract, receipt_scope, append_entry
):
    receipt = receipt_contract["receive"](**receipt_values(receipt_scope))
    alternative = append_entry("1")
    with pytest.raises(DatabaseError), transaction.atomic():
        receipt_contract["model"].objects.filter(pk=receipt.pk).update(ledger_entry=alternative)
    with pytest.raises(ProtectedError):
        receipt.ledger_entry.delete()
    receipt.refresh_from_db()
    assert receipt.ledger_entry_id != alternative.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "SERIALIZABLE"])
def test_receipt_requires_supported_read_committed_isolation(
    receipt_contract, receipt_scope, ledger_contract, isolation
):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation}")
        with pytest.raises(receipt_contract["validation"]):
            receipt_contract["receive"](**receipt_values(receipt_scope))
    assert receipt_contract["model"].objects.count() == 0
    assert ledger_contract[0].objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_receipt_migration_reverse_reapply_preserves_ledger_and_restores_guards(
    receipt_contract, receipt_scope, ledger_contract, append_entry
):
    from django.db.migrations.executor import MigrationExecutor

    entry = append_entry("3")
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("inventory", "0003_preserve_stock_parent_lifetime")])
        assert "inventory_stockreceipt" not in connection.introspection.table_names()
        assert ledger_contract[0].objects.get(pk=entry.pk).quantity_delta == 3
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regprocedure('inventory_validate_receipt_link()')")
            assert cursor.fetchone()[0] is None
    finally:
        MigrationExecutor(connection).migrate(latest)
    assert ledger_contract[0].objects.get(pk=entry.pk).quantity_delta == 3
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regprocedure('inventory_validate_receipt_link()')")
        assert cursor.fetchone()[0] is not None
    receipt = receipt_contract["model"].objects.create(request_id=uuid4(), ledger_entry=entry)
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            "UPDATE inventory_stockreceipt SET request_id = %s WHERE id = %s", [uuid4(), receipt.pk]
        )
    negative = append_entry("-1")
    with pytest.raises(DatabaseError), transaction.atomic():
        receipt_contract["model"].objects.create(request_id=uuid4(), ledger_entry=negative)
    another_positive = append_entry("1")
    with pytest.raises(DatabaseError), transaction.atomic():
        receipt_contract["model"].objects.create(
            id=receipt.pk + 100, request_id=uuid4(), ledger_entry=another_positive
        )
    assert receipt_contract["model"].objects.count() == 1
