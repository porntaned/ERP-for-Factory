from collections.abc import Callable
from typing import Any

import pytest
from django.apps import apps


@pytest.fixture
def model() -> Callable[[str], Any]:
    def resolve(name: str) -> Any:
        try:
            return apps.get_model("facilities", name)
        except LookupError:
            pytest.fail(
                f"facilities.{name} is not registered; expected RED until M2.2 is implemented",
                pytrace=False,
            )

    return resolve


@pytest.fixture
def hierarchy(db: None, model: Callable[[str], Any]) -> tuple[Any, Any, Any]:
    organization_model = model("Organization")
    plant_model = model("Plant")
    warehouse_model = model("Warehouse")

    organization = organization_model.objects.create(code="ACME", display_name="บริษัท เอซีเอ็มอี")
    plant = plant_model.objects.create(
        organization=organization,
        code="BKK",
        display_name="โรงงานบางกอก",
    )
    warehouse = warehouse_model.objects.create(
        plant=plant,
        code="RM-A",
        display_name="คลังวัตถุดิบ เอ",
    )
    return organization, plant, warehouse
