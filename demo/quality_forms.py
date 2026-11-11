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


class AuditFilterForm(forms.Form):
    """M6.4 (Issue #113): GET filters of the QC history page; only the user's warehouses."""

    warehouse = forms.ModelChoiceField(
        Warehouse.objects.none(),
        required=False,
        label="คลัง",
        empty_label="ทุกคลัง",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    date_from = forms.DateField(
        required=False,
        label="ตั้งแต่วันที่",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )
    date_to = forms.DateField(
        required=False,
        label="ถึงวันที่",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )
    page = forms.IntegerField(
        required=False, min_value=1, max_value=1_000_000, widget=forms.HiddenInput
    )

    def __init__(self, *args, warehouses, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = warehouses
        self.fields["warehouse"].label_from_instance = lambda warehouse: warehouse.code

    def clean(self):
        data = super().clean()
        start, end = data.get("date_from"), data.get("date_to")
        if start and end and start > end:
            raise forms.ValidationError("ตั้งแต่วันที่ต้องไม่เกินถึงวันที่")
        return data
