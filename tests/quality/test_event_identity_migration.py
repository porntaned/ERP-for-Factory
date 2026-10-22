from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from django.db import DatabaseError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)
PREVIOUS = [("quality", "0002_preserve_history_identity")]
CURRENT = [("quality", "0003_authoritative_event_identity")]


@pytest.fixture
def previous_identity_schema(transactional_db: None) -> Iterator[None]:
    assert connection.vendor == "postgresql"
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        MigrationExecutor(connection).migrate(PREVIOUS)
        assert identity_mode() == "d"
        yield
    finally:
        MigrationExecutor(connection).migrate(latest)


def identity_mode() -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT attidentity FROM pg_attribute "
            "WHERE attrelid = 'quality_lotdispositionevent'::regclass AND attname = 'id'"
        )
        return cursor.fetchone()[0]


def sequence_state() -> tuple[int, bool]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT last_value, is_called FROM quality_lotdispositionevent_id_seq")
        return cursor.fetchone()


def set_sequence(value: int, called: bool) -> None:
    # Synthetic test setup only; production migration uses transactional RESTART.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence('quality_lotdispositionevent', 'id'), %s, %s)",
            [value, called],
        )


def event_values(scope: dict[str, Any], actor: Any) -> dict[str, Any]:
    return {
        "lot": scope["lot"],
        "warehouse": scope["warehouse"],
        "actor": actor,
        "request_id": uuid4(),
        "from_disposition": "HOLD",
        "to_disposition": "RELEASED",
        "reason": "Synthetic pre-upgrade history",
    }


@pytest.mark.parametrize(
    "sequence_value,called", [(10, False), (2_000_000_000, True), (2_000_000_000, False)]
)
def test_upgrade_preserves_high_id_history_and_reverse_reapply(
    previous_identity_schema: None,
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    grant_role: Any,
    sequence_value: int,
    called: bool,
) -> None:
    events = disposition_contract["event_model"]
    grant_role(quality_user, quality_scope["warehouse"], "QUALITY")
    released = events.objects.create(id=1_000_000_000, **event_values(quality_scope, quality_user))
    original = events.objects.values().get(pk=released.pk)
    set_sequence(sequence_value, called)

    MigrationExecutor(connection).migrate(CURRENT)

    assert identity_mode() == "a"
    assert events.objects.values().get(pk=released.pk) == original
    assert (
        disposition_contract["get_disposition"](
            lot=quality_scope["lot"], warehouse=quality_scope["warehouse"]
        )
        == "RELEASED"
    )
    held = disposition_contract["transition"](
        lot=quality_scope["lot"],
        warehouse=quality_scope["warehouse"],
        actor=quality_user,
        expected_disposition="RELEASED",
        target_disposition="HOLD",
        reason="Containment after legacy high-ID upgrade",
        request_id=uuid4(),
    )
    assert held.pk == max(released.pk + 1, sequence_value + int(called))
    assert (
        disposition_contract["get_disposition"](
            lot=quality_scope["lot"], warehouse=quality_scope["warehouse"]
        )
        == "HOLD"
    )
    history = list(events.objects.order_by("id").values())
    before_reverse = sequence_state()

    MigrationExecutor(connection).migrate(PREVIOUS)
    assert identity_mode() == "d"
    assert list(events.objects.order_by("id").values()) == history
    assert sequence_state() == before_reverse
    reverse_values = event_values(quality_scope, quality_user)
    reverse_values["lot"] = quality_scope["second_lot"]
    legacy = events.objects.create(id=held.pk + 100, **reverse_values)
    legacy_original = events.objects.values().get(pk=legacy.pk)

    MigrationExecutor(connection).migrate(CURRENT)
    assert identity_mode() == "a"
    assert events.objects.values().get(pk=legacy.pk) == legacy_original
    assert list(events.objects.filter(pk__lte=held.pk).order_by("id").values()) == history
    second_hold = disposition_contract["transition"](
        lot=quality_scope["second_lot"],
        warehouse=quality_scope["warehouse"],
        actor=quality_user,
        expected_disposition="RELEASED",
        target_disposition="HOLD",
        reason="Containment after reapplying identity migration",
        request_id=uuid4(),
    )
    assert second_hold.pk == legacy.pk + 1


@pytest.mark.parametrize("sequence_value,called", [(1, False), (500, False), (500, True)])
def test_empty_upgrade_preserves_unused_or_ahead_sequence(
    previous_identity_schema: None,
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
    sequence_value: int,
    called: bool,
) -> None:
    events = disposition_contract["event_model"]
    assert events.objects.count() == 0
    set_sequence(sequence_value, called)

    MigrationExecutor(connection).migrate(CURRENT)

    assert identity_mode() == "a"
    assert sequence_state() == (sequence_value, called)
    created = events.objects.create(**event_values(quality_scope, quality_user))
    assert created.pk == sequence_value + int(called)


def test_exhausted_historical_id_aborts_migration_atomically(
    previous_identity_schema: None,
    disposition_contract: dict[str, Any],
    quality_scope: dict[str, Any],
    quality_user: Any,
) -> None:
    events = disposition_contract["event_model"]
    before = sequence_state()
    with pytest.raises(DatabaseError, match="event ID space exhausted") as error:
        with transaction.atomic():
            events.objects.create(
                id=9_223_372_036_854_775_807, **event_values(quality_scope, quality_user)
            )
            with connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            MigrationExecutor(connection).migrate(CURRENT)
    assert error.value.__cause__.sqlstate == "22003"
    assert identity_mode() == "d"
    assert events.objects.count() == 0
    assert sequence_state() == before
