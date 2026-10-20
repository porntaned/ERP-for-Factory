from collections.abc import Callable
from queue import Queue
from threading import Barrier, Thread
from typing import Any

import pytest
from django.db import IntegrityError, close_old_connections, connection, connections, transaction


def test_test_suite_uses_postgresql() -> None:
    assert connection.vendor == "postgresql"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("model_name", "parent_field", "code"),
    [
        ("Plant", "organization_id", "BKK"),
        ("Warehouse", "plant_id", "RM-A"),
    ],
)
def test_invalid_parent_reference_fails_at_database_boundary(
    model: Callable[[str], Any],
    model_name: str,
    parent_field: str,
    code: str,
) -> None:
    target_model = model(model_name)

    with pytest.raises(IntegrityError), transaction.atomic():
        target_model.objects.create(
            **{
                parent_field: 2_147_483_647,
                "code": code,
                "display_name": "Invalid parent",
            }
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("model_name", "null_field"),
    [
        ("Organization", "code"),
        ("Organization", "display_name"),
        ("Plant", "organization_id"),
        ("Plant", "code"),
        ("Plant", "display_name"),
        ("Warehouse", "plant_id"),
        ("Warehouse", "code"),
        ("Warehouse", "display_name"),
    ],
)
def test_required_fields_reject_null_at_database_boundary(
    model: Callable[[str], Any],
    model_name: str,
    null_field: str,
) -> None:
    organization_model = model("Organization")
    if model_name == "Organization":
        target_model = organization_model
        values = {"code": "ORG", "display_name": "Organization"}
    else:
        organization = organization_model.objects.create(
            code="PARENT",
            display_name="Parent organization",
        )
        plant_model = model("Plant")
        if model_name == "Plant":
            target_model = plant_model
            values = {
                "organization_id": organization.pk,
                "code": "PLANT",
                "display_name": "Plant",
            }
        else:
            plant = plant_model.objects.create(
                organization=organization,
                code="PLANT",
                display_name="Parent plant",
            )
            target_model = model("Warehouse")
            values = {
                "plant_id": plant.pk,
                "code": "WAREHOUSE",
                "display_name": "Warehouse",
            }

    values[null_field] = None
    with pytest.raises(IntegrityError), transaction.atomic():
        target_model.objects.create(**values)


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_warehouse_creation_allows_only_one(
    model: Callable[[str], Any],
) -> None:
    organization_model = model("Organization")
    plant_model = model("Plant")
    warehouse_model = model("Warehouse")
    organization = organization_model.objects.create(code="ACME", display_name="ACME")
    plant = plant_model.objects.create(organization=organization, code="BKK", display_name="BKK")
    barrier = Barrier(2)
    results: Queue[str] = Queue()

    def create_warehouse() -> None:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            with transaction.atomic():
                warehouse_model.objects.create(
                    plant_id=plant.pk,
                    code="RM-A",
                    display_name="Concurrent RM-A",
                )
            results.put("created")
        except IntegrityError:
            results.put("integrity_error")
        except Exception as error:  # Surface harness/thread failures in the parent assertion.
            results.put(f"unexpected:{type(error).__name__}:{error}")
        finally:
            connections.close_all()

    workers = [Thread(target=create_warehouse), Thread(target=create_warehouse)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)

    assert not any(worker.is_alive() for worker in workers)
    outcomes = sorted(results.get(timeout=1) for _ in range(2))
    assert outcomes == ["created", "integrity_error"]
    assert warehouse_model.objects.filter(plant=plant, code="RM-A").count() == 1
