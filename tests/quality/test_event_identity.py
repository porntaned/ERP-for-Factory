from typing import Any
from uuid import uuid4

import pytest
from django.db import DatabaseError, connection, transaction

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("write_path", ["orm", "sql"])
@pytest.mark.parametrize("explicit_id", [1, 1_000_000_000])
def test_explicit_event_id_is_rejected_without_blocking_service_hold(
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    write_path: str,
    explicit_id: int,
) -> None:
    assert connection.vendor == "postgresql"
    lot = quality_scope["lot"]
    warehouse = quality_scope["warehouse"]
    grant_role(quality_user, warehouse, "QUALITY")
    event_model = disposition_contract["event_model"]
    rejected_request = uuid4()

    with pytest.raises(DatabaseError) as rejected, transaction.atomic():
        if write_path == "orm":
            event_model.objects.create(
                id=explicit_id,
                lot=lot,
                warehouse=warehouse,
                actor=quality_user,
                request_id=rejected_request,
                from_disposition="HOLD",
                to_disposition="RELEASED",
                reason="Synthetic explicit-ID boundary regression",
            )
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO quality_lotdispositionevent "
                    "(id, lot_id, warehouse_id, actor_id, request_id, "
                    "from_disposition, to_disposition, reason) "
                    "VALUES (%s, %s, %s, %s, %s, 'HOLD', 'RELEASED', %s)",
                    [
                        explicit_id,
                        lot.pk,
                        warehouse.pk,
                        quality_user.pk,
                        rejected_request,
                        "Synthetic explicit-ID SQL regression",
                    ],
                )

    assert rejected.value.__cause__.sqlstate == "428C9"
    assert event_model.objects.count() == 0
    assert disposition_contract["get_disposition"](lot=lot, warehouse=warehouse) == "HOLD"

    released = disposition_contract["transition"](
        lot=lot,
        warehouse=warehouse,
        actor=quality_user,
        expected_disposition="HOLD",
        target_disposition="RELEASED",
        reason="Normal release after rejected explicit ID",
        request_id=uuid4(),
    )
    hold_command = {
        "lot": lot,
        "warehouse": warehouse,
        "actor": quality_user,
        "expected_disposition": "RELEASED",
        "target_disposition": "HOLD",
        "reason": "Normal containment remains possible",
        "request_id": uuid4(),
    }
    held = disposition_contract["transition"](**hold_command)
    retried = disposition_contract["transition"](**hold_command)
    assert held.pk > released.pk
    assert retried.pk == held.pk
    assert event_model.objects.count() == 2
    assert not event_model.objects.filter(request_id=rejected_request).exists()
    assert disposition_contract["get_disposition"](lot=lot, warehouse=warehouse) == "HOLD"
