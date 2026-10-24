"""Receipt -> Quality -> transfer -> replay through the real internal commands."""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import connection

from access_control.models import WarehouseRoleAssignment
from inventory.models import StockLedgerEntry, StockReceipt, StockTransfer
from inventory.services import get_stock_balance, receive_stock
from inventory.transfer_policy import TransferQualityError
from inventory.transfers import TransferAuthorizationError, TransferConflictError, transfer_stock
from quality.models import LotDispositionEvent
from quality.services import get_lot_disposition, transition_lot_disposition


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("destination_released", [False, True])
def test_receipt_quality_transfer_history_and_retry_workflow(ledger_scope, destination_released):
    # No pre-seeded ledger or disposition: receipt and Quality own those transitions.
    assert connection.vendor == "postgresql"
    scope = ledger_scope
    lot, source, destination, actor = (scope[key] for key in ("lot", "warehouse", "other", "actor"))
    for warehouse in (source, destination):
        for role in ("WAREHOUSE", "QUALITY"):
            WarehouseRoleAssignment.objects.create(user=actor, warehouse=warehouse, role=role)

    def disposition(warehouse):
        return get_lot_disposition(lot=lot, warehouse=warehouse)

    def release(warehouse):
        transition_lot_disposition(
            lot=lot,
            warehouse=warehouse,
            actor=actor,
            expected_disposition=disposition(warehouse),
            target_disposition="RELEASED",
            reason="Synthetic inspection — ตรวจรับ",
            request_id=uuid4(),
        )

    def snapshot():
        return (
            tuple(get_stock_balance(lot=lot, warehouse=w) for w in (source, destination)),
            list(StockLedgerEntry.objects.order_by("id").values()),
            list(StockTransfer.objects.order_by("id").values()),
            list(LotDispositionEvent.objects.order_by("id").values()),
        )

    receipt_values = dict(
        lot=lot,
        warehouse=source,
        actor=actor,
        quantity=Decimal("101.000003"),
        reason="Synthetic material receipt — รับเข้า",
        request_id=uuid4(),
    )
    receipt = receive_stock(**receipt_values)
    assert receive_stock(**receipt_values).pk == receipt.pk
    assert disposition(source) == disposition(destination) == "HOLD"
    assert LotDispositionEvent.objects.count() == 0
    command = dict(
        lot=lot,
        source_warehouse=source,
        destination_warehouse=destination,
        actor=actor,
        quantity=Decimal("37.000001"),
        reason="  Synthetic transfer — โอนคลัง  ",
        request_id=uuid4(),
    )
    before = snapshot()
    with pytest.raises(TransferQualityError):
        transfer_stock(**command)
    assert snapshot() == before  # Rejection must not consume this UUID or post a debit.

    release(source)
    if destination_released:
        release(destination)
    quality_before = list(LotDispositionEvent.objects.order_by("id").values())
    debit, credit = transfer_stock(**command)
    history = StockTransfer.objects.get(request_id=command["request_id"])
    assert (history.source_entry_id, history.destination_entry_id) == (debit.pk, credit.pk)
    assert receipt.ledger_entry_id not in (debit.pk, credit.pk)
    assert StockReceipt.objects.get().pk == receipt.pk
    assert snapshot()[0] == (Decimal("64.000002"), Decimal("37.000001"))
    assert list(LotDispositionEvent.objects.order_by("id").values()) == quality_before
    assert disposition(destination) == ("RELEASED" if destination_released else "HOLD")
    for entry, warehouse, delta in (
        (debit, source, Decimal("-37.000001")),
        (credit, destination, Decimal("37.000001")),
    ):
        entry.refresh_from_db()
        assert (entry.lot_id, entry.warehouse_id, entry.actor_id) == (
            lot.pk,
            warehouse.pk,
            actor.pk,
        )
        assert entry.quantity_delta == delta and entry.reason == command["reason"]
        assert entry.created_at is not None

    before = snapshot()
    assert tuple(e.pk for e in transfer_stock(**command)) == (debit.pk, credit.pk)
    with pytest.raises(TransferConflictError):
        transfer_stock(**(command | {"reason": "Changed request"}))
    assert snapshot() == before

    # Receipt replay and transfer replay remain separate historical operations.
    assert receive_stock(**receipt_values).pk == receipt.pk
    WarehouseRoleAssignment.objects.filter(
        user=actor, warehouse=destination, role="WAREHOUSE"
    ).delete()
    with pytest.raises(TransferAuthorizationError):
        transfer_stock(**command)
    assert snapshot() == before
    assert StockReceipt.objects.count() == StockTransfer.objects.count() == 1
    assert StockLedgerEntry.objects.count() == 3
