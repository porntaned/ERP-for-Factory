from collections.abc import Callable
from typing import Any

import pytest
from django.apps import apps


@pytest.fixture
def catalog_model() -> Callable[[str], Any]:
    def resolve(name: str) -> Any:
        try:
            return apps.get_model("catalog", name)
        except LookupError:
            pytest.fail(
                f"catalog.{name} is not registered; expected RED until Issue #5 is implemented",
                pytrace=False,
            )

    return resolve


@pytest.fixture
def organization(db: None) -> Any:
    organization_model = apps.get_model("facilities", "Organization")
    return organization_model.objects.create(code="ACME", display_name="บริษัท เอซีเอ็มอี")


@pytest.fixture
def each_uom(db: None, catalog_model: Callable[[str], Any]) -> Any:
    return catalog_model("UnitOfMeasure").objects.create(
        code="EA",
        display_name="ชิ้น",
    )
