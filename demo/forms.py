from uuid import uuid4

from django import forms

from facilities.models import Warehouse
from inventory.models import Lot

QUANTITY = dict(max_digits=20, decimal_places=6, min_value=0.000001, label="จำนวน")


class LotChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.code} · {obj.item.code}"


class WarehouseChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.code} · {obj.display_name}"


def _lot_field():
    return LotChoiceField(Lot.objects.select_related("item").order_by("code"), label="Lot")


def _request_id():
    return forms.UUIDField(widget=forms.HiddenInput, initial=uuid4)


class ReceiptForm(forms.Form):
    lot = _lot_field()
    warehouse = WarehouseChoiceField(Warehouse.objects.none(), label="คลังปลายทาง")
    quantity = forms.DecimalField(**QUANTITY)
    reason = forms.CharField(label="เหตุผล", max_length=500)
    request_id = _request_id()

    def __init__(self, *args, warehouses, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = warehouses


class TransferForm(forms.Form):
    lot = _lot_field()
    source_warehouse = WarehouseChoiceField(Warehouse.objects.none(), label="คลังต้นทาง")
    destination_warehouse = WarehouseChoiceField(Warehouse.objects.none(), label="คลังปลายทาง")
    quantity = forms.DecimalField(**QUANTITY)
    reason = forms.CharField(label="เหตุผล", max_length=500)
    request_id = _request_id()

    def __init__(self, *args, warehouses, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source_warehouse"].queryset = warehouses
        self.fields["destination_warehouse"].queryset = warehouses

    def clean(self):
        data = super().clean()
        if data.get("source_warehouse") and data.get("source_warehouse") == data.get(
            "destination_warehouse"
        ):
            raise forms.ValidationError("คลังต้นทางและปลายทางต้องต่างกัน")
        return data


class ReversalForm(forms.Form):
    reason = forms.CharField(label="เหตุผล", max_length=500)
    request_id = _request_id()
