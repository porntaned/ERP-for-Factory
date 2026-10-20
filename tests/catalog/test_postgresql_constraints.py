from collections.abc import Callable
from queue import Queue
from threading import Barrier, Thread
from typing import Any

import pytest
from django.apps import apps
from django.db import IntegrityError, close_old_connections, connections, transaction


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("model_name", "null_field"),
    [
        ("UnitOfMeasure", "code"),
        ("UnitOfMeasure", "display_name"),
        ("Item", "organization_id"),
        ("Item", "code"),
        ("Item", "display_name"),
        ("Item", "item_type"),
        ("Item", "base_uom_id"),
    ],
)
def test_required_fields_reject_null_at_database_boundary(
    catalog_model: Callable[[str], Any], null_field: str, model_name: str
) -> None:
    uom_model = catalog_model("UnitOfMeasure")
    if model_name == "UnitOfMeasure":
        target_model = uom_model
        values = {"code": "EA", "display_name": "Each"}
    else:
        organization_model = apps.get_model("facilities", "Organization")
        organization = organization_model.objects.create(code="ACME", display_name="ACME")
        uom = uom_model.objects.create(code="EA", display_name="Each")
        target_model = catalog_model("Item")
        values = {
            "organization_id": organization.pk,
            "code": "LED",
            "display_name": "LED",
            "item_type": "FINISHED",
            "base_uom_id": uom.pk,
        }

    values[null_field] = None
    with pytest.raises(IntegrityError), transaction.atomic():
        target_model.objects.create(**values)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("parent_field", ["organization_id", "base_uom_id"])
def test_invalid_item_reference_fails_at_database_boundary(
    catalog_model: Callable[[str], Any], parent_field: str
) -> None:
    organization_model = apps.get_model("facilities", "Organization")
    organization = organization_model.objects.create(code="ACME", display_name="ACME")
    uom = catalog_model("UnitOfMeasure").objects.create(code="EA", display_name="Each")
    values = {
        "organization_id": organization.pk,
        "code": "LED",
        "display_name": "LED",
        "item_type": "FINISHED",
        "base_uom_id": uom.pk,
    }
    values[parent_field] = 2_147_483_647

    with pytest.raises(IntegrityError), transaction.atomic():
        catalog_model("Item").objects.create(**values)


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_item_creation_allows_only_one(
    catalog_model: Callable[[str], Any],
) -> None:
    organization_model = apps.get_model("facilities", "Organization")
    organization = organization_model.objects.create(code="ACME", display_name="ACME")
    uom = catalog_model("UnitOfMeasure").objects.create(code="EA", display_name="Each")
    item_model = catalog_model("Item")
    barrier = Barrier(2)
    results: Queue[str] = Queue()

    def create_item() -> None:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            with transaction.atomic():
                item_model.objects.create(
                    organization_id=organization.pk,
                    code="LED",
                    display_name="Concurrent LED",
                    item_type="FINISHED",
                    base_uom_id=uom.pk,
                )
            results.put("created")
        except IntegrityError:
            results.put("integrity_error")
        except Exception as error:  # Surface harness/thread failures in the parent assertion.
            results.put(f"unexpected:{type(error).__name__}:{error}")
        finally:
            connections.close_all()

    workers = [Thread(target=create_item), Thread(target=create_item)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)

    assert not any(worker.is_alive() for worker in workers)
    outcomes = sorted(results.get(timeout=1) for _ in range(2))
    assert outcomes == ["created", "integrity_error"]
    assert item_model.objects.filter(organization=organization, code="LED").count() == 1
