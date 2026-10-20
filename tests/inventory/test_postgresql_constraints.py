from collections.abc import Callable
from queue import Queue
from threading import Barrier, Thread
from typing import Any

import pytest
from django.apps import apps
from django.db import IntegrityError, close_old_connections, connections, transaction


@pytest.mark.django_db
@pytest.mark.parametrize("null_field", ["item_id", "code"])
def test_required_lot_fields_reject_null_at_database_boundary(
    inventory_model: Callable[[str], Any], raw_item: Any, null_field: str
) -> None:
    values = {"item_id": raw_item.pk, "code": "LOT-001"}
    values[null_field] = None

    with pytest.raises(IntegrityError), transaction.atomic():
        inventory_model("Lot").objects.create(**values)


@pytest.mark.django_db(transaction=True)
def test_invalid_item_reference_fails_at_database_boundary(
    inventory_model: Callable[[str], Any],
) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        inventory_model("Lot").objects.create(
            item_id=2_147_483_647,
            code="LOT-001",
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_lot_creation_allows_only_one(
    inventory_model: Callable[[str], Any],
) -> None:
    organization_model = apps.get_model("facilities", "Organization")
    organization = organization_model.objects.create(code="ACME", display_name="ACME")
    uom_model = apps.get_model("catalog", "UnitOfMeasure")
    uom = uom_model.objects.create(code="EA", display_name="Each")
    item_model = apps.get_model("catalog", "Item")
    item = item_model.objects.create(
        organization=organization,
        code="LED-CHIP",
        display_name="LED chip",
        item_type="RAW",
        base_uom=uom,
    )
    lot_model = inventory_model("Lot")
    barrier = Barrier(2)
    results: Queue[str] = Queue()

    def create_lot() -> None:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            with transaction.atomic():
                lot_model.objects.create(item_id=item.pk, code="LOT-RACE")
            results.put("created")
        except IntegrityError:
            results.put("integrity_error")
        except Exception as error:  # Surface harness/thread failures in the parent assertion.
            results.put(f"unexpected:{type(error).__name__}:{error}")
        finally:
            connections.close_all()

    workers = [Thread(target=create_lot), Thread(target=create_lot)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)

    assert not any(worker.is_alive() for worker in workers)
    outcomes = sorted(results.get(timeout=1) for _ in range(2))
    assert outcomes == ["created", "integrity_error"]
    assert lot_model.objects.filter(item=item, code="LOT-RACE").count() == 1

