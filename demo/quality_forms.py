"""M6.1 PR 2 (Issue #96): forms for the Quality screens. Commands validate everything again."""

from django import forms

from facilities.models import Warehouse
from inventory.models import Lot

from .forms import QUANTITY, _request_id


class _PairForm(forms.Form):
    lot = forms.ModelChoiceField(Lot.objects.all(), widget=forms.HiddenInput)
    warehouse = forms.ModelChoiceField(Warehouse.objects.all(), widget=forms.HiddenInput)
    request_id = _request_id()


class InspectionForm(_PairForm):
    result = forms.ChoiceField(
        choices=(("PASS", "PASS"), ("FAIL", "FAIL")),
        label="ผล",
        widget=forms.Select(attrs={"aria-label": "ผล", "class": "form-select form-select-sm"}),
    )
    sample_quantity = forms.DecimalField(**(QUANTITY | {"label": "จำนวนตัวอย่าง"}))
    note = forms.CharField(label="บันทึก", max_length=500)


class ReturnToHoldForm(_PairForm):
    reason = forms.CharField(label="เหตุผล", max_length=500)
