from queue import Queue
from threading import Barrier, Thread
from typing import Any

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, connection, connections, transaction


def test_access_control_suite_uses_postgresql(assignment_model: Any) -> None:
    assert connection.vendor == "postgresql"


@pytest.mark.django_db(transaction=True)
def test_concurrent_exact_duplicate_assignment_allows_only_one(
    assignment_model: Any,
) -> None:
    user_model = get_user_model()
    user = user_model(username="synthetic-concurrent-user")
    user.set_unusable_password()
    user.save()
    assert not user.has_usable_password()

    organization_model = apps.get_model("facilities", "Organization")
    plant_model = apps.get_model("facilities", "Plant")
    warehouse_model = apps.get_model("facilities", "Warehouse")
    organization = organization_model.objects.create(code="ACME", display_name="ACME")
    plant = plant_model.objects.create(
        organization=organization,
        code="BKK",
        display_name="Bangkok",
    )
    warehouse = warehouse_model.objects.create(
        plant=plant,
        code="RM-A",
        display_name="Raw material warehouse",
    )
    barrier = Barrier(2)
    results: Queue[str] = Queue()

    def create_assignment() -> None:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            with transaction.atomic():
                assignment_model.objects.create(
                    user_id=user.pk,
                    warehouse_id=warehouse.pk,
                    role="WAREHOUSE",
                )
            results.put("created")
        except IntegrityError:
            results.put("integrity_error")
        except Exception as error:  # Surface harness/thread failures in the parent assertion.
            results.put(f"unexpected:{type(error).__name__}:{error}")
        finally:
            connections.close_all()

    workers = [Thread(target=create_assignment), Thread(target=create_assignment)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)

    assert not any(worker.is_alive() for worker in workers)
    outcomes = sorted(results.get(timeout=1) for _ in range(2))
    assert outcomes == ["created", "integrity_error"]
    assert assignment_model.objects.filter(
        user=user,
        warehouse=warehouse,
        role="WAREHOUSE",
    ).count() == 1
