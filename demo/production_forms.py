"""Record forms for the Manufacturing screens (M5.5 PR 2). Choices are narrowed for the user;
the Manufacturing commands still enforce every rule."""

from django import forms

from facilities.models import Warehouse
from inventory.models import Lot
from manufacturing.models import BillOfMaterials

from .forms import QUANTITY, LotChoiceField, WarehouseChoiceField, _request_id


class BomChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.item.code} v{obj.version} · {obj.item.display_name}"


def _lots(ids):
    return Lot.objects.filter(pk__in=ids).select_related("item").order_by("code")


def _reason():
    return forms.CharField(label="เหตุผล", max_length=500)


class OrderForm(forms.Form):
    bom = BomChoiceField(
        BillOfMaterials.objects.filter(status="ACTIVE").select_related("item"), label="BOM"
    )
    quantity = forms.DecimalField(**QUANTITY)
    line_warehouse = WarehouseChoiceField(Warehouse.objects.none(), label="Line")
    output_warehouse = WarehouseChoiceField(Warehouse.objects.none(), label="คลังผลผลิต")
    request_id = _request_id()

    def __init__(self, *args, warehouses, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["line_warehouse"].queryset = warehouses
        self.fields["output_warehouse"].queryset = warehouses


class IssueForm(forms.Form):
    lot = LotChoiceField(Lot.objects.none(), label="Lot")
    source_warehouse = WarehouseChoiceField(Warehouse.objects.none(), label="คลังต้นทาง")
    quantity = forms.DecimalField(**QUANTITY)
    reason = _reason()
    request_id = _request_id()

    def __init__(self, *args, order, warehouses, **kwargs):
        super().__init__(*args, **kwargs)
        components = order.bom.lines.values("component_id")
        self.fields["lot"].queryset = (
            Lot.objects.filter(item_id__in=components).select_related("item").order_by("code")
        )
        self.fields["source_warehouse"].queryset = warehouses.exclude(pk=order.line_warehouse_id)


class HeldLotForm(forms.Form):
    """Consume or scrap: only Lots the order holds on its line."""

    lot = LotChoiceField(Lot.objects.none(), label="Lot")
    quantity = forms.DecimalField(**QUANTITY)
    reason = _reason()
    request_id = _request_id()

    def __init__(self, *args, held, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lot"].queryset = _lots(held)


class ReturnForm(HeldLotForm):
    destination_warehouse = WarehouseChoiceField(Warehouse.objects.none(), label="คืนเข้าคลัง")

    field_order = ["lot", "destination_warehouse", "quantity", "reason"]

    def __init__(self, *args, order, warehouses, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["destination_warehouse"].queryset = warehouses.exclude(
            pk=order.line_warehouse_id
        )


class OutputForm(forms.Form):
    lot_code = forms.CharField(label="รหัส Lot ผลผลิต", max_length=32)
    quantity = forms.DecimalField(**QUANTITY)
    reason = _reason()
    request_id = _request_id()


class CloseForm(forms.Form):
    shortfall_reason = forms.CharField(
        label="เหตุผลที่ผลผลิตขาด (กรอกเฉพาะเมื่อผลผลิตน้อยกว่าที่สั่ง)",
        max_length=500,
        required=False,
    )
    request_id = _request_id()


class CancelForm(forms.Form):
    reason = _reason()
    request_id = _request_id()


class ReverseForm(forms.Form):
    reason = _reason()
    request_id = _request_id()


class LotSearchForm(forms.Form):
    """M6.3: an exact Lot code (any item). Django's CharField refuses a NUL character."""

    code = forms.CharField(label="รหัส Lot", required=False)
