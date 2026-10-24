"""Exact atomic posting, real database failure, and observed concurrent lock waits."""

from decimal import Decimal, localcontext
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction

from access_control.models import WarehouseRoleAssignment
from facilities.models import Organization, Plant, Warehouse
from inventory.models import Lot, StockLedgerEntry
from inventory.services import get_stock_balance
from inventory.transfer_policy import TransferQualityError, TransferQualityValidationError
from inventory.transfers import (
    InsufficientStockError,
    TransferAuthorizationError,
    TransferValidationError,
    transfer_stock,
)
from quality.models import LotDispositionEvent
from quality.services import get_lot_disposition, transition_lot_disposition

from .test_stock_receipt_concurrency import blocked_action


@pytest.fixture
def transfer_scope(ledger_scope):
    scope = ledger_scope
    for warehouse in (scope["warehouse"], scope["other"]):
        for role in ("QUALITY", "WAREHOUSE"):
            WarehouseRoleAssignment.objects.create(
                user=scope["actor"], warehouse=warehouse, role=role
            )
    StockLedgerEntry.objects.create(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=scope["actor"],
        quantity_delta=Decimal("100.000001"),
        reason="Synthetic starting stock",
    )
    change_quality(scope, scope["warehouse"], "RELEASED")
    return scope


def change_quality(scope, warehouse, target):
    return transition_lot_disposition(
        lot=scope["lot"],
        warehouse=warehouse,
        actor=scope["actor"],
        expected_disposition=get_lot_disposition(lot=scope["lot"], warehouse=warehouse),
        target_disposition=target,
        reason="Synthetic Quality",
        request_id=uuid4(),
    )


def post(scope, **overrides):
    return transfer_stock(
        **(
            dict(
                lot=scope["lot"],
                source_warehouse=scope["warehouse"],
                destination_warehouse=scope["other"],
                actor=scope["actor"],
                quantity=Decimal("30.000001"),
                reason="  โอน LED — synthetic  ",
                request_id=uuid4(),
            )
            | overrides
        )
    )


def balances(scope):
    return tuple(
        get_stock_balance(lot=scope["lot"], warehouse=scope[k]) for k in ("warehouse", "other")
    )


@pytest.mark.django_db
@pytest.mark.parametrize("destination", ["DEFAULT", "HOLD", "RELEASED"])
@pytest.mark.parametrize("quantity", [Decimal("30.000001"), Decimal("100.000001")])
def test_exact_pair_conserves_stock_and_preserves_quality(transfer_scope, destination, quantity):
    scope = transfer_scope
    if destination != "DEFAULT":
        change_quality(scope, scope["other"], "RELEASED")
        if destination == "HOLD":
            change_quality(scope, scope["other"], "HOLD")
    events = list(LotDispositionEvent.objects.order_by("id").values())
    debit, credit = post(scope, quantity=quantity)
    debit.refresh_from_db()
    credit.refresh_from_db()
    assert debit.quantity_delta == quantity.copy_negate()
    assert credit.quantity_delta == quantity
    assert debit.warehouse_id == scope["warehouse"].pk
    assert credit.warehouse_id == scope["other"].pk
    for entry in (debit, credit):
        assert entry.actor_id == scope["actor"].pk
        assert entry.lot_id == scope["lot"].pk
        assert entry.reason == "  โอน LED — synthetic  "
        assert entry.created_at is not None
    assert balances(scope) == (Decimal("100.000001") - quantity, quantity)
    assert list(LotDispositionEvent.objects.order_by("id").values()) == events
    assert StockLedgerEntry.objects.count() == 3


@pytest.mark.django_db
def test_small_decimal_context_cannot_round_debit(transfer_scope):
    with localcontext() as ctx:
        ctx.prec = 3
        debit, credit = post(transfer_scope)
    debit.refresh_from_db()
    credit.refresh_from_db()
    assert debit.quantity_delta == Decimal("-30.000001")
    assert credit.quantity_delta == Decimal("30.000001")
    assert balances(transfer_scope) == (Decimal("70"), Decimal("30.000001"))


@pytest.mark.django_db
@pytest.mark.parametrize("quantity", [Decimal("100.000002"), Decimal("200")])
def test_insufficient_source_writes_neither_side(transfer_scope, quantity):
    with pytest.raises(InsufficientStockError):
        post(transfer_scope, quantity=quantity)
    assert balances(transfer_scope) == (Decimal("100.000001"), 0)
    assert StockLedgerEntry.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "quantity",
    [
        None,
        True,
        "1",
        0.1,
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("1e14"),
        Decimal("0.0000001"),
        Decimal("1.0000001"),
    ],
)
def test_invalid_quantity_is_rejected(transfer_scope, quantity):
    with pytest.raises(TransferValidationError):
        post(transfer_scope, quantity=quantity)
    assert StockLedgerEntry.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("quantity", [Decimal("0.000001"), Decimal("1.0000000")])
def test_exact_precision_boundary_and_trailing_zero(transfer_scope, quantity):
    debit, credit = post(transfer_scope, quantity=quantity)
    assert debit.quantity_delta == quantity.copy_negate()
    assert credit.quantity_delta == quantity


@pytest.mark.django_db
@pytest.mark.parametrize("reason", [None, 1, "", " \t\n", "\u2003"])
def test_invalid_reason_is_rejected(transfer_scope, reason):
    with pytest.raises(TransferValidationError):
        post(transfer_scope, reason=reason)
    assert StockLedgerEntry.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["lot", "source_warehouse", "destination_warehouse"])
@pytest.mark.parametrize("invalid", ["none", "wrong", "unsaved", "manual_pk", "missing"])
def test_posting_checks_saved_existing_identities(transfer_scope, field, invalid):
    scope = transfer_scope
    model = Lot if field == "lot" else Warehouse
    existing = scope["lot"] if model == Lot else scope["warehouse"]
    value = None if invalid == "none" else "1" if invalid == "wrong" else model()
    if invalid == "manual_pk":
        value.pk = existing.pk
    elif invalid == "missing":
        value.pk = 999999999
        value._state.adding = False
    with pytest.raises(TransferQualityValidationError):
        post(scope, **{field: value})
    assert StockLedgerEntry.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "which",
    [
        "source",
        "destination",
        "both",
        "wrong_role",
        "superuser",
        "inactive",
        "deleted",
        "none",
        "unsaved",
        "manual_pk",
    ],
)
def test_current_actor_and_both_exact_grants_required(transfer_scope, which):
    scope = transfer_scope
    actor = scope["actor"]
    grants = WarehouseRoleAssignment.objects.filter(user=actor, role="WAREHOUSE")
    if which in ("source", "destination"):
        grants.filter(warehouse=scope["warehouse" if which == "source" else "other"]).delete()
    elif which in ("both", "wrong_role", "superuser"):
        grants.delete()  # QUALITY alone is insufficient.
        if which == "superuser":
            actor.is_superuser = True
            actor.save()
    elif which == "inactive":
        type(actor).objects.filter(pk=actor.pk).update(is_active=False)
        assert actor.is_active  # stale caller state must not authorize.
    elif which == "deleted":
        actor = get_user_model().objects.create(username="deleted-transfer-actor")
        pk = actor.pk
        actor.delete()
        actor.pk = pk
        actor._state.adding = False
    elif which == "none":
        actor = None
    else:
        actor = get_user_model()(username="unsaved-transfer")
        if which == "manual_pk":
            actor.pk = scope["actor"].pk
    with pytest.raises(TransferAuthorizationError):
        post(scope, actor=actor)
    assert StockLedgerEntry.objects.count() == 1


@pytest.mark.django_db
def test_same_warehouse_and_persisted_cross_plant_are_rejected(transfer_scope):
    scope = transfer_scope
    with pytest.raises(TransferQualityValidationError):
        post(scope, destination_warehouse=scope["warehouse"])
    other = Plant.objects.create(organization=scope["organization"], code="OTHER", display_name="O")
    assert scope["other"].plant_id == scope["plant"].pk
    Warehouse.objects.filter(pk=scope["other"].pk).update(plant=other)
    with pytest.raises(TransferQualityValidationError):
        post(scope)
    assert StockLedgerEntry.objects.count() == 1


@pytest.mark.django_db
def test_source_hold_cannot_be_transferred(transfer_scope):
    scope = transfer_scope
    change_quality(scope, scope["warehouse"], "HOLD")
    with pytest.raises(TransferQualityError):
        post(scope)
    assert StockLedgerEntry.objects.count() == 1


@pytest.mark.django_db
def test_real_destination_database_failure_rolls_back_debit_in_caller_transaction(transfer_scope):
    scope = transfer_scope
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE FUNCTION pg_temp.reject_transfer_credit() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.warehouse_id = TG_ARGV[0]::bigint THEN
                    RAISE EXCEPTION 'synthetic destination failure' USING ERRCODE='23514';
                END IF;
                RETURN NEW;
            END; $$;
        """)
        cursor.execute(
            "CREATE TRIGGER test_reject_transfer_credit BEFORE INSERT ON inventory_stockledgerentry "
            "FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_transfer_credit(%s)",
            [str(scope["other"].pk)],
        )
    try:
        with transaction.atomic():
            with pytest.raises(IntegrityError, match="synthetic destination failure"):
                post(scope)
            assert balances(scope) == (Decimal("100.000001"), 0)
            assert StockLedgerEntry.objects.count() == 1
            Organization.objects.create(code="CONTINUE", display_name="Outer still usable")
        assert Organization.objects.filter(code="CONTINUE").exists()
    finally:
        with connection.cursor() as cursor:
            cursor.execute("DROP TRIGGER test_reject_transfer_credit ON inventory_stockledgerentry")
            cursor.execute("DROP FUNCTION pg_temp.reject_transfer_credit()")


@pytest.mark.django_db
def test_outer_caller_rollback_restores_both_sides(transfer_scope):
    with transaction.atomic():
        post(transfer_scope)
        transaction.set_rollback(True)
    assert balances(transfer_scope) == (Decimal("100.000001"), 0)


@pytest.mark.django_db(transaction=True)
def test_competing_transfers_cannot_overdraw(transfer_scope):
    scope = transfer_scope
    _, outcome = blocked_action(
        lambda: post(scope, quantity=Decimal("70"))[0],
        lambda: post(scope, quantity=Decimal("70"))[0],
    )
    assert outcome[0] == "InsufficientStockError", outcome
    assert balances(scope) == (Decimal("30.000001"), Decimal("70"))
    assert StockLedgerEntry.objects.count() == 3


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mutation", ["quality", "deactivate", "source_grant", "destination_grant"])
@pytest.mark.parametrize("mutation_first", [False, True])
def test_transfer_serializes_with_quality_and_authorization_changes(
    transfer_scope,
    mutation,
    mutation_first,
):
    scope = transfer_scope

    def change():
        if mutation == "quality":
            change_quality(scope, scope["warehouse"], "HOLD")
        elif mutation == "deactivate":
            type(scope["actor"]).objects.filter(pk=scope["actor"].pk).update(is_active=False)
        else:
            WarehouseRoleAssignment.objects.filter(
                user=scope["actor"],
                role="WAREHOUSE",
                warehouse=scope["warehouse" if mutation == "source_grant" else "other"],
            ).delete()
        return scope["lot"]

    def transfer():
        return post(scope)[0]

    _, outcome = blocked_action(
        change if mutation_first else transfer, transfer if mutation_first else change
    )
    if mutation_first:
        expected = "TransferQualityError" if mutation == "quality" else "TransferAuthorizationError"
        assert outcome[0] == expected, outcome
        assert StockLedgerEntry.objects.count() == 1
        assert balances(scope) == (Decimal("100.000001"), 0)
    else:
        assert outcome[0] == "committed", outcome
        assert StockLedgerEntry.objects.count() == 3
        assert balances(scope) == (Decimal("70"), Decimal("30.000001"))
