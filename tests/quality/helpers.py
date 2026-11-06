"""Test helpers for M6.1 (Issue #96): releasing a Lot-Warehouse now takes an inspection.

`release` is the normal path through `record_inspection`. `force_release` is for setups the
command can no longer reach, such as releasing a pair that holds no stock (owner ruling,
2026-11-06): it writes the inspection and its event directly, so PostgreSQL still checks the
origin, kind, note and pairing; only the command's balance check is skipped. `give_origin` links
a receipt to a raw starting ledger entry so the Lot has an origin.
"""

from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from inventory.models import StockReceipt
from inventory.services import get_stock_balance
from quality.models import LotDispositionEvent, LotInspection
from quality.services import inspection_kind, record_inspection


def release(
    lot, warehouse, actor, *, quantity=None, note="Synthetic inspection — PASS", request_id=None
):
    if quantity is None:
        quantity = get_stock_balance(lot=lot, warehouse=warehouse)
    return record_inspection(
        lot=lot,
        warehouse=warehouse,
        result="PASS",
        sample_quantity=quantity,
        note=note,
        actor=actor,
        request_id=request_id or uuid4(),
    )


def force_release(lot, warehouse, actor, *, note="Synthetic setup release"):
    with transaction.atomic():
        inspection = LotInspection.objects.create(
            lot=lot,
            warehouse=warehouse,
            kind=inspection_kind(lot),
            result="PASS",
            sample_quantity=Decimal("1"),
            note=note,
            inspector=actor,
        )
        return LotDispositionEvent.objects.create(
            lot=lot,
            warehouse=warehouse,
            actor=actor,
            request_id=uuid4(),
            from_disposition="HOLD",
            to_disposition="RELEASED",
            reason=note,
            inspection=inspection,
        )


ORIGIN_KEYS = set()


def give_origin(entry):
    """Link a receipt to a raw starting entry; its key is remembered so counts can skip it."""
    key = uuid4()
    ORIGIN_KEYS.add(key)
    return StockReceipt.objects.create(request_id=key, ledger_entry=entry)


def made_receipts():
    """Receipts the test made itself, without the origin receipts give_origin linked."""
    return StockReceipt.objects.exclude(request_id__in=ORIGIN_KEYS)
