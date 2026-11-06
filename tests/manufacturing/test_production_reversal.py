# ruff: noqa: F811 (fixtures imported from sibling test modules)
"""M5.2c (Issue #81): reverse production postings; shortfall reason; holding messages.

Owner rules (2026-11-05): APPROVER at the posting's warehouse reverses a whole posting once,
with an opposite entry referencing the untouched original; only while the order is OPEN; an
OUTPUT only while every entry of its Lot is an OUTPUT posting or the reversal of one.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from inventory.models import (
    ProductionPosting,
    ProductionPostingReversal,
    RequestKey,
    StockLedgerEntry,
    StockReceipt,
)
from inventory.production import (
    AlreadyReversedError,
    OutputLotUsedError,
    PostingAuthorizationError,
    PostingConflictError,
    reverse_production_posting,
)
from inventory.transfers import transfer_stock
from tests.inventory.test_stock_receipt_concurrency import blocked_action
from tests.quality.helpers import release as inspect_release

from .test_material_movements import balance, give_back, issue, order, plant, stock  # noqa: F401
from .test_production_postings import consume, line, output, scrap  # noqa: F401

D = Decimal


def reverse_posting(mf, link, *, actor="approver2", reason="Recorded in error", key=None):
    return reverse_production_posting(
        posting=link.posting,
        actor=mf.users[actor],
        reason=reason,
        request_id=key or uuid4(),
    )


def release(mf, lot, warehouse="FG"):
    # M6.1: an output Lot is released by a FINAL inspection that passes.
    inspect_release(lot, mf.wh[warehouse], mf.qc, quantity=Decimal("1"), note="Synthetic release")


def move(mf, lot, source, destination, quantity):
    return transfer_stock(
        lot=lot,
        source_warehouse=mf.wh[source],
        destination_warehouse=mf.wh[destination],
        actor=mf.staff,
        quantity=D(quantity),
        reason="Synthetic move",
        request_id=uuid4(),
    )


def rejected(action):
    with pytest.raises(IntegrityError), transaction.atomic():
        action()


# ---------------------------------------------------------------- Inventory command


@pytest.mark.django_db
def test_inventory_reverses_each_kind_with_one_opposite_entry(line):
    used = consume(line, "30")
    reversal = reverse_posting(line, used)
    entry = reversal.ledger_entry
    assert (entry.lot, entry.warehouse.code, entry.quantity_delta) == (line.lot, "LINE-1", D("30"))
    assert (entry.actor, entry.reason) == (line.users["approver2"], "Recorded in error")
    used.posting.ledger_entry.refresh_from_db()
    assert used.posting.ledger_entry.quantity_delta == D("-30")
    assert ProductionPosting.objects.get(pk=used.posting.pk).reversal == reversal
    assert balance(line, "LINE-1") == D("40")

    made = output(line, "5")
    lamp = made.posting.ledger_entry.lot
    reversal = reverse_posting(line, made)
    assert (reversal.ledger_entry.warehouse.code, reversal.ledger_entry.quantity_delta) == (
        "FG",
        D("-5"),
    )
    assert balance(line, "FG", lot=lamp) == D("0")


@pytest.mark.django_db
def test_inventory_reversal_needs_approver_at_the_posting_warehouse(line):
    used = consume(line, "1")
    for actor in ("production", "approver"):  # PRODUCTION only / APPROVER elsewhere
        with pytest.raises(PostingAuthorizationError):
            reverse_posting(line, used, actor=actor)
    assert not ProductionPostingReversal.objects.exists()


@pytest.mark.django_db
def test_inventory_reversal_replay_conflict_and_once_only(line):
    used, other = consume(line, "1"), consume(line, "2")
    key = uuid4()
    first = reverse_posting(line, used, key=key)
    assert reverse_posting(line, used, key=key) == first
    with pytest.raises(PostingConflictError):
        reverse_posting(line, used, key=key, reason="Another reason")
    with pytest.raises(PostingConflictError):
        reverse_posting(line, other, key=key)
    with pytest.raises(AlreadyReversedError):
        reverse_posting(line, used)
    consume_key = uuid4()
    consume(line, "1", key=consume_key)
    with pytest.raises(PostingConflictError):
        reverse_posting(line, other, key=consume_key)
    assert RequestKey.objects.get(request_id=key).command == "POSTING_REV"
    assert ProductionPostingReversal.objects.count() == 1


@pytest.mark.django_db
def test_output_reversal_refused_after_the_lot_moved(line):
    made = output(line, "5")
    lamp = made.posting.ledger_entry.lot
    release(line, lamp)
    move(line, lamp, "FG", "RM-A", "1")
    release(line, lamp, "RM-A")
    move(line, lamp, "RM-A", "FG", "1")  # back again: history still blocks
    assert balance(line, "FG", lot=lamp) == D("5")
    with pytest.raises(OutputLotUsedError):
        reverse_posting(line, made)


@pytest.mark.django_db
def test_output_reversal_allowed_after_release(line):
    made = output(line, "5")
    release(line, made.posting.ledger_entry.lot)
    assert reverse_posting(line, made).ledger_entry.quantity_delta == D("-5")


# ---------------------------------------------------------------- Inventory database rules


def raw_reversal(link, *, quantity=None, lot=None, warehouse=None, entry=None):
    original = link.posting.ledger_entry
    if entry is None:
        entry = StockLedgerEntry.objects.create(
            lot=lot or original.lot,
            warehouse=warehouse or original.warehouse,
            actor=original.actor,
            reason="Raw reversal",
            quantity_delta=-original.quantity_delta if quantity is None else quantity,
        )
    return ProductionPostingReversal.objects.create(
        posting=link.posting, ledger_entry=entry, request_id=uuid4()
    )


@pytest.mark.django_db
def test_database_checks_reversal_links(line):
    used = consume(line, "3")
    other_lot = stock(line, "L7", D("5"))
    receipt_entry = StockReceipt.objects.first().ledger_entry
    rejected(lambda: raw_reversal(used, quantity=D("2")))
    rejected(lambda: raw_reversal(used, lot=other_lot))
    rejected(lambda: raw_reversal(used, warehouse=line.wh["RM-A"]))
    rejected(lambda: raw_reversal(used, entry=receipt_entry))
    rejected(lambda: raw_reversal(used, entry=consume(line, "3").posting.ledger_entry))

    reversal = raw_reversal(used)
    rejected(
        lambda: ProductionPostingReversal.objects.filter(pk=reversal.pk).update(request_id=uuid4())
    )
    rejected(lambda: ProductionPostingReversal.objects.filter(pk=reversal.pk).delete())
    entry = reversal.ledger_entry
    rejected(lambda: StockReceipt.objects.create(ledger_entry=entry, request_id=uuid4()))
    rejected(
        lambda: ProductionPosting.objects.create(
            kind="CONSUME", ledger_entry=entry, request_id=uuid4()
        )
    )
    rejected(lambda: raw_reversal(used))  # once only
    assert RequestKey.objects.get(request_id=reversal.request_id).command == "POSTING_REV"


@pytest.mark.django_db
def test_database_refuses_output_reversal_of_a_used_lot(line):
    made = output(line, "5")
    lamp = made.posting.ledger_entry.lot
    release(line, lamp)
    move(line, lamp, "FG", "RM-A", "1")
    rejected(lambda: raw_reversal(made, quantity=D("-5")))


# ---------------------------------------------------------------- Manufacturing command


def reverse(mf, link, *, actor="approver2", key=None):
    from manufacturing.services import reverse_order_posting

    return reverse_order_posting(
        order_posting=link,
        actor=mf.users[actor],
        reason="Recorded in error",
        request_id=key or uuid4(),
    )


@pytest.mark.django_db
def test_reversed_consumption_returns_to_the_order_holding(line):
    used = consume(line, "30")
    reverse(line, used)
    assert balance(line, "LINE-1") == D("40")
    give_back(line, "40")
    assert balance(line, "LINE-1") == D("0")


@pytest.mark.django_db
def test_reversed_scrap_returns_to_the_order_holding(line):
    lost = scrap(line, "5")
    reverse(line, lost)
    consume(line, "40")
    assert balance(line, "LINE-1") == D("0")


@pytest.mark.django_db
def test_reversed_output_lowers_net_output(line):
    from manufacturing.services import MaterialLimitError

    made = output(line, "10")
    reverse(line, made)
    output(line, "10")  # same Lot code again: the Lot holds only this order's outputs
    with pytest.raises(MaterialLimitError):
        output(line, "1")
    assert balance(line, "FG", lot=made.posting.ledger_entry.lot) == D("10")


@pytest.mark.django_db
def test_order_reversal_maps_inventory_refusals(line):
    from manufacturing.services import MaterialAuthorizationError, MaterialLimitError

    used = consume(line, "1")
    with pytest.raises(MaterialAuthorizationError):
        reverse(line, used, actor="production")
    reverse(line, used)
    with pytest.raises(AlreadyReversedError):
        reverse(line, used)
    made = output(line, "5")
    release(line, made.posting.ledger_entry.lot)
    move(line, made.posting.ledger_entry.lot, "FG", "RM-A", "1")
    with pytest.raises(MaterialLimitError):
        reverse(line, made)


@pytest.mark.django_db
def test_reversal_refused_on_a_closed_order(line):
    from manufacturing.services import MaterialValidationError, close_production_order

    used = consume(line, "40")
    output(line, "10")
    close_production_order(order=line.order, actor=line.users["production"], request_id=uuid4())
    with pytest.raises(MaterialValidationError):
        reverse(line, used)
    rejected(lambda: raw_reversal(used))
    assert not ProductionPostingReversal.objects.exists()


@pytest.mark.django_db
def test_genealogy_nets_reversals(line):
    from manufacturing.genealogy import inputs_of, outputs_of

    give_back(line, "8")
    other_lot = stock(line, "L2", D("10"))
    issue(line, "8", lot=other_lot)
    wrong = consume(line, "8", lot=other_lot)
    consume(line, "32")
    kept = output(line, "5")
    dropped = output(line, "5", code="LAMP-0002")
    reverse(line, wrong)
    reverse(line, dropped)
    lamp = kept.posting.ledger_entry.lot
    assert [(link.lot, link.quantity) for link in inputs_of(lamp)] == [(line.lot, D("32"))]
    assert inputs_of(dropped.posting.ledger_entry.lot) == []  # M5.4: fully reversed output
    assert outputs_of(other_lot) == []
    assert [(link.lot, link.quantity) for link in outputs_of(line.lot)] == [(lamp, D("5"))]


# ---------------------------------------------------------------- concurrency


@pytest.mark.django_db(transaction=True)
def test_concurrent_reversals_of_one_posting(line):
    used = consume(line, "10")
    _, outcome = blocked_action(lambda: reverse(line, used), lambda: reverse(line, used))
    assert outcome[0] == "AlreadyReversedError", outcome
    assert ProductionPostingReversal.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_close_racing_a_consumption_reversal(line):
    from manufacturing.services import close_production_order

    used = consume(line, "40")
    output(line, "10")

    def close():
        return close_production_order(
            order=line.order, actor=line.users["production"], request_id=uuid4()
        )

    _, outcome = blocked_action(lambda: reverse(line, used), close)
    assert outcome[0] == "OrderValidationError", outcome
    line.order.refresh_from_db()
    assert line.order.status == "OPEN"


@pytest.mark.django_db(transaction=True)
def test_consumption_reversal_racing_a_close(line):
    from manufacturing.services import close_production_order

    used = consume(line, "40")
    output(line, "10")
    _, outcome = blocked_action(
        lambda: close_production_order(
            order=line.order, actor=line.users["production"], request_id=uuid4()
        ),
        lambda: reverse(line, used),
    )
    assert outcome[0] == "MaterialValidationError", outcome
    assert balance(line, "LINE-1") == D("0")


@pytest.mark.django_db(transaction=True)
def test_output_reversal_racing_a_transfer(line):
    made = output(line, "5")
    lamp = made.posting.ledger_entry.lot
    release(line, lamp)
    _, outcome = blocked_action(
        lambda: move(line, lamp, "FG", "RM-A", "1")[0], lambda: reverse(line, made)
    )
    assert outcome[0] == "MaterialLimitError", outcome
    assert balance(line, "FG", lot=lamp) == D("4")


@pytest.mark.django_db(transaction=True)
def test_transfer_racing_an_output_reversal(line):
    made = output(line, "5")
    lamp = made.posting.ledger_entry.lot
    release(line, lamp)
    _, outcome = blocked_action(
        lambda: reverse(line, made), lambda: move(line, lamp, "FG", "RM-A", "1")[0]
    )
    assert outcome[0] == "InsufficientStockError", outcome
    assert balance(line, "FG", lot=lamp) == D("0")


# ---------------------------------------------------------------- shortfall reason


def close(mf, *, reason=None, key=None):
    from manufacturing.services import close_production_order

    return close_production_order(
        order=mf.order,
        actor=mf.users["production"],
        request_id=key or uuid4(),
        shortfall_reason=reason,
    )


@pytest.mark.django_db
def test_close_short_needs_a_reason(line):
    from manufacturing.services import OrderValidationError

    consume(line, "40")
    output(line, "9")
    for blank in (None, "", "   "):
        with pytest.raises(OrderValidationError, match="shortfall"):
            close(line, reason=blank)
    closed = close(line, reason="Yield loss on synthetic run")
    assert (closed.status, closed.shortfall_reason) == ("CLOSED", "Yield loss on synthetic run")


@pytest.mark.django_db
def test_close_complete_refuses_a_reason(line):
    from manufacturing.services import OrderValidationError

    consume(line, "40")
    output(line, "10")
    with pytest.raises(OrderValidationError, match="shortfall"):
        close(line, reason="Not short at all")
    closed = close(line)
    assert (closed.status, closed.shortfall_reason) == ("CLOSED", None)


@pytest.mark.django_db
def test_shortfall_follows_output_reversal(line):
    from manufacturing.services import OrderValidationError

    consume(line, "40")
    output(line, "9")
    extra = output(line, "1")
    reverse(line, extra)
    with pytest.raises(OrderValidationError, match="shortfall"):
        close(line)
    assert close(line, reason="One lamp recorded in error").status == "CLOSED"


@pytest.mark.django_db
def test_close_replay_compares_the_reason(line):
    from manufacturing.services import OrderConflictError

    give_back(line, "40")
    key = uuid4()
    first = close(line, reason="Order stopped", key=key)
    assert close(line, reason="Order stopped", key=key) == first
    with pytest.raises(OrderConflictError):
        close(line, reason="Another story", key=key)


@pytest.mark.django_db
def test_database_requires_shortfall_reason_iff_short(line):
    from django.utils import timezone

    from manufacturing.models import ProductionOrder

    consume(line, "40")
    output(line, "9")
    orders = ProductionOrder.objects.filter(pk=line.order.pk)

    def closing(reason):
        return lambda: orders.update(
            status="CLOSED",
            closed_by=line.users["production"],
            closed_at=timezone.now(),
            close_request_id=uuid4(),
            shortfall_reason=reason,
        )

    rejected(lambda: orders.update(shortfall_reason="Not closed yet"))
    rejected(closing(None))
    rejected(closing("   "))
    output(line, "1")
    rejected(closing("Complete but explained"))
    closing(None)()
    assert orders.get().status == "CLOSED"


# ---------------------------------------------------------------- refusal messages


@pytest.mark.django_db
def test_refusals_name_each_held_lot(line):
    from manufacturing.services import OrderValidationError, cancel_production_order

    give_back(line, "10")
    other_lot = stock(line, "L2", D("10"))
    issue(line, "10", lot=other_lot)
    held = "LED-CHIP lot L1 holds 30, LED-CHIP lot L2 holds 10"
    with pytest.raises(OrderValidationError) as closing:
        close(line)
    assert str(closing.value).endswith(held), closing.value
    with pytest.raises(OrderValidationError) as cancelling:
        cancel_production_order(
            order=line.order, actor=line.users["production"], reason="Stop", request_id=uuid4()
        )
    assert str(cancelling.value).endswith(held), cancelling.value


# ---------------------------------------------------------------- cancel needs no output
# Issue #86 (owner ruling, 2026-11-05, option A): an order with net output cannot be cancelled.


def cancel(mf, *, key=None):
    from manufacturing.services import cancel_production_order

    return cancel_production_order(
        order=mf.order, actor=mf.users["production"], reason="Stop", request_id=key or uuid4()
    )


@pytest.mark.django_db
def test_cancel_refused_while_the_order_has_net_output(line):
    from manufacturing.models import ProductionOrder
    from manufacturing.services import OrderValidationError

    consume(line, "40")
    made = output(line, "5")
    with pytest.raises(OrderValidationError, match="net output is 5"):
        cancel(line)
    assert ProductionOrder.objects.get(pk=line.order.pk).status == "OPEN"
    reverse(line, made)
    assert cancel(line).status == "CANCELLED"


@pytest.mark.django_db
def test_cancel_refused_after_a_partial_output_reversal(line):
    from manufacturing.services import OrderValidationError

    consume(line, "40")
    output(line, "4")
    extra = output(line, "1")
    reverse(line, extra)
    with pytest.raises(OrderValidationError, match="net output is 4"):
        cancel(line)


@pytest.mark.django_db
def test_database_refuses_cancel_with_net_output(line):
    from django.utils import timezone

    from manufacturing.models import ProductionOrder

    consume(line, "40")
    made = output(line, "5")
    orders = ProductionOrder.objects.filter(pk=line.order.pk)

    def cancelling():
        return orders.update(
            status="CANCELLED",
            cancelled_by=line.users["production"],
            cancelled_at=timezone.now(),
            cancel_reason="Stop",
            cancel_request_id=uuid4(),
        )

    rejected(cancelling)
    assert orders.get().status == "OPEN"
    reverse(line, made)
    cancelling()
    assert orders.get().status == "CANCELLED"


# ---------------------------------------------------------------- migrations


@pytest.mark.django_db(transaction=True)
def test_migrations_unapply_only_without_reversals(line):
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        used = consume(line, "5")
        executor.migrate([("inventory", "0012_production_posting_rules")])
        MigrationExecutor(connection).migrate(latest)
        reverse(line, used)
        with pytest.raises(IntegrityError, match="production reversals exist"):
            MigrationExecutor(connection).migrate(
                [("inventory", "0013_production_posting_reversal")]
            )
        assert ProductionPostingReversal.objects.count() == 1
    finally:
        MigrationExecutor(connection).migrate(latest)


@pytest.mark.django_db
def test_order_reversal_rejects_a_malformed_request(line):
    from manufacturing.services import MaterialValidationError, reverse_order_posting

    used = consume(line, "1")
    for key in ("not-a-uuid", None):
        with pytest.raises(MaterialValidationError):
            reverse_order_posting(
                order_posting=used, actor=line.users["approver2"], reason="x", request_id=key
            )
