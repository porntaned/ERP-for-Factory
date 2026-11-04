"""M5.1 (Issue #69): create_bom_draft and approve_bom.

Owner rules: PRODUCTION drafts, APPROVER (not the creator) activates; an ACTIVE version is
locked and the previous ACTIVE version retires in the same transaction. Each command replays an
exact repeat of its request UUID and rejects any other reuse.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from inventory.models import RequestKey
from manufacturing.models import BillOfMaterials, BomLine
from manufacturing.services import (
    BomAuthorizationError,
    BomConflictError,
    BomValidationError,
    approve_bom,
    create_bom_draft,
)
from tests.inventory.test_stock_receipt_concurrency import blocked_action

FOUR = Decimal("4")


def draft(mf, *, actor="production", item="lamp", lines=None, key=None):
    return create_bom_draft(
        item=mf.items[item],
        lines=lines
        if lines is not None
        else [(mf.items["chip"], FOUR), (mf.items["driver"], Decimal("1"))],
        actor=mf.users[actor],
        request_id=key or uuid4(),
    )


def approve(mf, bom, *, actor="approver", key=None):
    return approve_bom(bom=bom, actor=mf.users[actor], request_id=key or uuid4())


def state(bom):
    bom.refresh_from_db()
    return bom.status


# ---------------------------------------------------------------- drafts


@pytest.mark.django_db
def test_draft_creates_next_version_with_lines(mf):
    first = draft(mf)
    second = draft(mf, lines=[(mf.items["chip"], Decimal("2.5"))])
    assert (first.version, second.version) == (1, 2)
    assert first.status == "DRAFT" and first.created_by == mf.users["production"]
    assert dict(first.lines.values_list("component__code", "quantity_per")) == {
        "LED-CHIP": FOUR,
        "DRIVER": Decimal("1"),
    }
    assert draft(mf, item="lamp2").version == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "case",
    ["empty", "duplicate", "itself", "float", "zero", "negative", "seven_places", "not_a_pair"],
)
def test_draft_rejects_bad_lines(mf, case):
    chip, lamp = mf.items["chip"], mf.items["lamp"]
    lines = {
        "empty": [],
        "duplicate": [(chip, FOUR), (chip, Decimal("1"))],
        "itself": [(lamp, FOUR)],
        "float": [(chip, 4.0)],
        "zero": [(chip, Decimal("0"))],
        "negative": [(chip, Decimal("-1"))],
        "seven_places": [(chip, Decimal("1.0000001"))],
        "not_a_pair": [chip],
    }[case]
    with pytest.raises(BomValidationError):
        draft(mf, lines=lines)
    assert not BillOfMaterials.objects.exists() and not RequestKey.objects.exists()


@pytest.mark.django_db
def test_draft_rejects_raw_item_and_foreign_component(mf):
    with pytest.raises(BomValidationError):
        draft(mf, item="chip", lines=[(mf.items["driver"], FOUR)])
    with pytest.raises(BomValidationError):
        draft(mf, lines=[(mf.items["foreign"], FOUR)])
    assert not BillOfMaterials.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("actor", ["approver2", "outsider"])
def test_draft_requires_production(mf, actor):
    with pytest.raises(BomAuthorizationError):
        draft(mf, actor=actor)


@pytest.mark.django_db
def test_draft_authority_is_scoped_to_organization(mf):
    # mf-foreign holds PRODUCTION only at a warehouse of another organization.
    with pytest.raises(BomAuthorizationError):
        draft(mf, actor="foreign")
    assert not BillOfMaterials.objects.exists()


@pytest.mark.django_db
def test_inactive_actor_rejected(mf):
    user = mf.users["production"]
    user.is_active = False
    user.save()
    with pytest.raises(BomAuthorizationError):
        draft(mf)


@pytest.mark.django_db
def test_draft_replay_and_conflict(mf):
    key = uuid4()
    first = draft(mf, key=key)
    assert draft(mf, key=key) == first  # exact repeat replays
    assert BillOfMaterials.objects.count() == 1
    with pytest.raises(BomConflictError):
        draft(mf, key=key, lines=[(mf.items["chip"], Decimal("5"))])
    with pytest.raises(BomConflictError):
        draft(mf, key=key, item="lamp2")


# ---------------------------------------------------------------- approval


@pytest.mark.django_db
def test_approve_activates_and_retires_previous(mf):
    v1 = approve(mf, draft(mf))
    assert (v1.status, v1.approved_by) == ("ACTIVE", mf.users["approver"])
    assert v1.approved_at is not None
    v2 = approve(mf, draft(mf), actor="approver2")
    assert (state(v1), v2.status) == ("RETIRED", "ACTIVE")
    assert BillOfMaterials.objects.filter(item=mf.items["lamp"], status="ACTIVE").get() == v2


@pytest.mark.django_db
def test_approve_rejects_creator(mf):
    bom = draft(mf, actor="approver")  # approver also holds PRODUCTION at LINE-1/FG
    with pytest.raises(BomAuthorizationError):
        approve(mf, bom, actor="approver")
    assert state(bom) == "DRAFT"


@pytest.mark.django_db
@pytest.mark.parametrize("actor", ["production", "outsider", "foreign"])
def test_approve_requires_approver_in_organization(mf, actor):
    bom = draft(mf, actor="approver")
    with pytest.raises(BomAuthorizationError):
        approve(mf, bom, actor=actor)
    assert state(bom) == "DRAFT"


@pytest.mark.django_db
def test_approve_rejects_non_draft(mf):
    v1 = approve(mf, draft(mf))
    with pytest.raises(BomValidationError, match="only a DRAFT"):
        approve(mf, v1, actor="approver2")
    approve(mf, draft(mf))
    with pytest.raises(BomValidationError, match="only a DRAFT"):
        approve(mf, v1, actor="approver2")  # now RETIRED
    v1.refresh_from_db()
    assert (v1.status, v1.approved_by) == ("RETIRED", mf.users["approver"])


@pytest.mark.django_db
def test_approve_replay_after_retirement(mf):
    key = uuid4()
    v1 = approve(mf, draft(mf), key=key)
    approve(mf, draft(mf))  # retires v1
    replay = approve(mf, v1, key=key)
    assert replay == v1 and replay.status == "RETIRED"


@pytest.mark.django_db
def test_approve_key_reused_for_other_bom_conflicts(mf):
    key = uuid4()
    approve(mf, draft(mf), key=key)
    other = draft(mf, item="lamp2")
    with pytest.raises(BomConflictError):
        approve(mf, other, key=key)
    with pytest.raises(BomConflictError):
        approve(
            mf,
            BillOfMaterials.objects.get(version=1, item=mf.items["lamp"]),
            actor="approver2",
            key=key,
        )
    assert state(other) == "DRAFT"


@pytest.mark.django_db
def test_cross_command_key_conflict(mf):
    key = uuid4()
    bom = draft(mf, key=key)
    with pytest.raises(BomConflictError):
        approve(mf, bom, key=key)  # key belongs to BOM_DRAFT
    RequestKey.objects.create(request_id=(receipt_key := uuid4()), command="RECEIPT")
    with pytest.raises(BomConflictError):
        draft(mf, key=receipt_key)
    assert state(bom) == "DRAFT" and BillOfMaterials.objects.count() == 1


# ---------------------------------------------------------------- concurrency


@pytest.mark.django_db(transaction=True)
def test_concurrent_drafts_get_versions_1_and_2(mf):
    first, outcome = blocked_action(lambda: draft(mf), lambda: draft(mf))
    assert outcome[0] == "committed"
    assert sorted(BillOfMaterials.objects.values_list("version", flat=True)) == [1, 2]
    assert first.version == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_approvals_leave_one_active(mf):
    a, b = draft(mf), draft(mf)
    _, outcome = blocked_action(lambda: approve(mf, a), lambda: approve(mf, b, actor="approver2"))
    assert outcome[0] == "committed"
    assert BillOfMaterials.objects.filter(status="ACTIVE").count() == 1
    assert (state(a), state(b)) == ("RETIRED", "ACTIVE")
    assert BomLine.objects.count() == 4


@pytest.mark.django_db
def test_replay_requires_current_authority(mf):
    """As M4.3.6: an exact replay is answered only while the actor still holds the role."""
    from access_control.models import WarehouseRoleAssignment

    draft_key, approve_key = uuid4(), uuid4()
    bom = draft(mf, key=draft_key)
    approve(mf, bom, key=approve_key)
    WarehouseRoleAssignment.objects.filter(user=mf.users["production"]).delete()
    WarehouseRoleAssignment.objects.filter(user=mf.users["approver"], role="APPROVER").delete()
    with pytest.raises(BomAuthorizationError):
        draft(mf, key=draft_key)
    with pytest.raises(BomAuthorizationError):
        approve(mf, bom, key=approve_key)
