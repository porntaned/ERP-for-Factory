"""M6.4 (Issue #113): LotInspection joins the read-only admin (M6.1 finding 2, owner ruling 1).

View-only: no add, change or delete, as for LotDispositionEvent.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from quality.models import LotInspection


@pytest.fixture
def superuser(db):
    call_command("seed_demo", verbosity=0)  # releases L-0001 at RM-A with an inspection
    return get_user_model().objects.create_superuser(username="root-demo", password=None)


@pytest.mark.django_db
def test_lot_inspection_is_in_the_read_only_admin(client, superuser):
    client.force_login(superuser)
    index = client.get("/admin/").content.decode()
    assert 'href="/admin/quality/lotinspection/"' in index
    assert 'href="/admin/quality/lotinspection/add/"' not in index
    inspection = LotInspection.objects.order_by("id").first()
    before = (LotInspection.objects.count(), inspection.note)
    assert client.get("/admin/quality/lotinspection/").status_code == 200
    assert client.get("/admin/quality/lotinspection/add/").status_code == 403
    change = client.get(f"/admin/quality/lotinspection/{inspection.pk}/change/")
    assert change.status_code == 200 and 'name="_save"' not in change.content.decode()
    assert (
        client.post(
            f"/admin/quality/lotinspection/{inspection.pk}/change/", {"note": "Rewritten"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/admin/quality/lotinspection/{inspection.pk}/delete/", {"post": "yes"}
        ).status_code
        == 403
    )
    client.post(
        "/admin/quality/lotinspection/",
        {"action": "delete_selected", "_selected_action": [inspection.pk], "post": "yes"},
    )
    inspection.refresh_from_db()
    assert (LotInspection.objects.count(), inspection.note) == before
