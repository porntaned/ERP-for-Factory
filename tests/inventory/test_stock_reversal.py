"""M4.5: reversal of receipts and transfers by compensating entries referencing the original.

Owner policy (Issue #59): both receipts and transfers; APPROVER at every warehouse
involved; whole transaction only; once only, a reversal cannot be reversed, insufficient
stock is rejected; receipt reversal in any Quality state, transfer reversal requires the
original destination to be RELEASED; Quality disposition never changes.
"""

from decimal import Decimal
from importlib import import_module
from uuid import uuid4

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from access_control.models import WarehouseRoleAssignment
from inventory.models import StockLedgerEntry, StockReceipt, StockTransfer
from inventory.services import ReceiptConflictError, receive_stock
from quality.models import LotDispositionEvent

from .test_atomic_transfer import balances, change_quality, post
from .test_atomic_transfer import transfer_scope as transfer_scope  # noqa: F401
from .test_stock_receipt_concurrency import blocked_action


@pytest.fixture
def rv():
    try:
        module = import_module("inventory.reversals")
        model = apps.get_model("inventory", "StockReversal")
    except ModuleNotFoundError, LookupError:
        pytest.fail("M4.5 reversal contract absent: controlled Issue #59 RED", pytrace=False)
    return module, model


def approver(scope, warehouses=("warehouse", "other"), username="synthetic-approver"):
    user = get_user_model().objects.create(username=username)
    user.set_unusable_password()
    user.save()
    for key in warehouses:
        WarehouseRoleAssignment.objects.create(user=user, warehouse=scope[key], role="APPROVER")
    return user


def receive(scope, quantity=Decimal("40"), key=None, warehouse="warehouse"):
    return receive_stock(
        lot=scope["lot"],
        warehouse=scope[warehouse],
        actor=scope["actor"],
        quantity=quantity,
        reason="Synthetic receipt",
        request_id=key or uuid4(),
    )


def quality_snapshot():
    return list(LotDispositionEvent.objects.order_by("id").values())


# ---------------------------------------------------------------- receipt reversal


@pytest.mark.django_db
@pytest.mark.parametrize("disposition", ["DEFAULT_HOLD", "HOLD", "RELEASED"])
def test_receipt_reversal_restores_balance_in_any_quality_state(transfer_scope, rv, disposition):
    module, model = rv
    scope = transfer_scope
    target = "other"  # never released by transfer_scope
    if disposition == "RELEASED":
        change_quality(scope, scope[target], "RELEASED")
    elif disposition == "HOLD":
        change_quality(scope, scope[target], "RELEASED")
        change_quality(scope, scope[target], "HOLD")
    receipt = receive(scope, warehouse=target)
    before = quality_snapshot()
    user = approver(scope)
    reversal = module.reverse_receipt(
        receipt=receipt, actor=user, reason="  Mis-keyed delivery — ทดสอบ ", request_id=uuid4()
    )
    assert balances(scope)[1] == 0
    assert reversal.receipt_id == receipt.pk and reversal.transfer_id is None
    assert reversal.credit_entry_id is None
    debit = reversal.debit_entry
    assert debit.quantity_delta == Decimal("-40") and debit.warehouse_id == scope[target].pk
    assert debit.lot_id == scope["lot"].pk and debit.actor_id == user.pk
    assert debit.reason == "  Mis-keyed delivery — ทดสอบ "
    assert quality_snapshot() == before
    assert model.objects.count() == 1


@pytest.mark.django_db
def test_receipt_reversal_rejected_when_stock_already_moved(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    receipt = receive(scope, quantity=Decimal("40"))
    post(scope, quantity=Decimal("130"))  # leaves 10.000001 at source, less than 40
    ledger_before = StockLedgerEntry.objects.count()
    with pytest.raises(module.InsufficientStockError):
        module.reverse_receipt(
            receipt=receipt, actor=approver(scope), reason="Too late", request_id=uuid4()
        )
    assert StockLedgerEntry.objects.count() == ledger_before and model.objects.count() == 0


# ---------------------------------------------------------------- transfer reversal


@pytest.mark.django_db
def test_transfer_reversal_moves_stock_back_and_keeps_quality(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    debit, credit = post(scope)
    change_quality(scope, scope["other"], "RELEASED")
    before = quality_snapshot()
    user = approver(scope)
    transfer = StockTransfer.objects.get(source_entry=debit)
    reversal = module.reverse_transfer(
        transfer=transfer, actor=user, reason="Wrong destination", request_id=uuid4()
    )
    assert balances(scope) == (Decimal("100.000001"), 0)
    assert reversal.transfer_id == transfer.pk and reversal.receipt_id is None
    assert reversal.debit_entry.warehouse_id == scope["other"].pk
    assert reversal.debit_entry.quantity_delta == -credit.quantity_delta
    assert reversal.credit_entry.warehouse_id == scope["warehouse"].pk
    assert reversal.credit_entry.quantity_delta == credit.quantity_delta
    assert quality_snapshot() == before


@pytest.mark.django_db
@pytest.mark.parametrize("destination", ["DEFAULT_HOLD", "HOLD"])
def test_transfer_reversal_requires_released_destination(transfer_scope, rv, destination):
    module, model = rv
    scope = transfer_scope
    debit, _ = post(scope)
    if destination == "HOLD":
        change_quality(scope, scope["other"], "RELEASED")
        change_quality(scope, scope["other"], "HOLD")
    transfer = StockTransfer.objects.get(source_entry=debit)
    ledger_before = StockLedgerEntry.objects.count()
    with pytest.raises(module.ReversalQualityError):
        module.reverse_transfer(
            transfer=transfer, actor=approver(scope), reason="Held", request_id=uuid4()
        )
    assert StockLedgerEntry.objects.count() == ledger_before and model.objects.count() == 0


@pytest.mark.django_db
def test_transfer_reversal_ignores_source_quality(transfer_scope, rv):
    module, _ = rv
    scope = transfer_scope
    debit, _ = post(scope)
    change_quality(scope, scope["other"], "RELEASED")
    change_quality(scope, scope["warehouse"], "HOLD")  # goods return into a HOLD source
    transfer = StockTransfer.objects.get(source_entry=debit)
    module.reverse_transfer(
        transfer=transfer, actor=approver(scope), reason="Return", request_id=uuid4()
    )
    assert balances(scope) == (Decimal("100.000001"), 0)


@pytest.mark.django_db
def test_transfer_reversal_rejected_when_destination_stock_moved_on(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    debit, _ = post(scope)
    change_quality(scope, scope["other"], "RELEASED")
    post(
        scope,
        source_warehouse=scope["other"],
        destination_warehouse=scope["warehouse"],
        quantity=Decimal("10"),
    )
    transfer = StockTransfer.objects.get(source_entry=debit)
    with pytest.raises(module.InsufficientStockError):
        module.reverse_transfer(
            transfer=transfer, actor=approver(scope), reason="Late", request_id=uuid4()
        )
    assert model.objects.count() == 0


# ---------------------------------------------------------------- authority


@pytest.mark.django_db
@pytest.mark.parametrize("case", ["warehouse_role_only", "missing_one_end", "inactive"])
def test_transfer_reversal_requires_approver_at_every_warehouse(transfer_scope, rv, case):
    module, model = rv
    scope = transfer_scope
    debit, _ = post(scope)
    change_quality(scope, scope["other"], "RELEASED")
    transfer = StockTransfer.objects.get(source_entry=debit)
    if case == "warehouse_role_only":
        user = scope["actor"]  # WAREHOUSE and QUALITY at both, no APPROVER
    elif case == "missing_one_end":
        user = approver(scope, warehouses=("other",))
    else:
        user = approver(scope)
        type(user).objects.filter(pk=user.pk).update(is_active=False)
    with pytest.raises(module.ReversalAuthorizationError):
        module.reverse_transfer(transfer=transfer, actor=user, reason="No", request_id=uuid4())
    assert model.objects.count() == 0


@pytest.mark.django_db
def test_receipt_reversal_requires_approver_at_its_warehouse(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    receipt = receive(scope)
    with pytest.raises(module.ReversalAuthorizationError):
        module.reverse_receipt(
            receipt=receipt,
            actor=approver(scope, warehouses=("other",)),
            reason="No",
            request_id=uuid4(),
        )
    assert model.objects.count() == 0


# ---------------------------------------------------------------- once only, replay


@pytest.mark.django_db
def test_original_can_be_reversed_only_once(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    receipt = receive(scope)
    user = approver(scope)
    module.reverse_receipt(receipt=receipt, actor=user, reason="First", request_id=uuid4())
    with pytest.raises(module.AlreadyReversedError):
        module.reverse_receipt(receipt=receipt, actor=user, reason="Second", request_id=uuid4())
    assert model.objects.count() == 1


@pytest.mark.django_db
def test_exact_replay_returns_original_and_changed_payload_conflicts(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    receipt = receive(scope)
    user, key = approver(scope), uuid4()
    first = module.reverse_receipt(receipt=receipt, actor=user, reason="Fix", request_id=key)
    again = module.reverse_receipt(receipt=receipt, actor=user, reason="Fix", request_id=key)
    assert again.pk == first.pk and model.objects.count() == 1
    with pytest.raises(module.ReversalConflictError):
        module.reverse_receipt(receipt=receipt, actor=user, reason="Other", request_id=key)


@pytest.mark.django_db
def test_replay_still_requires_current_authority(transfer_scope, rv):
    module, _ = rv
    scope = transfer_scope
    receipt = receive(scope)
    user, key = approver(scope), uuid4()
    module.reverse_receipt(receipt=receipt, actor=user, reason="Fix", request_id=key)
    WarehouseRoleAssignment.objects.filter(user=user, role="APPROVER").delete()
    with pytest.raises(module.ReversalAuthorizationError):
        module.reverse_receipt(receipt=receipt, actor=user, reason="Fix", request_id=key)


@pytest.mark.django_db
@pytest.mark.parametrize("reason", ["", "   ", None])
def test_reason_is_required(transfer_scope, rv, reason):
    module, _ = rv
    receipt = receive(transfer_scope)
    with pytest.raises(module.ReversalValidationError):
        module.reverse_receipt(
            receipt=receipt, actor=approver(transfer_scope), reason=reason, request_id=uuid4()
        )


@pytest.mark.django_db
@pytest.mark.parametrize("key", [None, "uuid-text", 1])
def test_request_id_must_be_uuid(transfer_scope, rv, key):
    module, _ = rv
    receipt = receive(transfer_scope)
    with pytest.raises(module.ReversalValidationError):
        module.reverse_receipt(
            receipt=receipt, actor=approver(transfer_scope), reason="x", request_id=key
        )


# ---------------------------------------------------------------- shared key registry


@pytest.mark.django_db
def test_reversal_key_cannot_reuse_a_receipt_key_and_vice_versa(transfer_scope, rv):
    module, _ = rv
    scope = transfer_scope
    used = uuid4()
    receipt = receive(scope, key=used)
    user = approver(scope)
    with pytest.raises(module.ReversalConflictError):
        module.reverse_receipt(receipt=receipt, actor=user, reason="x", request_id=used)
    reversal_key = uuid4()
    module.reverse_receipt(receipt=receipt, actor=user, reason="x", request_id=reversal_key)
    with pytest.raises(ReceiptConflictError):
        receive(scope, key=reversal_key)


# ---------------------------------------------------------------- database rules


@pytest.mark.django_db
def test_database_rejects_second_reversal_of_same_original(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    receipt = receive(scope)
    first = module.reverse_receipt(
        receipt=receipt, actor=approver(scope), reason="x", request_id=uuid4()
    )
    extra = StockLedgerEntry.objects.create(
        lot=scope["lot"],
        warehouse=scope["warehouse"],
        actor=first.debit_entry.actor,
        quantity_delta=Decimal("-40"),
        reason="x",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(receipt=receipt, debit_entry=extra, request_id=uuid4())


@pytest.mark.django_db
@pytest.mark.parametrize("bad", ["quantity", "warehouse", "both_originals", "no_original"])
def test_database_rejects_mismatched_reversal_link(transfer_scope, rv, bad):
    _, model = rv
    scope = transfer_scope
    receipt = receive(scope)
    debit, _ = post(scope)
    transfer = StockTransfer.objects.get(source_entry=debit)
    if bad == "warehouse":
        receive(scope, warehouse="other")  # so -40 is a valid ledger row at the wrong warehouse
    # A valid ledger row whose link to the original is wrong in exactly one way.
    entry = StockLedgerEntry.objects.create(
        lot=scope["lot"],
        warehouse=scope["other" if bad == "warehouse" else "warehouse"],
        actor=scope["actor"],
        quantity_delta=Decimal("-39" if bad == "quantity" else "-40"),
        reason="x",
    )
    links = {
        "quantity": dict(receipt=receipt),
        "warehouse": dict(receipt=receipt),
        "both_originals": dict(receipt=receipt, transfer=transfer),
        "no_original": {},
    }[bad]
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(debit_entry=entry, request_id=uuid4(), **links)


@pytest.mark.django_db
def test_reversal_entries_cannot_be_adopted_as_receipt_or_transfer(transfer_scope, rv):
    module, _ = rv
    scope = transfer_scope
    debit, _ = post(scope)
    change_quality(scope, scope["other"], "RELEASED")
    transfer = StockTransfer.objects.get(source_entry=debit)
    reversal = module.reverse_transfer(
        transfer=transfer, actor=approver(scope), reason="x", request_id=uuid4()
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        StockReceipt.objects.create(ledger_entry=reversal.credit_entry, request_id=uuid4())
    with pytest.raises(IntegrityError), transaction.atomic():
        StockTransfer.objects.create(
            source_entry=reversal.debit_entry,
            destination_entry=reversal.credit_entry,
            request_id=uuid4(),
        )


@pytest.mark.django_db
def test_reversal_rows_are_immutable(transfer_scope, rv):
    module, model = rv
    receipt = receive(transfer_scope)
    reversal = module.reverse_receipt(
        receipt=receipt, actor=approver(transfer_scope), reason="x", request_id=uuid4()
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.filter(pk=reversal.pk).update(request_id=uuid4())
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.filter(pk=reversal.pk).delete()


# ---------------------------------------------------------------- concurrency


@pytest.mark.django_db(transaction=True)
def test_competing_reversals_of_one_original_post_once(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    receipt = receive(scope)
    first_user = approver(scope)
    second_user = approver(scope, username="synthetic-approver-2")
    _, outcome = blocked_action(
        lambda: module.reverse_receipt(
            receipt=receipt, actor=first_user, reason="A", request_id=uuid4()
        ),
        lambda: module.reverse_receipt(
            receipt=receipt, actor=second_user, reason="B", request_id=uuid4()
        ),
    )
    assert outcome[0] == "AlreadyReversedError", outcome
    assert model.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_reversal_and_transfer_compete_for_the_same_stock(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    receipt = receive(scope, quantity=Decimal("40"))  # source now 140.000001
    user = approver(scope, username="synthetic-approver-race")
    _, outcome = blocked_action(
        lambda: post(scope, quantity=Decimal("110"))[0],  # leaves 30.000001 < 40
        lambda: module.reverse_receipt(receipt=receipt, actor=user, reason="x", request_id=uuid4()),
    )
    assert outcome[0] == "InsufficientStockError", outcome
    assert model.objects.count() == 0
    assert balances(scope) == (Decimal("30.000001"), Decimal("110"))


@pytest.mark.django_db
def test_unapplying_reversal_migration_is_refused_while_reversals_exist(transfer_scope, rv):
    from django.db import DatabaseError, connection
    from django.db.migrations.executor import MigrationExecutor

    module, _ = rv
    receipt = receive(transfer_scope)
    module.reverse_receipt(
        receipt=receipt, actor=approver(transfer_scope), reason="x", request_id=uuid4()
    )
    with pytest.raises(DatabaseError, match="cannot unapply 0009"):
        MigrationExecutor(connection).migrate([("inventory", "0008_require_request_key")])


# ---------------------------------------------------------------- review follow-ups


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad", ["valid", "debit_quantity", "credit_warehouse", "credit_lot", "actor", "reason"]
)
def test_database_validates_each_transfer_reversal_field(transfer_scope, rv, bad):
    """Each case is wrong in exactly one way; 'valid' proves the setup itself is accepted."""
    _, model = rv
    scope = transfer_scope
    debit, credit = post(scope)  # 30.000001 from warehouse to other
    transfer = StockTransfer.objects.get(source_entry=debit)
    quantity = credit.quantity_delta
    other_actor = approver(scope, username="synthetic-other-actor")
    debit_row = StockLedgerEntry.objects.create(
        lot=scope["lot"],
        warehouse=scope["other"],
        actor=scope["actor"],
        quantity_delta=Decimal("-30") if bad == "debit_quantity" else -quantity,
        reason="x",
    )
    credit_row = StockLedgerEntry.objects.create(
        lot=scope["second"] if bad == "credit_lot" else scope["lot"],
        warehouse=scope["other" if bad == "credit_warehouse" else "warehouse"],
        actor=other_actor if bad == "actor" else scope["actor"],
        quantity_delta=quantity,
        reason="y" if bad == "reason" else "x",
    )
    values = dict(
        transfer=transfer, debit_entry=debit_row, credit_entry=credit_row, request_id=uuid4()
    )
    if bad == "valid":
        assert model.objects.create(**values).pk
    else:
        with pytest.raises(IntegrityError, match="exactly offset"), transaction.atomic():
            model.objects.create(**values)


@pytest.mark.django_db
def test_transfer_reversal_once_only_replay_and_conflict(transfer_scope, rv):
    module, model = rv
    scope = transfer_scope
    debit, _ = post(scope)
    change_quality(scope, scope["other"], "RELEASED")
    transfer = StockTransfer.objects.get(source_entry=debit)
    user, key = approver(scope), uuid4()
    first = module.reverse_transfer(transfer=transfer, actor=user, reason="Fix", request_id=key)
    # Replay returns history even though the destination is now HOLD and empty.
    change_quality(scope, scope["other"], "HOLD")
    again = module.reverse_transfer(transfer=transfer, actor=user, reason="Fix", request_id=key)
    assert again.pk == first.pk
    with pytest.raises(module.ReversalConflictError):
        module.reverse_transfer(transfer=transfer, actor=user, reason="Other", request_id=key)
    with pytest.raises(module.AlreadyReversedError):
        module.reverse_transfer(transfer=transfer, actor=user, reason="Fix", request_id=uuid4())
    assert model.objects.count() == 1


@pytest.mark.django_db
def test_receipt_reversal_rejects_inactive_approver(transfer_scope, rv):
    module, model = rv
    receipt = receive(transfer_scope)
    user = approver(transfer_scope)
    type(user).objects.filter(pk=user.pk).update(is_active=False)
    with pytest.raises(module.ReversalAuthorizationError):
        module.reverse_receipt(receipt=receipt, actor=user, reason="x", request_id=uuid4())
    assert model.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_cross_lot_same_uuid_reversal_race_is_decided_at_the_registry(transfer_scope, rv):
    """Different Lot and different actor: the only shared row is the registry key."""
    module, model = rv
    scope = transfer_scope
    second = scope | {"lot": scope["second"]}
    first_receipt, second_receipt = receive(scope), receive(second)
    first_user = approver(scope)
    second_user = approver(scope, username="synthetic-approver-other-lot")
    ledger_second_lot = StockLedgerEntry.objects.filter(lot=scope["second"]).count()
    key = uuid4()
    _, outcome = blocked_action(
        lambda: module.reverse_receipt(
            receipt=first_receipt, actor=first_user, reason="A", request_id=key
        ),
        lambda: module.reverse_receipt(
            receipt=second_receipt, actor=second_user, reason="B", request_id=key
        ),
    )
    assert outcome[0] == "ReversalConflictError", outcome
    assert model.objects.count() == 1
    assert StockLedgerEntry.objects.filter(lot=scope["second"]).count() == ledger_second_lot


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("hold_first", [True, False])
def test_transfer_reversal_serializes_with_destination_hold(transfer_scope, rv, hold_first):
    module, model = rv
    scope = transfer_scope
    debit, _ = post(scope)
    change_quality(scope, scope["other"], "RELEASED")
    transfer = StockTransfer.objects.get(source_entry=debit)
    user = approver(scope, username="synthetic-approver-hold")

    def hold():
        return change_quality(scope, scope["other"], "HOLD")

    def reverse():
        return module.reverse_transfer(
            transfer=transfer, actor=user, reason="x", request_id=uuid4()
        )

    _, outcome = blocked_action(hold if hold_first else reverse, reverse if hold_first else hold)
    if hold_first:
        assert outcome[0] == "ReversalQualityError", outcome
        assert model.objects.count() == 0
    else:
        assert outcome[0] == "committed", outcome
        assert model.objects.count() == 1
